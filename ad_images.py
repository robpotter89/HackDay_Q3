from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep
from six import BytesIO
import base64
from PIL import Image


def get_ad_images_from_url(url):
    ads = []
    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    page_base64_image = ''
    try:
        driver.get(url)
        sleep(5)
        driver.maximize_window()
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

    except Exception as e:
        print("exception", e)

    finally:
        driver.quit()

    ad_base64_images = []
    for ad in ads:
        location = ad[0]
        size = ad[1]
        left = location['x']
        top = location['y']
        right = location['x'] + size['width']
        bottom = location['y'] + size['height']
        output = BytesIO()
        pil_image = Image.open(
            BytesIO(base64.decodebytes(page_base64_image.encode()))
        )
        pil_image = pil_image.crop((left, top, right, bottom))
        pil_image.save(output, format='PNG')
        output.seek(0)
        ad_base64_image = base64.b64encode(output.read())
        ad_base64_images.append(ad_base64_image)

    return ad_base64_images
