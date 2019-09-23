from google_login import read_all_logins, google_login
from ad_images import get_ad_images_from_url
from data_access import AdLoader

SITES = [
    'https://www.youtube.com/',
    'https://stackoverflow.com/',
    'https://www.reddit.com/',
    'https://mailtester.com/',
    'https://coinmarketcap.com/',
    'https://www.hurriyet.com.tr/',
    'https://www.freepik.com/',
    'https://blog.csdn.net/',
    'https://allegro.pl/',
    'https://bootsnipp.com/'
]


def run():
    ad_loader = AdLoader(index='final')
    accounts = read_all_logins()
    for account in accounts:
        email, password, age, gender = account
        for site in SITES:
            driver = google_login(email, password)
            ad_images_bytes = get_ad_images_from_url(driver, site)
            for ad_image_bytes in ad_images_bytes:
                ad_loader.add_image_bytes(
                    ad_image_bytes, site, email, age, gender, []
                )
