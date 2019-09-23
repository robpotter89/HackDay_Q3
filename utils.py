""" Common utilities """
import time
import datetime
from math import ceil
from math import radians
from math import degrees as rad2deg
from math import cos
import random
import re
import regex
import signal
import os
import sys
from sys import exit as clean_exit
from platform import system
from platform import python_version
from subprocess import call
import csv
import sqlite3
import json
from contextlib import contextmanager
from tempfile import gettempdir
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import TimeoutException


def delete_line_from_file(filepath, userToDelete, logger):
    """ Remove user's record from the followed pool file after unfollowing """
    if not os.path.isfile(filepath):
        # in case of there is no any followed pool file yet
        return 0

    try:
        file_path_old = filepath + ".old"
        file_path_Temp = filepath + ".temp"

        with open(filepath, "r") as f:
            lines = f.readlines()

        with open(file_path_Temp, "w") as f:
            for line in lines:
                entries = line.split(" ~ ")
                sz = len(entries)
                if sz == 1:
                    user = entries[0][:-2]
                elif sz == 2:
                    user = entries[1][:-2]
                else:
                    user = entries[1]

                if user == userToDelete:
                    slash_in_filepath = "/" if "/" in filepath else "\\"
                    filename = filepath.split(slash_in_filepath)[-1]
                    logger.info(
                        "\tRemoved '{}' from {} file".format(
                            line.split(",\n")[0], filename
                        )
                    )

                else:
                    f.write(line)

        # File leftovers that should not exist, but if so remove it
        while os.path.isfile(file_path_old):
            try:
                os.remove(file_path_old)

            except OSError as e:
                logger.error("Can't remove file_path_old {}".format(str(e)))
                sleep(5)

        # rename original file to _old
        os.rename(filepath, file_path_old)

        # rename new temp file to filepath
        while os.path.isfile(file_path_Temp):
            try:
                os.rename(file_path_Temp, filepath)

            except OSError as e:
                logger.error(
                    "Can't rename file_path_Temp to filepath {}".format(str(e))
                )
                sleep(5)

        # remove old and temp file
        os.remove(file_path_old)

    except BaseException as e:
        logger.error("delete_line_from_file error {}".format(str(e).encode("utf-8")))


def scroll_bottom(browser, element, range_int):
    # put a limit to the scrolling
    if range_int > 50:
        range_int = 50

    for _ in range(int(range_int / 2)):
        # scroll down the page by 1000 pixels every time
        browser.execute_script("window.scrollBy(0, 1000)")
        # update server calls
        update_activity(browser, state=None)
        sleep(1)

    return


def click_element(browser, element, tryNum=0):
    try:
        # use Selenium's built in click function
        element.click()

        # update server calls after a successful click by selenium
        update_activity(browser, state=None)

    except Exception:
        # click attempt failed
        # try something funky and try again

        if tryNum == 0:
            # try scrolling the element into view
            browser.execute_script(
                "document.getElementsByClassName('"
                + element.get_attribute("class")
                + "')[0].scrollIntoView({ inline: 'center' });"
            )

        elif tryNum == 1:
            # well, that didn't work, try scrolling to the top and then
            # clicking again
            browser.execute_script("window.scrollTo(0,0);")

        elif tryNum == 2:
            # that didn't work either, try scrolling to the bottom and then
            # clicking again
            browser.execute_script("window.scrollTo(0,document.body.scrollHeight);")

        else:
            # try `execute_script` as a last resort
            # print("attempting last ditch effort for click, `execute_script`")
            browser.execute_script(
                "document.getElementsByClassName('"
                + element.get_attribute("class")
                + "')[0].click()"
            )
            # update server calls after last click attempt by JS
            update_activity(browser, state=None)
            # end condition for the recursive function
            return

        # update server calls after the scroll(s) in 0, 1 and 2 attempts
        update_activity(browser, state=None)

        # sleep for 1 second to allow window to adjust (may or may not be
        # needed)
        sleep_actual(1)

        tryNum += 1

        # try again!
        click_element(browser, element, tryNum)


def format_number(number):
    """
    Format number. Remove the unused comma. Replace the concatenation with
    relevant zeros. Remove the dot.

    :param number: str

    :return: int
    """
    formatted_num = number.replace(",", "")
    formatted_num = re.sub(
        r"(k)$", "00" if "." in formatted_num else "000", formatted_num
    )
    formatted_num = re.sub(
        r"(m)$", "00000" if "." in formatted_num else "000000", formatted_num
    )
    formatted_num = formatted_num.replace(".", "")
    return int(formatted_num)



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
        # navigate faster

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


@contextmanager
def interruption_handler(
    threaded=False,
    SIG_type=signal.SIGINT,
    handler=signal.SIG_IGN,
    notify=None,
    logger=None,
):
    """ Handles external interrupt, usually initiated by the user like
    KeyboardInterrupt with CTRL+C """
    if notify is not None and logger is not None:
        logger.warning(notify)

    if not threaded:
        original_handler = signal.signal(SIG_type, handler)

    try:
        yield

    finally:
        if not threaded:
            signal.signal(SIG_type, original_handler)


def remove_duplicates(container, keep_order, logger):
    """ Remove duplicates from all kinds of data types easily """
    # add support for data types as needed in future
    # currently only 'list' data type is supported
    if isinstance(container, list):
        if keep_order is True:
            result = sorted(set(container), key=container.index)

        else:
            result = set(container)

    else:
        if not logger:
            logger = Settings.logger

        logger.warning(
            "The given data type- '{}' is not supported "
            "in `remove_duplicates` function, yet!".format(type(container))
        )
        result = container

    return result


def emergency_exit(browser, username, logger):
    """ Raise emergency if the is no connection to server OR if user is not
    logged in """
    server_address = "instagram.com"
    connection_state = ping_server(server_address, logger)
    if connection_state is False:
        return True, "not connected"

    # check if the user is logged in
    auth_method = "activity counts"
    login_state = check_authorization(browser, username, auth_method, logger)
    if login_state is False:
        return True, "not logged in"

    return False, "no emergency"


@contextmanager
def new_tab(browser):
    """ USE once a host tab must remain untouched and yet needs extra data-
    get from guest tab """
    try:
        # add a guest tab
        browser.execute_script("window.open()")
        sleep(1)
        # switch to the guest tab
        browser.switch_to.window(browser.window_handles[1])
        sleep(2)
        yield

    finally:
        # close the guest tab
        browser.execute_script("window.close()")
        sleep(1)
        # return to the host tab
        browser.switch_to.window(browser.window_handles[0])
        sleep(2)


def explicit_wait(browser, track, ec_params, logger, timeout=35, notify=True):
    """
    Explicitly wait until expected condition validates

    :param browser: webdriver instance
    :param track: short name of the expected condition
    :param ec_params: expected condition specific parameters - [param1, param2]
    :param logger: the logger instance
    """
    if not isinstance(ec_params, list):
        ec_params = [ec_params]

    # find condition according to the tracks
    if track == "VOEL":
        elem_address, find_method = ec_params
        ec_name = "visibility of element located"

        find_by = (
            By.XPATH
            if find_method == "XPath"
            else By.CSS_SELECTOR
            if find_method == "CSS"
            else By.CLASS_NAME
        )
        locator = (find_by, elem_address)
        condition = ec.visibility_of_element_located(locator)

    elif track == "TC":
        expect_in_title = ec_params[0]
        ec_name = "title contains '{}' string".format(expect_in_title)

        condition = ec.title_contains(expect_in_title)

    elif track == "PFL":
        ec_name = "page fully loaded"
        condition = lambda browser: browser.execute_script(
            "return document.readyState"
        ) in ["complete" or "loaded"]

    elif track == "SO":
        ec_name = "staleness of"
        element = ec_params[0]

        condition = ec.staleness_of(element)

    # generic wait block
    try:
        wait = WebDriverWait(browser, timeout)
        result = wait.until(condition)

    except TimeoutException:
        if notify is True:
            logger.info(
                "Timed out with failure while explicitly waiting until {}!\n".format(
                    ec_name
                )
            )
        return False

    return result


def get_current_url(browser):
    """ Get URL of the loaded webpage """
    try:
        current_url = browser.execute_script("return window.location.href")

    except WebDriverException:
        try:
            current_url = browser.current_url

        except WebDriverException:
            current_url = None

    return current_url


def is_page_available(browser, logger):
    """ Check if the page is available and valid """
    expected_keywords = ["Page Not Found", "Content Unavailable"]
    page_title = get_page_title(browser, logger)

    if any(keyword in page_title for keyword in expected_keywords):
        reload_webpage(browser)
        page_title = get_page_title(browser, logger)

        if any(keyword in page_title for keyword in expected_keywords):
            if "Page Not Found" in page_title:
                logger.warning(
                    "The page isn't available!\t~the link may be broken, "
                    "or the page may have been removed..."
                )

            elif "Content Unavailable" in page_title:
                logger.warning(
                    "The page isn't available!\t~the user may have blocked " "you..."
                )

            return False

    return True


@contextmanager
def smart_run(session, threaded=False):
    try:
        session.login()
        yield
    except NoSuchElementException:
        # The problem is with a change in IG page layout
        log_file = "{}.html".format(time.strftime("%Y%m%d-%H%M%S"))
        file_path = os.path.join(gettempdir(), log_file)

        with open(file_path, "wb") as fp:
            fp.write(session.browser.page_source.encode("utf-8"))

        print(
            "{0}\nIf raising an issue, "
            "please also upload the file located at:\n{1}\n{0}".format(
                "*" * 70, file_path
            )
        )
    except KeyboardInterrupt:
        clean_exit("You have exited successfully.")
    finally:
        session.end(threaded_session=threaded)


def reload_webpage(browser):
    """ Reload the current webpage """
    browser.execute_script("location.reload()")
    update_activity(browser, state=None)
    sleep(2)

    return True


def get_page_title(browser, logger):
    """ Get the title of the webpage """
    # wait for the current page fully load to get the correct page's title
    explicit_wait(browser, "PFL", [], logger, 10)

    try:
        page_title = browser.title

    except WebDriverException:
        try:
            page_title = browser.execute_script("return document.title")

        except WebDriverException:
            try:
                page_title = browser.execute_script(
                    "return document.getElementsByTagName('title')[0].text"
                )

            except WebDriverException:
                logger.info("Unable to find the title of the page :(")
                return None

    return page_title


def click_visibly(browser, element):
    """ Click as the element become visible """
    if element.is_displayed():
        click_element(browser, element)

    else:
        browser.execute_script(
            "arguments[0].style.visibility = 'visible'; "
            "arguments[0].style.height = '10px'; "
            "arguments[0].style.width = '10px'; "
            "arguments[0].style.opacity = 1",
            element,
        )
        # update server calls
        update_activity(browser, state=None)

        click_element(browser, element)

    return True


def get_action_delay(action):
    """ Get the delay time to sleep after doing actions """
    defaults = {"like": 2, "comment": 2, "follow": 3, "unfollow": 10, "story": 3}
    config = Settings.action_delays

    if (
        not config
        or action not in config
        or config["enabled"] is not True
        or config[action] is None
        or isinstance(config[action], (int, float)) is not True
    ):
        return defaults[action]

    else:
        custom_delay = config[action]

    # randomize the custom delay in user-defined range
    if (
        config["randomize"] is True
        and isinstance(config["random_range"], tuple)
        and len(config["random_range"]) == 2
        and all(
            (isinstance(i, (type(None), int, float)) for i in config["random_range"])
        )
        and any(not isinstance(i, type(None)) for i in config["random_range"])
    ):
        min_range = config["random_range"][0]
        max_range = config["random_range"][1]

        if not min_range or min_range < 0:
            min_range = 100

        if not max_range or max_range < 0:
            max_range = 100

        if min_range > max_range:
            a = min_range
            min_range = max_range
            max_range = a

        custom_delay = random.uniform(
            custom_delay * min_range / 100, custom_delay * max_range / 100
        )

    if custom_delay < defaults[action] and config["safety_match"] is not False:
        return defaults[action]

    return custom_delay


def deform_emojis(text):
    """ Convert unicode emojis into their text form """
    new_text = ""
    emojiless_text = ""
    data = regex.findall(r"\X", text)
    emojis_in_text = []

    for word in data:
        if any(char in UNICODE_EMOJI for char in word):
            word_emoji = emoji.demojize(word).replace(":", "").replace("_", " ")
            if word_emoji not in emojis_in_text:  # do not add an emoji if
                # already exists in text
                emojiless_text += " "
                new_text += " ({}) ".format(word_emoji)
                emojis_in_text.append(word_emoji)
            else:
                emojiless_text += " "
                new_text += " "  # add a space [instead of an emoji to be
                # duplicated]

        else:
            new_text += word
            emojiless_text += word

    emojiless_text = remove_extra_spaces(emojiless_text)
    new_text = remove_extra_spaces(new_text)

    return new_text, emojiless_text


def extract_text_from_element(elem):
    """ As an element is valid and contains text, extract it and return """
    if elem and hasattr(elem, "text") and elem.text:
        text = elem.text
    else:
        text = None

    return text


def truncate_float(number, precision, round=False):
    """ Truncate (shorten) a floating point value at given precision """

    # don't allow a negative precision [by mistake?]
    precision = abs(precision)

    if round:
        # python 2.7+ supported method [recommended]
        short_float = round(number, precision)

        # python 2.6+ supported method
        """short_float = float("{0:.{1}f}".format(number, precision))
        """

    else:
        operate_on = 1  # returns the absolute number (e.g. 11.0 from 11.456)

        for _ in range(precision):
            operate_on *= 10

        short_float = float(int(number * operate_on)) / operate_on

    return short_float


def get_time_until_next_month():
    """ Get total seconds remaining until the next month """
    now = datetime.datetime.now()
    next_month = now.month + 1 if now.month < 12 else 1
    year = now.year if now.month < 12 else now.year + 1
    date_of_next_month = datetime.datetime(year, next_month, 1)

    remaining_seconds = (date_of_next_month - now).total_seconds()

    return remaining_seconds


def remove_extra_spaces(text):
    """ Find and remove redundant spaces more than 1 in text """
    new_text = re.sub(r" {2,}", " ", text)

    return new_text


def has_any_letters(text):
    """ Check if the text has any letters in it """
    # result = re.search("[A-Za-z]", text)   # works only with english letters
    result = any(
        c.isalpha() for c in text
    )  # works with any letters - english or non-english

    return result


def save_account_progress(browser, username, logger):
    """
    Check account current progress and update database

    Args:
        :browser: web driver
        :username: Account to be updated
        :logger: library to log actions
    """
    logger.info("Saving account progress...")
    followers, following = get_relationship_counts(browser, username, logger)

    # save profile total posts
    posts = getUserData("graphql.user.edge_owner_to_timeline_media.count", browser)

    try:
        # DB instance
        db, id = get_database()
        conn = sqlite3.connect(db)
        with conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            sql = (
                "INSERT INTO accountsProgress (profile_id, followers, "
                "following, total_posts, created, modified) "
                "VALUES (?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S'), "
                "strftime('%Y-%m-%d %H:%M:%S'))"
            )
            cur.execute(sql, (id, followers, following, posts))
            conn.commit()
    except Exception:
        logger.exception("message")


def get_epoch_time_diff(time_stamp, logger):
    try:
        # time diff in seconds from input to now
        log_time = datetime.datetime.strptime(time_stamp, "%Y-%m-%d %H:%M")

        former_epoch = (log_time - datetime.datetime(1970, 1, 1)).total_seconds()
        cur_epoch = (
            datetime.datetime.now() - datetime.datetime(1970, 1, 1)
        ).total_seconds()

        return cur_epoch - former_epoch
    except ValueError:
        logger.error("Error occurred while reading timestamp value from database")
        return None


def is_follow_me(browser, person=None):
    # navigate to profile page if not already in it
    if person:
        user_link = "https://www.instagram.com/{}/".format(person)
        web_address_navigator(browser, user_link)

    return getUserData("graphql.user.follows_viewer", browser)


def get_users_from_dialog(old_data, dialog):
    """
    Prepared to work specially with the dynamic data load in the 'Likes'
    dialog box
    """

    user_blocks = dialog.find_elements_by_tag_name("a")
    loaded_users = [
        extract_text_from_element(u)
        for u in user_blocks
        if extract_text_from_element(u)
    ]
    new_data = old_data + loaded_users
    new_data = remove_duplicates(new_data, True, None)

    return new_data


def progress_tracker(current_value, highest_value, initial_time, logger):
    """ Provide a progress tracker to keep value updated until finishes """
    if current_value is None or highest_value is None or highest_value == 0:
        return

    try:
        real_time = time.time()
        progress_percent = int((current_value / highest_value) * 100)
        show_logs = Settings.show_logs

        elapsed_time = real_time - initial_time
        elapsed_formatted = truncate_float(elapsed_time, 2)
        elapsed = (
            "{} seconds".format(elapsed_formatted)
            if elapsed_formatted < 60
            else "{} minutes".format(truncate_float(elapsed_formatted / 60, 2))
        )

        eta_time = abs(
            (elapsed_time * 100) / (progress_percent if progress_percent != 0 else 1)
            - elapsed_time
        )
        eta_formatted = truncate_float(eta_time, 2)
        eta = (
            "{} seconds".format(eta_formatted)
            if eta_formatted < 60
            else "{} minutes".format(truncate_float(eta_formatted / 60, 2))
        )

        tracker_line = "-----------------------------------"
        filled_index = int(progress_percent / 2.77)
        progress_container = (
            "[" + tracker_line[:filled_index] + "+" + tracker_line[filled_index:] + "]"
        )
        progress_container = (
            progress_container[: filled_index + 1].replace("-", "=")
            + progress_container[filled_index + 1 :]
        )

        total_message = (
            "\r  {}/{} {}  {}%    "
            "|> Elapsed: {}    "
            "|> ETA: {}      ".format(
                current_value,
                highest_value,
                progress_container,
                progress_percent,
                elapsed,
                eta,
            )
        )

        if show_logs is True:
            sys.stdout.write(total_message)
            sys.stdout.flush()

    except Exception as exc:
        if not logger:
            logger = Settings.logger

        logger.info(
            "Error occurred with Progress Tracker:\n{}".format(str(exc).encode("utf-8"))
        )


def close_dialog_box(browser):
    """ Click on the close button spec. in the 'Likes' dialog box """

    try:
        close = browser.find_element_by_xpath(
            read_xpath("class_selectors", "likes_dialog_close_xpath")
        )

        click_element(browser, close)

    except NoSuchElementException:
        pass



def get_bounding_box(
    latitude_in_degrees, longitude_in_degrees, half_side_in_miles, logger
):
    if half_side_in_miles == 0:
        logger.error("Check your Radius its lower then 0")
        return {}
    if latitude_in_degrees < -90.0 or latitude_in_degrees > 90.0:
        logger.error("Check your latitude should be between -90/90")
        return {}
    if longitude_in_degrees < -180.0 or longitude_in_degrees > 180.0:
        logger.error("Check your longtitude should be between -180/180")
        return {}
    half_side_in_km = half_side_in_miles * 1.609344
    lat = radians(latitude_in_degrees)
    lon = radians(longitude_in_degrees)

    radius = 6371
    # Radius of the parallel at given latitude
    parallel_radius = radius * cos(lat)

    lat_min = lat - half_side_in_km / radius
    lat_max = lat + half_side_in_km / radius
    lon_min = lon - half_side_in_km / parallel_radius
    lon_max = lon + half_side_in_km / parallel_radius

    lat_min = rad2deg(lat_min)
    lon_min = rad2deg(lon_min)
    lat_max = rad2deg(lat_max)
    lon_max = rad2deg(lon_max)

    bbox = {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max,
    }

    return bbox


def take_rotative_screenshot(browser, logfolder):
    """
        Make a sequence of screenshots, based on hour:min:secs
    """
    global next_screenshot

    if next_screenshot == 1:
        browser.save_screenshot("{}screenshot_1.png".format(logfolder))
    elif next_screenshot == 2:
        browser.save_screenshot("{}screenshot_2.png".format(logfolder))
    else:
        browser.save_screenshot("{}screenshot_3.png".format(logfolder))
        next_screenshot = 0
        # sum +1 next

    # update next
    next_screenshot += 1


def get_query_hash(browser, logger):
    """ Load Instagram JS file and find query hash code """
    link = "https://www.instagram.com/static/bundles/es6/Consumer.js/1f67555edbd3.js"
    web_address_navigator(browser, link)
    page_source = browser.page_source
    # locate pattern value from JS file
    # sequence of 32 words and/or numbers just before ,n=" value
    hash = re.findall('[a-z0-9]{32}(?=",n=")', page_source)
    if hash:
        return hash[0]
    else:
        logger.warn("Query Hash not found")


class CustomizedArgumentParser(ArgumentParser):
    """
     Subclass ArgumentParser in order to turn off
    the abbreviation matching on older pythons.

    `allow_abbrev` parameter was added by Python 3.5 to do it.
    Thanks to @paul.j3 - https://bugs.python.org/msg204678 for this solution.
    """

    def _get_option_tuples(self, option_string):
        """
         Default of this method searches through all possible prefixes
        of the option string and all actions in the parser for possible
        interpretations.

        To view the original source of this method, running,
        ```
        import inspect; import argparse; inspect.getsourcefile(argparse)
        ```
        will give the location of the 'argparse.py' file that have this method.
        """
        return []
