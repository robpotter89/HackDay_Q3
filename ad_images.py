from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep
from six import BytesIO
import base64
from PIL import Image

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Safari/537.36'


def get_ad_images_from_url(url, debug=False):
    ads = []
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--user-agent=%s' % USER_AGENT)
    driver = webdriver.Chrome(options=chrome_options)
    page_pil_image = None
    try:
        driver.get(url)
        sleep(5)
        driver.set_window_size(2160, 4096)
        sleep(1)
        all_iframes = driver.find_elements_by_tag_name("iframe")
        for iframe in all_iframes:
            try:
                iframe_location = iframe.location
                iframe_size = iframe.size
                driver.switch_to.frame(iframe)
                iframe_html = (
                    driver.find_elements_by_xpath("/*")[0].get_attribute(
                        'outerHTML'
                    )
                )
                is_ad = 'tpc.googlesyndication' in iframe_html
                if is_ad:
                    ads.append((iframe_location, iframe_size))

            except Exception as e:
                print("exception", e)

            finally:
                driver.switch_to.default_content()

        page_base64_image = driver.get_screenshot_as_base64()
        page_pil_image = Image.open(
            BytesIO(base64.decodebytes(page_base64_image.encode()))
        )
        if debug:
            page_pil_image.show()

    except Exception as e:
        print("exception", e)

    finally:
        driver.quit()

    ad_base64_images = []
    if page_pil_image:
        for ad in ads:
            location = ad[0]
            size = ad[1]
            left = location['x']
            top = location['y']
            right = location['x'] + size['width']
            bottom = location['y'] + size['height']
            output = BytesIO()
            ad_pil_image = page_pil_image.crop((left, top, right, bottom))
            if debug:
                ad_pil_image.show()

            ad_pil_image.save(output, format='PNG')
            output.seek(0)
            ad_base64_image = base64.b64encode(output.read())
            ad_base64_images.append(ad_base64_image)

    return ad_base64_images
