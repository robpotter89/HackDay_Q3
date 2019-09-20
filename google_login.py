from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException

chrome_options = Options()
chromeOptions = webdriver.ChromeOptions()
user_agent = '"Mozilla/5.0 (Linux; Android 9; Pixel 3 Build/PQ3A.190801.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/76.0.3809.132 Mobile Safari/537.36 GSA/10.49.11.21.arm64"'
chrome_options.add_argument('--headless')
chrome_options.add_argument('--incognito')
chrome_options.add_argument('--user-agent=%s' % user_agent)

CONFIG_FILE = "accounts.config"


def read_all_logins(conf_file):
    f = open(conf_file, "r")
    lines = f.read().splitlines()
    accounts = zip(*(lines[x::4] for x in range(0, 3)))
    f.close()
    return accounts


def google_login(username, password, meta):  # See test_cookies for example on how to use the cookies field from the dictionary
    driver = webdriver.Chrome(options=chrome_options)

    driver.get('https://accounts.google.com/ServiceLogin?hl=en&passive=true&continue=https://www.google.com/')
    user_input = driver.find_element_by_xpath('//div//input[@type="email"]')
    actions = ActionChains(driver).click(user_input).send_keys(username).send_keys(Keys.RETURN)
    actions.perform()

    try:
        pass_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//div//input[@type="password"]'))
            )
    except TimeoutException:
        driver.close()
        return None

    actions = ActionChains(driver).click(pass_input).send_keys(password).send_keys(Keys.RETURN)
    actions.perform()

    try:
        WebDriverWait(driver, 10).until(
            EC.url_matches('https://www.google.com/')
        )
    except TimeoutException:
        driver.close()
        return None

    cookies = driver.get_cookies()

    for cookie in cookies:
        cookie['expiry'] = int(cookie['expiry'])  # expiry being an integer is part of the WebDriver specs

    driver.close()
    return {'username': username, 'cookies': cookies, 'meta': meta}


def test_cookies(c):  # Returns true for valid login cookies
    driver = webdriver.Chrome(options=chrome_options)

    driver.get('https://www.google.com/')  # Note that due to WebDriver specs, the cookie must be added while on the original domain
    driver.delete_all_cookies()

    for d in c:
        driver.add_cookie(d)

    driver.get('https://adssettings.google.com/authenticated')

    try:
        WebDriverWait(driver, 10).until(
            EC.title_is('Ad Settings')
        )
    except TimeoutException:
        driver.close()
        return False

    driver.close()
    return True
