import hashlib
from datetime import datetime
from operator import itemgetter
from base64 import b64encode, b64decode

import numpy
import requests
from requests.exceptions import HTTPError
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConflictError, NotFoundError
from furl import furl
from image_match import signature_database_base
from image_match.elasticsearch_driver import SignatureES
from image_match.goldberg import ImageSignature
from logbook import Logger


class AdES(SignatureES):
    def make_record_from_signature_base64(
        self, signature, path=None, metadata=None
    ):
        """
        Mostly copied from `image_match.signature_database_base.make_record`,
        but takes in an image signature in base 64 instead of a path to an
        image.
        :param signature: The signature of the image, in base 64.
        :type signature: :class:`basestring`
        :param path: The path to associate with this image. This does not
            influence the signature.
        :type: path: :class:`basestring`
        :param metadata: The metadata to associate with this image. This does
            not influence the signature.
        :type metadata: :class:`object`
        :return: The record.
        :rtype: :class:`dict`
        """
        record = dict()
        record['path'] = path
        signature = image_signature_base64_to_array(signature)
        record['signature'] = signature.tolist()
        if metadata:
            record['metadata'] = metadata

        words = signature_database_base.get_words(signature, self.k, self.N)
        signature_database_base.max_contrast(words)
        words = signature_database_base.words_to_int(words)
        for i in range(self.N):
            record[''.join(['simple_word_', str(i)])] = words[i].tolist()

        return record

    def search_image_signature_base64(self, signature):
        """
        Searches for matches to the given base 64 image signature in the
        database.
        :param signature: The signature of the image, in base 64.
        :type signature: :class:`basestring`
        :return: A list of matches.
        :rtype: :class:`list` of :class:`dict`
        """
        record = self.make_record_from_signature_base64(signature)
        results = self.search_single_record(record)
        return sorted(results, key=itemgetter('dist'))

    def add_image_signature_base64(
        self, _id, signature, path=None, metadata=None
    ):
        """
        Adds an image signature to the database.
        :param _id: The ID to assign to this image.
        :type _id: :class:`basestring`
        :param signature: The signature of the image, in base 64.
        :type signature: :class:`basestring`
        :param path: The path to associate with this image. This does not
            influence the signature.
        :type: path: :class:`basestring`
        :param metadata: The metadata to associate with this image. This does
            not influence the signature.
        :type metadata: :class:`object`
        """
        record = self.make_record_from_signature_base64(
            signature, path=path, metadata=metadata
        )
        record['timestamp'] = datetime.utcnow()
        self.es.create(
            index=self.index, doc_type=self.doc_type, id=_id, body=record
        )

MAX_CONFLICT_RETRIES = 3
MAX_RETRIES = 3

METADATA_SOURCES_KEY = 'sources'
SOURCE_URL_KEY = 'url'
SOURCE_DOMAIN_KEY = 'domain'
SOURCE_EMAIL_KEY = 'email'
SOURCE_AGE_KEY = 'age'
SOURCE_GENDER_KEY = 'gender'
SOURCE_INTERESTS_KEY = 'interests'

METADATA_IMAGE_KEY = 'image'

ADD_IMAGE_URL_MSG_FORMAT = 'Adding: {}'
ADD_IMAGE_BYTES_MSG_FORMAT = 'Adding bytes.'
ADD_IMAGE_URL_NO_SIGNATURE_MSG_FORMAT = 'Failed to get signature for: {}'
ADD_IMAGE_URL_CONFLICT_MSG_FORMAT = 'Conflict, retrying: {}'


class AdLoader(object):
    def __init__(
        self,
        index,
        hosts=None,
        distance_cutoff=0.38,
        logger=None,
        exceptions_to_reraise=None
    ):
        self._iss = ImageSignatureService()
        self._es = Elasticsearch(hosts=hosts)
        self._aes = AdES(
            self._es, index=index, distance_cutoff=distance_cutoff
        )

        if not logger:
            self.logger = Logger(self.__class__.__name__)

        else:
            self.logger = logger

        if not exceptions_to_reraise:
            self.exceptions_to_reraise = tuple()

        else:
            self.exceptions_to_reraise = tuple(exceptions_to_reraise)

        # Ensure the index to be used exists.
        self.create_index()

        self.num_images_inserted = 0
        self.num_images_updated = 0
        self.num_images_errored = 0

    def create_index(self):
        self._es.indices.create(self._aes.index, ignore=400)

    def delete_index(self):
        self._es.indices.delete(index=self._aes.index)

    def wipe_index(self):
        self.delete_index()
        self.create_index()

    def refresh_index(self):
        self._es.indices.refresh(index=self._aes.index)

    def _add_image_to_index(
            self,
            image_signature,
            image,
            image_url,
            source_url,
            email,
            age,
            gender,
            interests
    ):
        source = {
            SOURCE_URL_KEY: source_url,
            SOURCE_DOMAIN_KEY: furl(source_url).netloc,
            SOURCE_EMAIL_KEY: email,
            SOURCE_AGE_KEY: age,
            SOURCE_GENDER_KEY: gender,
            SOURCE_INTERESTS_KEY: interests
        }
        _id = hashlib.sha512(image_signature.encode('utf-8')).hexdigest()
        existing_document = None
        try:
            get_result = self._es.get(
                index=self._aes.index, doc_type=self._aes.doc_type, id=_id
            )
            existing_document = get_result['_source']

        except NotFoundError:
            pass

        if existing_document:
            existing_sources = existing_document['metadata'][
                METADATA_SOURCES_KEY
            ]
            existing_sources.append(source)
            self._es.update(
                index=self._aes.index,
                doc_type=self._aes.doc_type,
                id=_id,
                body={'doc': existing_document}
            )
            self.num_images_updated += 1

        else:
            metadata = {
                METADATA_SOURCES_KEY: [source],
                METADATA_IMAGE_KEY: image
            }
            self._aes.add_image_signature_base64(
                _id, image_signature, path=image_url, metadata=metadata
            )
            self.num_images_inserted += 1

    def _add_image(
            self,
            image_signature,
            image,
            image_url,
            source_url,
            email,
            age,
            gender,
            interests,
            retry_num=0
    ):
        try:
            self._add_image_to_index(
                image_signature,
                image,
                image_url,
                source_url,
                email,
                age,
                gender,
                interests
            )

        except ConflictError:
            if retry_num >= MAX_CONFLICT_RETRIES:
                self.logger.exception()
                self.num_images_errored += 1

            else:
                self.logger.warning(
                    ADD_IMAGE_URL_CONFLICT_MSG_FORMAT.format(image_url)
                )
                retry_num += 1
                self._add_image(
                    image_signature,
                    image,
                    image_url,
                    source_url,
                    email,
                    age,
                    gender,
                    interests,
                    retry_num=retry_num
                )

    def add_image_url(
            self, image_url, source_url, email, age, gender, interests
    ):
        try:
            self.logger.debug(ADD_IMAGE_URL_MSG_FORMAT.format(image_url))
            image_signature, image = self._iss.get_image_signature_from_url(
                image_url
            )
            if image_signature:
                self._add_image(
                    image_signature,
                    image,
                    image_url,
                    source_url,
                    email,
                    age,
                    gender,
                    interests
                )

            else:
                self.logger.warning(
                    ADD_IMAGE_URL_NO_SIGNATURE_MSG_FORMAT.format(image_url)
                )

        except self.exceptions_to_reraise:
            raise

        except Exception:
            self.logger.exception()
            self.num_images_errored += 1

    def add_image_bytes(
            self, image_bytes, source_url, email, age, gender, interests
    ):
        try:
            self.logger.debug(ADD_IMAGE_URL_MSG_FORMAT.format('from bytes'))
            image_signature, image = self._iss.get_image_signature_from_bytes(
                image_bytes
            )
            if image_signature:
                self._add_image(
                    image_signature,
                    image,
                    image_signature,
                    source_url,
                    email,
                    age,
                    gender,
                    interests
                )

            else:
                self.logger.warning(
                    ADD_IMAGE_URL_NO_SIGNATURE_MSG_FORMAT.format('from bytes')
                )

        except self.exceptions_to_reraise:
            raise

        except Exception:
            self.logger.exception()
            self.num_images_errored += 1

    def get_image_match_by_image_url(self, image_url):
        return self._aes.search_image(image_url)

    def get_image_match_by_image_signature_base64(self, image_signature):
        return self._aes.search_image_signature_base64(
            image_signature
        )


def image_signature_array_to_base64(image_signature_array):
    return b64encode(image_signature_array.tobytes()).decode()


def image_signature_base64_to_array(image_signature_base64):
    return numpy.frombuffer(b64decode(image_signature_base64), dtype='int8')


class ImageSignatureService(object):
    def __init__(self):
        self._gis = ImageSignature()
        self._logger = Logger(self.__class__.__name__)

    def get_image_signature_from_bytes(self, image_bytes):
        base64_signature = image_signature_array_to_base64(
            self._gis.generate_signature(image_bytes, bytestream=True)
        )
        base64_image = b64encode(image_bytes).decode()
        return base64_signature, base64_image

    def get_image_signature_from_file_path(self, image_file_path):
        with open(image_file_path, 'rb') as image_file:
            return self.get_image_signature_from_bytes(image_file.read())

    def get_image_signature_from_url(self, image_url):
        return self._get_image_signature_from_url(image_url)

    def _get_image_signature_from_url(self, image_url, retry_num=0):
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            return self.get_image_signature_from_bytes(
                response.content
            )

        except HTTPError as e:
            if retry_num >= MAX_RETRIES or e.response.status_code == 404:
                return

            else:
                retry_num += 1
                return self._get_image_signature_from_url(
                    image_url, retry_num=retry_num
                )
