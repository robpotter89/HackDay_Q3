
import argparse
import imghdr
import os
import os.path as osp
import platform
import shutil
import time
from multiprocessing import Pool

import requests
from selenium import webdriver
from selenium.common.exceptions import (ElementNotVisibleException,
                                        StaleElementReferenceException)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from collect_links import CollectLinks


class Sites:
    GOOGLE = 1
    NAVER = 2
    GOOGLE_FULL = 3
    NAVER_FULL = 4

    @staticmethod
    def get_text(code):
        if code == Sites.GOOGLE:
            return 'google'
        elif code == Sites.NAVER:
            return 'naver'
        elif code == Sites.GOOGLE_FULL:
            return 'google'
        elif code == Sites.NAVER_FULL:
            return 'naver'

    @staticmethod
    def get_face_url(code):
        if code == Sites.GOOGLE or Sites.GOOGLE_FULL:
            return "&tbs=itp:face"
        if code == Sites.NAVER or Sites.NAVER_FULL:
            return "&face=1"


class AutoCrawler:
    def __init__(self, skip_already_exist=True, n_threads=4, do_google=True, do_naver=True, download_path='download',
                 full_resolution=False, face=False):
        """
        :param skip_already_exist: Skips keyword already downloaded before. This is needed when re-downloading.
        :param n_threads: Number of threads to download.
        :param do_google: Download from google.com (boolean)
        :param do_naver: Download from naver.com (boolean)
        :param download_path: Download folder path
        :param full_resolution: Download full resolution image instead of thumbnails (slow)
        :param face: Face search mode
        """

        self.skip = skip_already_exist
        self.n_threads = n_threads
        self.do_google = do_google
        self.do_naver = do_naver
        self.download_path = download_path
        self.full_resolution = full_resolution
        self.face = face

        os.makedirs('./{}'.format(self.download_path), exist_ok=True)

    @staticmethod
    def all_dirs(path):
        paths = []
        for dir in os.listdir(path):
            if os.path.isdir(path + '/' + dir):
                paths.append(path + '/' + dir)

        return paths

    @staticmethod
    def all_files(path):
        paths = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if os.path.isfile(path + '/' + file):
                    paths.append(path + '/' + file)

        return paths

    @staticmethod
    def get_extension_from_link(link, default='jpg'):
        splits = str(link).split('.')
        if len(splits) == 0:
            return default
        ext = splits[-1].lower()
        if ext == 'jpg' or ext == 'jpeg':
            return 'jpg'
        elif ext == 'gif':
            return 'gif'
        elif ext == 'png':
            return 'png'
        else:
            return default

    @staticmethod
    def validate_image(path):
        ext = imghdr.what(path)
        if ext == 'jpeg':
            ext = 'jpg'
        return ext  # returns None if not valid

    @staticmethod
    def make_dir(dirname):
        current_path = os.getcwd()
        path = os.path.join(current_path, dirname)
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def get_keywords(keywords_file='keywords.txt'):
        # read search keywords from file
        with open(keywords_file, 'r', encoding='utf-8-sig') as f:
            text = f.read()
            lines = text.split('\n')
            lines = filter(lambda x: x != '' and x is not None, lines)
            keywords = sorted(set(lines))

        print('{} keywords found: {}'.format(len(keywords), keywords))

        # re-save sorted keywords
        with open(keywords_file, 'w+', encoding='utf-8') as f:
            for keyword in keywords:
                f.write('{}\n'.format(keyword))

        return keywords

    @staticmethod
    def save_object_to_file(object, file_path):
        try:
            with open('{}'.format(file_path), 'wb') as file:
                shutil.copyfileobj(object.raw, file)
        except Exception as e:
            print('Save failed - {}'.format(e))

    def download_images(self, keyword, links, site_name):
        self.make_dir('{}/{}'.format(self.download_path, keyword))
        total = len(links)

        for index, link in enumerate(links):
            try:
                print('Downloading {} from {}: {} / {}'.format(keyword, site_name, index + 1, total))
                response = requests.get(link, stream=True)
                ext = self.get_extension_from_link(link)

                no_ext_path = '{}/{}/{}_{}'.format(self.download_path, keyword, site_name, str(index).zfill(4))
                path = no_ext_path + '.' + ext
                self.save_object_to_file(response, path)

                del response

                ext2 = self.validate_image(path)
                if ext2 is None:
                    print('Unreadable file - {}'.format(link))
                    os.remove(path)
                else:
                    if ext != ext2:
                        path2 = no_ext_path + '.' + ext2
                        os.rename(path, path2)
                        print('Renamed extension {} -> {}'.format(ext, ext2))

            except Exception as e:
                print('Download failed - ', e)
                continue

    def download_from_site(self, keyword, site_code):
        site_name = Sites.get_text(site_code)
        add_url = Sites.get_face_url(site_code) if self.face else ""

        try:
            collect = CollectLinks()  # initialize chrome driver
        except Exception as e:
            print('Error occurred while initializing chromedriver - {}'.format(e))
            return

        try:
            print('Collecting links... {} from {}'.format(keyword, site_name))

            if site_code == Sites.GOOGLE:
                links = collect.google(keyword, add_url)

            elif site_code == Sites.NAVER:
                links = collect.naver(keyword, add_url)

            elif site_code == Sites.GOOGLE_FULL:
                links = collect.google_full(keyword, add_url)

            elif site_code == Sites.NAVER_FULL:
                links = collect.naver_full(keyword, add_url)

            else:
                print('Invalid Site Code')
                links = []

            print('Downloading images from collected links... {} from {}'.format(keyword, site_name))
            self.download_images(keyword, links, site_name)

            print('Done {} : {}'.format(site_name, keyword))

        except Exception as e:
            print('Exception {}:{} - {}'.format(site_name, keyword, e))

    def download(self, args):
        self.download_from_site(keyword=args[0], site_code=args[1])

    def do_crawling(self):
        keywords = self.get_keywords()

        tasks = []

        for keyword in keywords:
            dir_name = '{}/{}'.format(self.download_path, keyword)
            if os.path.exists(os.path.join(os.getcwd(), dir_name)) and self.skip:
                print('Skipping already existing directory {}'.format(dir_name))
                continue

            if self.do_google:
                if self.full_resolution:
                    tasks.append([keyword, Sites.GOOGLE_FULL])
                else:
                    tasks.append([keyword, Sites.GOOGLE])

            if self.do_naver:
                if self.full_resolution:
                    tasks.append([keyword, Sites.NAVER_FULL])
                else:
                    tasks.append([keyword, Sites.NAVER])

        pool = Pool(self.n_threads)
        pool.map_async(self.download, tasks)
        pool.close()
        pool.join()
        print('Task ended. Pool join.')

        self.imbalance_check()

        print('End Program')

    def imbalance_check(self):
        print('Data imbalance checking...')

        dict_num_files = {}

        for dir in self.all_dirs(self.download_path):
            n_files = len(self.all_files(dir))
            dict_num_files[dir] = n_files

        avg = 0
        for dir, n_files in dict_num_files.items():
            avg += n_files / len(dict_num_files)
            print('dir: {}, file_count: {}'.format(dir, n_files))

        dict_too_small = {}

        for dir, n_files in dict_num_files.items():
            if n_files < avg * 0.5:
                dict_too_small[dir] = n_files

        if len(dict_too_small) >= 1:
            for dir, n_files in dict_too_small.items():
                print('Data imbalance detected.')
                print('Below keywords have smaller than 50% of average file count.')
                print('I recommend you to remove these directories and re-download for that keyword.')
                print('_________________________________')
                print('Too small file count directories:')
                print('dir: {}, file_count: {}'.format(dir, n_files))

            print("Remove directories above? (y/n)")
            answer = input()

            if answer == 'y':
                # removing directories too small files
                print("Removing too small file count directories...")
                for dir, n_files in dict_too_small.items():
                    shutil.rmtree(dir)
                    print('Removed {}'.format(dir))

                print('Now re-run this program to re-download removed files. (with skip_already_exist=True)')
        else:
            print('Data imbalance not detected.')



class CollectLinks:
    def __init__(self):
        executable = ''

        if platform.system() == 'Windows':
            print('Detected OS : Windows')
            executable = './chromedriver/chromedriver_win.exe'
        elif platform.system() == 'Linux':
            print('Detected OS : Linux')
            executable = './chromedriver/chromedriver_linux'
        elif platform.system() == 'Darwin':
            print('Detected OS : Mac')
            executable = './chromedriver/chromedriver_mac'
        else:
            raise OSError('Unknown OS Type')

        if not osp.exists(executable):
            raise FileNotFoundError('Chromedriver file should be placed at {}'.format(executable))

        self.browser = webdriver.Chrome(executable)

        browser_version = 'Failed to detect version'
        chromedriver_version = 'Failed to detect version'
        major_version_different = False

        if 'browserVersion' in self.browser.capabilities:
            browser_version = str(self.browser.capabilities['browserVersion'])

        if 'chrome' in self.browser.capabilities:
            if 'chromedriverVersion' in self.browser.capabilities['chrome']:
                chromedriver_version = str(self.browser.capabilities['chrome']['chromedriverVersion']).split(' ')[0]

        if browser_version.split('.')[0] != chromedriver_version.split('.')[0]:
            major_version_different = True

        print('_________________________________')
        print('Current web-browser version:\t{}'.format(browser_version))
        print('Current chrome-driver version:\t{}'.format(chromedriver_version))
        if major_version_different:
            print('warning: Version different')
            print('Download correct version at "http://chromedriver.chromium.org/downloads" and place in "./chromedriver"')
        print('_________________________________')

    def get_scroll(self):
        pos = self.browser.execute_script("return window.pageYOffset;")
        return pos

    def wait_and_click(self, xpath):
        #  Sometimes click fails unreasonably. So tries to click at all cost.
        try:
            w = WebDriverWait(self.browser, 15)
            elem = w.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            elem.click()
        except Exception as e:
            print('Click time out - {}'.format(xpath))
            print('Refreshing browser...')
            self.browser.refresh()
            time.sleep(2)
            return self.wait_and_click(xpath)

        return elem

    def google(self, keyword, add_url=""):
        self.browser.get("https://www.google.com/search?q={}&source=lnms&tbm=isch{}".format(keyword, add_url))

        time.sleep(1)

        print('Scrolling down')

        elem = self.browser.find_element_by_tag_name("body")

        for i in range(60):
            elem.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.2)

        try:
            # btn_more = self.browser.find_element(By.XPATH, '//input[@value="결과 더보기"]')
            self.wait_and_click('//input[@id="smb"]')

            for i in range(60):
                elem.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.2)

        except ElementNotVisibleException:
            pass

        photo_grid_boxes = self.browser.find_elements(By.XPATH, '//div[@class="rg_bx rg_di rg_el ivg-i"]')

        print('Scraping links')

        links = []

        for box in photo_grid_boxes:
            try:
                imgs = box.find_elements(By.TAG_NAME, 'img')

                for img in imgs:
                    src = img.get_attribute("src")
                    if src[0] != 'd':
                        links.append(src)

            except Exception as e:
                print('[Exception occurred while collecting links from google] {}'.format(e))

        print('Collect links done. Site: {}, Keyword: {}, Total: {}'.format('google', keyword, len(links)))
        self.browser.close()

        return set(links)


    def google_full(self, keyword, add_url=""):
        print('[Full Resolution Mode]')

        self.browser.get("https://www.google.co.kr/search?q={}&tbm=isch{}".format(keyword, add_url))
        time.sleep(1)

        elem = self.browser.find_element_by_tag_name("body")

        print('Scraping links')

        self.wait_and_click('//div[@data-ri="0"]')
        time.sleep(1)

        links = []
        count = 1

        last_scroll = 0
        scroll_patience = 0

        while True:
            try:
                xpath = '//div[@class="irc_c i8187 immersive-container"]//img[@class="irc_mi"]'
                imgs = self.browser.find_elements(By.XPATH, xpath)

                for img in imgs:
                    src = img.get_attribute('src')

                    if src not in links and src is not None:
                        links.append(src)
                        print('%d: %s' % (count, src))
                        count += 1

            except StaleElementReferenceException:
                # print('[Expected Exception - StaleElementReferenceException]')
                pass
            except Exception as e:
                print('[Exception occurred while collecting links from google_full] {}'.format(e))

            scroll = self.get_scroll()
            if scroll == last_scroll:
                scroll_patience += 1
            else:
                scroll_patience = 0
                last_scroll = scroll

            if scroll_patience >= 30:
                break

            elem.send_keys(Keys.RIGHT)

        links = set(links)

        print('Collect links done. Site: {}, Keyword: {}, Total: {}'.format('google_full', keyword, len(links)))
        self.browser.close()

        return links



import time
from bs4 import BeautifulSoup
from selenium import webdriver

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
import PIL


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from __future__ import absolute_import
from celery_tasks.celery import app
import time
import requests
from pymongo import MongoClient
from requests import RequestException
from requests_html import HTMLSession
import re


@app.task(bind=True, default_retry_delay=10)
def fetch_url_content(self, url, scheme='http'):
    client = MongoClient('127.0.0.1', 27017)
    db = client.crawled_urls
    collection = db.results
    stripped_url = url.strip()

    try:
        robots = Robots.fetch(scheme + '://' + stripped_url + '/robots.txt')
    except RequestException:
        return 'FAILURE: ' + stripped_url + ' : Unable to fetch robots.txt'

    if not robots.allowed(stripped_url, 'just-some-user-agent'):
        return 'FAILURE: ' + stripped_url + ' : Robots say no'

    try:
        r = requests.get(scheme + '://' + stripped_url)
        new_emails = set(re.findall("[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", r.text, re.I))
        domains = r.html.absolute_links
        collection.insert({
            'url': url,
            'scheme': 'http',
            'status': r.status_code,
            "create_time": time.time(),
            "result": r.text
        })
    except Exception as exc:
        raise self.retry(exc=exc)

    client.close()
    return 'SUCCESS: ' + stripped_url

def scroll_bottom(browser, element, range_int):
    # put a limit to the scrolling
    if range_int > 50:
        range_int = 50

    for _ in range(int(range_int / 2)):
        browser.execute_script("window.scrollBy(0, 1000)")
        update_activity(browser, state=None)
        sleep(1)

    return


def click_element(browser, element, tryNum=0):
    try:
        element.click()
        update_activity(browser, state=None)
    except Exception:
        if tryNum == 0:
            browser.execute_script(
                "document.getElementsByClassName('"
                + element.get_attribute("class")
                + "')[0].scrollIntoView({ inline: 'center' });"
            )
        elif tryNum == 1:
            browser.execute_script("window.scrollTo(0,0);")

        elif tryNum == 2:
            browser.execute_script("window.scrollTo(0,document.body.scrollHeight);")

        else:
            print("attempting last ditch effort for click, `execute_script`")
            browser.execute_script(
                "document.getElementsByClassName('"
                + element.get_attribute("class")
                + "')[0].click()"
            )
            # update server calls after last click attempt by JS
            update_activity(browser, state=None)
            # end condition for the recursive function
            return
        update_activity(browser, state=None)
        sleep_actual(1)
        tryNum += 1
        click_element(browser, element, tryNum)

def web_address_navigator(browser, link):
    """Checks and compares current URL of web page and the URL to be
    navigated and if it is different, it does navigate"""
    current_url = get_current_url(browser)
    total_timeouts = 0
    page_type = None  # file or directory

    # remove slashes at the end to compare efficiently
    if current_url is not None and current_url.endswith("/"):
        current_url = current_url[:-1]

    if link.endswith("/"):
        link = link[:-1]
        page_type = "dir"  # slash at the end is a directory

    new_navigation = current_url != link

    if current_url is None or new_navigation:
        link = link + "/" if page_type == "dir" else link  # directory links
        while True:
            try:
                browser.get(link)
                # update server calls
                update_activity(browser, state=None)
                sleep(2)
                break

            except TimeoutException as exc:
                if total_timeouts >= 7:
                    raise TimeoutException(
                        "Retried {} times to GET '{}' webpage "
                        "but failed out of a timeout!\n\t{}".format(
                            total_timeouts,
                            str(link).encode("utf-8"),
                            str(exc).encode("utf-8"),
                        )
                    )
                total_timeouts += 1
                sleep(2)


class CollectLinks:
    def __init__(self):
        return
    def tables(self):
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table = soup.find_all('td', attrs={'class': None})
        names = [str(c.contents[0]) for c in soup.find_all('td', attrs={'class': None})]
        str_names = '\n'.join(names)
        print(str_names)
        w.write(str_names)
        w.flush()
        #driver.find_elements_by_class_name('submit_button')[-1].click()
        time.sleep(3)


    def get_scroll(self):
        pos = self.browser.execute_script("return window.pageYOffset;")
        return pos

    def wait_and_click(self, xpath):
        #  Sometimes click fails unreasonably. So tries to click at all cost.
        try:
            w = WebDriverWait(self.browser, 15)
            elem = w.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            elem.click()
        except Exception as e:
            print('Click time out - {}'.format(xpath))
            print('Refreshing browser...')
            self.browser.refresh()
            time.sleep(2)
            return self.wait_and_click(xpath)

        return elem

    def google(self, keyword, add_url=""):
        self.browser.get("https://www.google.com/search?q={}&source=lnms&tbm=isch{}".format(keyword, add_url))

        time.sleep(1)

        print('Scrolling down')

        elem = self.browser.find_element_by_tag_name("body")

        for i in range(60):
            elem.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.2)

        try:
            # btn_more = self.browser.find_element(By.XPATH, '//input[@value="결과 더보기"]')
            self.wait_and_click('//input[@id="smb"]')

            for i in range(60):
                elem.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.2)

        except ElementNotVisibleException:
            pass

        photo_grid_boxes = self.browser.find_elements(By.XPATH, '//div[@class="rg_bx rg_di rg_el ivg-i"]')

        print('Scraping links')

        links = []

        for box in photo_grid_boxes:
            try:
                imgs = box.find_elements(By.TAG_NAME, 'img')

                for img in imgs:
                    src = img.get_attribute("src")
                    if src[0] != 'd':
                        links.append(src)

            except Exception as e:
                print('[Exception occurred while collecting links from google] {}'.format(e))

        print('Collect links done. Site: {}, Keyword: {}, Total: {}'.format('google', keyword, len(links)))
        self.browser.close()

        return set(links)


    def google_full(self, keyword, add_url=""):
        print('[Full Resolution Mode]')
        self.browser.get("https://www.google.com/search?q={}&tbm=isch{}".format(keyword, add_url))
        time.sleep(1)

        elem = self.browser.find_element_by_tag_name("body")

        print('Scraping links')

        self.wait_and_click('//div[@data-ri="0"]')
        time.sleep(1)

        links = []
        count = 1

        last_scroll = 0
        scroll_patience = 0

        while True:
            try:
                xpath = '//div[@class="irc_c i8187 immersive-container"]//img[@class="irc_mi"]'
                imgs = self.browser.find_elements(By.XPATH, xpath)

                for img in imgs:
                    src = img.get_attribute('src')

                    if src not in links and src is not None:
                        links.append(src)
                        print('%d: %s' % (count, src))
                        count += 1

            except StaleElementReferenceException:
                # print('[Expected Exception - StaleElementReferenceException]')
                pass
            except Exception as e:
                print('[Exception occurred while collecting links from google_full] {}'.format(e))

            scroll = self.get_scroll()
            if scroll == last_scroll:
                scroll_patience += 1
            else:
                scroll_patience = 0
                last_scroll = scroll

            if scroll_patience >= 30:
                break

            elem.send_keys(Keys.RIGHT)

        links = set(links)

        print('Collect links done. Site: {}, Keyword: {}, Total: {}'.format('google_full', keyword, len(links)))
        self.browser.close()

        return links


def retry(max_retry_count=3, start_page=None):
    """
        Decorator which refreshes the page and tries to execute the function again.
        Use it like that: @retry() => the '()' are important because its a decorator
        with params.
    """

    def real_decorator(org_func):
        def wrapper(*args, **kwargs):
            browser = None
            _start_page = start_page

            # try to find instance of a browser in the arguments
            # all webdriver classes (chrome, firefox, ...) inherit from Remote class
            for arg in args:
                if not isinstance(arg, Remote):
                    continue

                browser = arg
                break

            else:
                for _, value in kwargs.items():
                    if not isinstance(value, Remote):
                        continue

                    browser = value
                    break

            if not browser:
                print("not able to find browser in parameters!")
                return org_func(*args, **kwargs)

            if max_retry_count == 0:
                print("max retry count is set to 0, this function is useless right now")
                return org_func(*args, **kwargs)

            # get current page if none is given
            if not start_page:
                _start_page = browser.current_url

            rv = None
            retry_count = 0
            while True:
                try:
                    rv = org_func(*args, **kwargs)
                    break
                except Exception as e:
                    # TODO: maybe handle only certain exceptions here
                    retry_count += 1

                    # if above max retries => throw original exception
                    if retry_count > max_retry_count:
                        raise e

                    rv = None

                    # refresh page
                    browser.get(_start_page)

            return rv

        return wrapper

    return real_decorator

def threaded_crawler_rq(
    start_url,
    link_regex,
    user_agent="",
    proxies=None,
    delay=3,
    max_depth=4,
    num_retries=2,
    cache={},
    max_threads=10,
    scraper_callback=None,
):
    """ Crawl from the given start URLs following links matched by link_regex. In this
        implementation, we do not actually scrape any information.

        args:
            start_url (str or list of strs): web site(s) to start crawl
            link_regex (str): regex to match for links
        kwargs:
            user_agent (str): user agent (default: wswp)
            proxies (list of dicts): a list of possible dicts
                for http / https proxies
                For formatting, see the requests library
            delay (int): seconds to throttle between requests to one domain
                        (default: 3)
            max_depth (int): maximum crawl depth (to avoid traps) (default: 4)
            num_retries (int): # of retries when 5xx error (default: 2)
            cache (dict): cache dict with urls as keys
                          and dicts for responses (default: {})
            scraper_callback: function to be called on url and html content
    """
    crawl_queue = RedisQueue()
    crawl_queue.push(start_url)
    # keep track which URL's have seen before
    robots = {}
    D = Downloader(delay=delay, user_agent=user_agent, proxies=proxies, cache=cache)

    def process_queue():
        while len(crawl_queue):
            url = crawl_queue.pop()
            no_robots = False
            if not url or "http" not in url:
                continue
            domain = "{}://{}".format(urlparse(url).scheme, urlparse(url).netloc)
            rp = robots.get(domain)
            if not rp and domain not in robots:
                robots_url = "{}/robots.txt".format(domain)
                rp = get_robots_parser(robots_url)
                if not rp:
                    # issue finding robots.txt, still crawl
                    no_robots = True
                robots[domain] = rp
            elif domain in robots:
                no_robots = True
            # check url passes robots.txt restrictions
            if no_robots or rp.can_fetch(user_agent, url):
                depth = crawl_queue.get_depth(url)
                if depth == max_depth:
                    print("Skipping %s due to depth" % url)
                    continue
                html = D(url, num_retries=num_retries)
                if not html:
                    continue
                if scraper_callback:
                    links = scraper_callback(url, html) or []
                else:
                    links = []
                # filter for links matching our regular expression
                for link in list(get_links(html, link_regex)) + links:
                    if "http" not in link:
                        link = clean_link(url, domain, link)
                    crawl_queue.push(link)
                    crawl_queue.set_depth(link, depth + 1)
            else:
                print("Blocked by robots.txt:", url)

    # wait for all download threads to finish
    threads = []
    while threads or len(crawl_queue):
        for thread in threads:
            if not thread.is_alive():
                threads.remove(thread)
        while len(threads) < max_threads and crawl_queue:
            # can start some more threads
            thread = threading.Thread(target=process_queue)
            thread.setDaemon(True)  # set daemon so main thread can exit w/ ctrl-c
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        time.sleep(SLEEP_TIME)



def mp_threaded_crawler(*args, **kwargs):
    processes = []
    num_procs = kwargs.pop("num_procs")
    if not num_procs:
        num_procs = multiprocessing.cpu_count()
    for _ in range(num_procs):
        proc = multiprocessing.Process(
            target=threaded_crawler_rq, args=args, kwargs=kwargs
        )
        proc.start()
        processes.append(proc)
    # wait for processes to complete
    for proc in processes:
        proc.join()

def google(keyword, add_url=""):
    driver.get("https://www.google.com/search?q={}&source=lnms&tbm=isch{}".format(keyword, add_url))
    time.sleep(1)
    print('Scrolling down')
    elem = driver.find_element_by_tag_name("body")
    for i in range(60):
        elem.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.3)
    try:
        # btn_more = self.browser.find_element(By.XPATH, '//input[@value="결과 더보기"]')
        self.wait_and_click('//input[@id="smb"]')
        for i in range(60):
            elem.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.2)
    except:
        pass
    photo_grid_boxes = driver.find_elements(By.XPATH, '//div[@class="rg_bx rg_di rg_el ivg-i"]')
    print('Scraping links')
    links = []
    for box in photo_grid_boxes:
        try:
            imgs = box.find_elements(By.TAG_NAME, 'img')
            for img in imgs:
                src = img.get_attribute("src")
                if src[0] != 'd':
                    links.append(src)
        except Exception as e:
            print('[Exception occurred while collecting links from google] {}'.format(e))
    print('Collect links done. Site: {}, Keyword: {}, Total: {}'.format('google', keyword, len(links)))
    driver.close()
    return set(links)

def search_q(driver, name, query):
    firstnameField = driver.find_element_by_name(name)
    actions = ActionChains(driver).click(firstnameField).send_keys(query).send_keys(Keys.RETURN)
    actions.perform()
    time.sleep(3)

agent = CollectLinks()
agent.wait_and_click("//")
# driver = webdriver.Chrome('/usr/local/bin/chromedriver')
driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver')
driver.get("https://google.com")
driver.maximize_window()


#lement = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "q")))
#search_q(driver, "q", "numerator")
google("numerator")
