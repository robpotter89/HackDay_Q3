from selenium import webdriver
import stat
import re
from collections import OrderedDict
from selenium.common import exceptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from time import sleep
import sys, argparse, os
import string
import time
from contextlib import contextmanager, ContextDecorator

mine = os.path.abspath(os.path.dirname(sys.argv[0]))


class Browser:
    """

    **Constructor**

    :__init__(showWindow = True):
        The constructor takes showWindow flag as argument which Defaults to False. If it is set to true , all browser happen without showing up any GUI window .


    Object attributes:  Key , errors

    :Key:
        - It contains the constants for all the special keys in the keyboard which can be used in the *press* method

    errors:
        - It is a list containing all the errors which might have occured during performing an action like click , type etc

    """

    def __init__(self, showWindow=True):
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")

        if not showWindow:
            options.set_headless(headless=True)

        if sys.platform == "linux" or sys.platform == "linux2":
            driverfilename = "/home/silas/chromedriver"
        elif sys.platform == "win32":
            driverfilename = "chrome_windows.exe"
        elif sys.platform == "darwin":
            driverfilename = "chrome_mac"
        driverpath = "/usr/local/bin/chromedriver"

        self.driver = webdriver.Chrome(
            executable_path=driverpath, chrome_options=options
        )
        self.Key = Keys
        self.errors = list()
        [
            setattr(self, function, getattr(self.driver, function))
            for function in [
                "add_cookie",
                "delete_all_cookies",
                "delete_cookie",
                "execute_script",
                "execute_async_script",
                "fullscreen_window",
                "get_cookie",
                "get_cookies",
                "get_log",
                "get_network_conditions",
                "get_screenshot_as_base64",
                "get_screenshot_as_file",
                "get_screenshot_as_png",
                "get_window_position",
                "get_window_rect",
                "get_window_size",
                "maximize_window",
                "minimize_window",
                "implicitly_wait",
                "quit",
                "refresh",
                "save_screenshot",
                "set_network_conditions",
                "set_page_load_timeout",
                "set_script_timeout",
                "set_window_position",
                "set_window_rect",
                "start_client",
                "start_session",
                "stop_client",
                "switch_to_alert",
            ]
        ]

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.close()

    def close_current_tab(self):
        """Closes the current tab which the driver is controlling"""
        self.driver.close()

    def get_current_url(self):
        """Get the curren url of the webpage """
        return self.driver.current_url

    def get_current_window_handle(self):
        """get the window handle of the current window or tab which the web driver is controlling"""
        return self.driver.current_window_handle

    def close_browser(self):
        """CLose browser and kill child processes"""
        return self.driver.quit()

    def close_browser(self):
        """CLose browser and kill child processes"""
        return self.driver.quit()

    def get_application_cache(self):
        """Get application cache object to interact with the browser app cache """
        return self.driver.application_cache

    def get_desired_capabilities(self):
        """returns the drivers current desired capabilities being used"""
        return self.driver.desired_capabilities

    def get_log_types(self):
        """Get supported log types to be used by the get_log method"""
        return self.driver.log_types

    def get_title(self):
        """Gets the title of the current webpage """
        return self.driver.title

    def get_page_source(self):
        """ Gets the html source code for the current webpage """
        return self.driver.page_source

    def find_elements(
        self,
        text="",
        tag="button",
        id="",
        classname="",
        number=1,
        css_selector="",
        xpath="",
        loose_match=True,
    ):
        """Returns a list of elements that best fit the given parameters"""
        return self.__find_element(
            text, tag, classname, id, number, css_selector, xpath, loose_match
        )

    def exists(
        self,
        text="",
        tag="button",
        id="",
        classname="",
        number=1,
        css_selector="",
        xpath="",
        loose_match=True,
    ):
        """
        Check if an element exists or not.

        Returns True if any element that best fits the given parameters exists.
        Return False if no such element exists.


        :Args:
            - text  : The text of the element.
            - tag   : The html tag of the element to look for (eg : button , a ) , defaults to 'button'
            - id    : id of the element
            - classname : Any class of the element to search for.
            - number : if there are multiple elements matching the criteria of other parameters , number specifies which element to select for the operation. This defaults to 1 and selects the first element to perform the action .
            - multiple : if True , the specified action is performed on all the elements matching the criteria and not just the first element . If it is true , number parameter is ignored . Defaults to False
            - css_selector : css_selector expression for better control over selecting the elements to perform the action.
            - xpath : xpath expression for better control over selecting the elements to perform the action.
            - loose_match :  If loose_match is True then if no element of specified tag is found  , all other tags are considered to search for the text , else only specified tag is considered for matching elements. Defaults to True


        :Usage :

        .. code-block:: python

           driver = Browser()
           driver.go_to('google.com')

           driver.exists('Sign In')  #Returns True
           driver.exists('yahoo')  #Returns False
        """

        return (
            True
            if len(
                self.__find_element(
                    text, tag, classname, id, number, css_selector, xpath, loose_match
                )
            )
            else False
        )

    def quick_search(self, name, query):
        firstnameField = self.driver.find_element_by_name(name)
        actions = (
            ActionChains(self.driver)
            .click(firstnameField)
            .send_keys(query)
            .send_keys(Keys.RETURN)
        )
        actions.perform()
        time.sleep(3)

    def __find_element(
        self, text, tag, classname, id, number, css_selector, xpath, loose_match
    ):
        """Returns a list of elements that best fit the given parameters"""

        self.element_to_score = OrderedDict()
        self.element_to_score_id_set = set()
        if tag == "link":
            tag = "a"

        def add_to_init_text_matches_score(text_matches_elements, score):
            """Extends a dictionary and maps it with the text_matched_element with the score"""

            for element in text_matches_elements:
                try:
                    if (
                        (not element.is_displayed())
                        or (
                            not element.is_enabled()
                            and tag in ["input", "button", "a", "textarea"]
                        )
                        or (element.get_attribute("hidden") == "true")
                        or (
                            element.tag_name == "input"
                            and element.get_attribute("type") == "hidden"
                        )
                    ):
                        continue

                    # accessing id or class attribute of stale element("like that input tag which in is google.com page ") raises this exception
                    element_tag_name = element.tag_name

                except exceptions.StaleElementReferenceException as E:
                    self.__set_error(E, element)
                    continue

                if element.id in self.element_to_score_id_set:
                    """ No need to call the max method if the method call is ordered from most specific to least specific which naturally has the max score if the element is already present """
                    self.element_to_score[element] = max(
                        self.element_to_score[element], score
                    )

                else:
                    self.element_to_score[element] = score
                    self.element_to_score_id_set.add(element.id)

        def element_fetch_helper(xpath, score):
            add_to_init_text_matches_score(
                self.driver.find_elements_by_xpath(xpath), score
            )

        def find_input_element_for_label(elementlist, score):
            """This method finds the input tag elements by taking in the label elements and assigns the score argument to the new found input elements and puts them in the  elemenet to score mapping """

            for element in elementlist:
                if not element.is_displayed:
                    continue

                possible_input_id = element.get_attribute("for")
                try:
                    element_fetch_helper(
                        ("//body//input[@id='{}']".format(possible_input_id)), score
                    )

                    add_to_init_text_matches_score(
                        element.find_elements_by_xpath(
                            "../input[contains(translate(@id , '{}' ,'{}' ) , '{}')]".format(
                                text.upper(), text.lower(), text.lower()
                            )
                        ),
                        score - 5,
                    )

                    add_to_init_text_matches_score(
                        element.find_elements_by_xpath("/./preceding::input"), score - 7
                    )

                    element_fetch_helper(
                        ("//body//input[@name='{}']".format(possible_input_id)),
                        score - 6,
                    )

                    add_to_init_text_matches_score(
                        element.find_elements_by_xpath("../input"), score - 10
                    )

                except exceptions.NoSuchElementException as E:
                    self.__set_error(E, element)

        def handle_input_tag():
            if text:
                for test_attr in ["@value", "@placeholder", "name", "@aria-label"]:
                    element_fetch_helper(
                        ("//body//input[{}='{}']".format(test_attr, text)), score=45
                    )
                    element_fetch_helper(
                        ("//body//input[contains( {} , '{}')]".format(test_attr, text)),
                        score=37,
                    )
                    element_fetch_helper(
                        (
                            "//body//input[contains(translate( {} , '{}' , '{}' ) , '{}')]".format(
                                test_attr, text.upper(), text.lower(), text.lower()
                            )
                        ),
                        score=33,
                    )

                find_input_element_for_label(
                    self.driver.find_elements_by_xpath(
                        "//body//label[text()='{}']".format(text)
                    ),
                    score=45,
                )

                find_input_element_for_label(
                    self.driver.find_elements_by_xpath(
                        "//body//label[contains( text() , '{}')]".format(text)
                    ),
                    score=37,
                )

                find_input_element_for_label(
                    self.driver.find_elements_by_xpath(
                        "//body//label[contains(translate( text() , '{}' , '{}' ) , '{}')]".format(
                            text.upper(), text.lower(), text.lower()
                        )
                    ),
                    score=33,
                )

            else:
                element_fetch_helper("//body//{}".format(tag), score=40)

        def handle_button_or_link_tag(tagvar):
            if text:
                element_fetch_helper(
                    ("//body//{}[text()='{}']".format(tagvar, text)), score=45
                )
                element_fetch_helper(
                    ("//body//{}//*[text()='{}']".format(tagvar, text)), score=45
                )

                add_to_init_text_matches_score(
                    self.driver.find_elements_by_link_text("{}".format(text)), score=43
                )

                element_fetch_helper(
                    ("//body//{}[contains(text() , '{}')]".format(tagvar, text)),
                    score=37,
                )
                element_fetch_helper(
                    ("//body//{}//*[contains(text() , '{}')]".format(tagvar, text)),
                    score=37,
                )

                element_fetch_helper(
                    (
                        "//body//{}[contains(translate(text() , '{}' , '{}' ) , '{}')]".format(
                            tagvar, text.upper(), text.lower(), text.lower()
                        )
                    ),
                    score=33,
                )
                element_fetch_helper(
                    (
                        "//body//{}//*[contains(translate(text() , '{}' , '{}' ) , '{}')]".format(
                            tagvar, text.upper(), text.lower(), text.lower()
                        )
                    ),
                    score=33,
                )

            else:
                element_fetch_helper(("//body//{}".format(tagvar)), score=40)

        def handle_loose_check():
            """This method must only be used iff no element based on the given text input is found ! """
            if text:
                element_fetch_helper("//body//*[@value='{}']".format(text), score=30)
                element_fetch_helper("//body//*[text()='{}']".format(text), score=30)

                element_fetch_helper(
                    ("//body//*[contains(text() , '{}')]".format(text)), score=27
                )

                element_fetch_helper(
                    (
                        "//body//*[contains(translate(text() , '{}' , '{}' ) , '{}' )]".format(
                            text.upper(), text.lower(), text.lower()
                        )
                    ),
                    score=25,
                )

        if css_selector:
            add_to_init_text_matches_score(
                self.driver.find_elements_by_css_selector(css_selector), 80
            )

        if xpath:
            add_to_init_text_matches_score(
                self.driver.find_elements_by_xpath(xpath), 100
            )

        if not text and tag:
            element_fetch_helper(("//body//{}".format(tag)), score=50)

        elif tag:
            element_fetch_helper(
                ("//body//{}[@value='{}']".format(tag, text)), score=50
            )
            element_fetch_helper(
                ("//body//{}[text()='{}']".format(tag, text)), score=50
            )
            element_fetch_helper(
                ("//body//{}[contains(text() , '{}') ]".format(tag, text)), score=49
            )
            element_fetch_helper(
                (
                    "//body//{0}[contains(translate(text()  ,'{1}', '{2}') , '{2}') ]".format(
                        tag, text.upper(), text.lower()
                    )
                ),
                score=48,
            )

        if text.lower() in "your password":
            element_fetch_helper(
                "//body//input[contains(@name , '{}') ]".format("password"), score=47
            )

        if text.lower() in ["username", "email", "login"] and tag == "input":
            element_fetch_helper(
                """//body//input[contains(translate(@name , 'USERNAME' , 'username' )  , 'username') or contains(translate(@name ,'EMAIL' , 'email' ) , 'email') or contains(translate(@name , 'LOGIN' , 'login'  ) , 'login' ) or contains(translate(@type , 'EMAIL' , 'email') , 'email')] """,
                53,
            )

        if tag == "input":
            handle_input_tag()

        if tag == "button":
            handle_button_or_link_tag(tag)

            if len(self.element_to_score.keys()) == 0:
                handle_input_tag()
            if len(self.element_to_score.keys()) == 0:
                handle_button_or_link_tag("a")

        if id:
            add_to_init_text_matches_score(self.driver.find_elements_by_id(id), 100)
        if classname:
            add_to_init_text_matches_score(
                self.driver.find_elements_by_class_name(classname), 50
            )

        if not len(self.element_to_score.keys()) and loose_match:
            handle_loose_check()

        if not len(self.element_to_score.keys()):
            self.__set_error(
                "Element not found ! ",
                message="There is no element that matches your search criteria.",
            )
            return []

        for element in self.element_to_score.keys():
            score = self.element_to_score.get(element)

            # Check ID
            if id and id == element.get_attribute("id"):
                score += 100

            # Check Class
            if classname and classname in element.get_attribute("class").split():
                score += 50

            # Check element tag and check for button or anchor  or input or textarea
            if (
                tag.lower() in ["button", "link"]
                and element.tag_name in ["button", "a"]
                or (tag.lower() == "input" and "input" == element.tag_name)
            ):
                score += 35

            # If user doesn't enter any tag [stick to default i.e button for click and input for type method ]
            if tag in ["button", "input"] and element.tag_name in [
                "button",
                "a",
                "input",
            ]:
                score += 30

            self.element_to_score[element] = score

        max_score = max(self.element_to_score.values())
        max_scored_elements = [
            element
            for element in self.element_to_score.keys()
            if (self.element_to_score[element] == max_score)
        ]

        self._max_score_elements_ = max_scored_elements
        self._max_score_ = max_score

        return self._max_score_elements_

    def __set_error(self, Exceptionerror, element=None, message=""):
        """Set the error in case of any exception occured whenever performing any action like click or type """
        self.errors.append(
            {"Exceptionerror": Exceptionerror, "element": element, "message": message}
        )

    def __reset_error(self):
        self.errors = list()

    def find_cookie(self, name):
        """Gets the specified cookie from the current session"""
        return self.driver.get_cookie(name)

    def find_cookie(self, name):
        """Gets the specified cookie from the current session"""
        return self.driver.get_cookie(name)

    def cookies(self):
        cookies = self.driver.get_cookies()
        return cookies

    def get_total_tabs(self):
        """Gets the total number of tabs or windows that is currently open """
        return len(self.driver.window_handles)

    def switch_to_tab(self, number):
        """Switch to the tab corresponding to the number argument. The tabs are numbered in the order that they are opened by the web driver.
So changing the order of the tabs in the browser won't change the tab numbers.
        """
        assert (
            number <= len(self.driver.window_handles) and number > 0
        ), "Tab number must be less than or equal to the total number of tabs"

        self.driver.switch_to_window(self.driver.window_handles[number - 1])

    def go_back(self):
        """Go back to the previous URL.
It's same as clicking the back button in browser .
        """
        self.driver.back()

    def go_forward(self):
        """It's same as clicking the forward button in the browser"""
        self.driver.forward()

    def go_to(self, url):
        """Open the webpage corresponding to the url given in the parameter.

If the url doesn't contain the protocol of the url  , then by default https is considered

        """
        if not re.match("\w+://.*", url):
            if url[:4] == "www.":
                url = url[4:]
            url = "https://www." + url

        self.driver.get(url)

    def click(
        self,
        text="",
        tag="button",
        id="",
        classname="",
        number=1,
        css_selector="",
        xpath="",
        loose_match=True,
        multiple=False,
    ):
        """
       Clicks one or more elements on the webpage.

        :Args:
            - text: The text of the element that needs to be clicked.
            - tag: The html tag of the element to be clicked (eg: button, a), defaults to 'button'.
            - id: id of the element
            - classname: Any class of the element to consider while selecting the element to click.
            - number: If there are multiple elements matching the criteria of other parameters, number specifies which element to select for the operation. This defaults to 1 and selects the first element to perform the action.
            - multiple: If True, the specified action is performed on all the elements matching the criteria and not just the first element. If it is true, number parameter is ignored. Defaults to False
            - css_selector: css_selector expression for better control over selecting the elements to perform the action.
            - xpath: xpath expression for better control over selecting the elements to perform the action.
            - loose_match: If loose_match is True then if no element of specified tag is found, all other tags are considered to search for the text, else only specified tag is considered for matching elements. Defaults to True

        :Usage:

        .. code-block:: python

           driver = Browser()
           driver.go_to('google.com')

           driver.click('Sign In')
           driver.click('Sign In' , tag='span' )
           driver.click(id = 'elementid')

           # if there are multiple elements matching the text "NEXT" , then 2'nd element is clicked (since number paramter is 2 ) .
           driver.click("NEXT" , tag='span' , number = 2 )

        """

        self.__reset_error()

        if not (text or id or classname or css_selector or xpath):
            ActionChains(self.driver).click().perform()
            return

        maxElements = self.__find_element(
            text, tag, classname, id, number, css_selector, xpath, loose_match
        )

        temp_element_index_ = 1

        for element in maxElements:
            try:
                if element.is_displayed() and element.is_enabled():
                    if (number == temp_element_index_) or multiple:
                        element.click()
                        if not multiple:
                            break
                    temp_element_index_ += 1

            except Exception as E:
                self.__set_error(
                    E,
                    element,
                    """ tagname : {} , id : {}  , classname : {} , id_attribute : {}
                """.format(
                        element.tag_name,
                        element.id,
                        element.get_attribute("class"),
                        element.get_attribute("id"),
                    ),
                )

    def scrolly(self, amount):
        """Scroll vertically by the specified amount

        :Args:
            - amount: positive integer for scrolling down or negative integer for scrolling up

        :Usage:

        .. code-block:: python

           scrolly(100)
           scrolly(-200)
        """
        assert isinstance(amount, int)
        self.driver.execute_script("window.scrollBy(0, {})".format(amount))

    def scrollx(self, amount):
        """Scroll horizontally by the specified amount
        :Args:
            - amount: positive integer for scrolling right or negative integer for scrolling left
        :Usage:
        .. code-block:: python
           scrollx(100)
           scrollx(-200)
        """
        assert isinstance(amount, int)
        self.driver.execute_script("window.scrollBy( {}, 0 )".format(amount))

    def open_urls(self, urls):
        link_doc = "data:text/html,"
        link_doc += "<html><head><title>Links!</title></head><body>"
        id = 0
        for url in urls:
            link_doc += '<a id="%d" href="%s">%d: %s</a><br>' % (id, url, id, url)
            id += 1
        link_doc += "</body><html>"
        self.driver.get(link_doc)
        for tag in self.driver.find_elements_by_tag_name("a"):
            action = ActionChains(self.driver)
            if mozinfo.os == "mac":
                ctrl_key = Keys.COMMAND
            else:
                ctrl_key = Keys.CONTROL
            action.key_down(ctrl_key).key_down(Keys.SHIFT).click(tag).key_up(
                Keys.SHIFT
            ).key_up(ctrl_key).perform()
            time.sleep(per_tab_pause)
        time.sleep(settle_wait_time)
        self.stats.print_stats()

    def press(self, key):

        """Press any special key or a key combination involving Ctrl , Alt , Shift

        :Args:
            -key: A key present in Browser().Key added with any other key to get the key combination.

        :Usage:

        .. code-block:: python

           press(driver.Key.SHIFT + 'hello')  # Sends keys HELLO in capital letters

           press(driver.Key.CONTROL + driver.Key.UP )

           press(driver.Key.ENTER)

        """

        action = ActionChains(self.driver)

        for char in key:
            action = action.key_down(char)

        action.perform()
        action.reset_actions()

        for char in key:
            if char not in string.ascii_letters:
                action = action.key_up(char)

        action.perform()
        action.reset_actions()

    def maximize(self):
        self.driver.maximize_window()

    def type(
        self,
        text,
        into="",
        clear=True,
        multiple=False,
        tag="input",
        id="",
        classname="",
        number=1,
        css_selector="",
        xpath="",
        loose_match=True,
    ):
        """
        Types the text into an input field

        :Args:
            - text: The text to type in the input field.
            - into: This can be any placeholder or name or value that is seen inside the input text box as seen in a self.driver. If not specified, other params are considered or the first input field is selected.
            - clear: Clears the input field before typing the text. Defaults to True
            - tag: The html tag to consider for the input field (eg: textarea), defaults to 'input'
            - id: id of the element to which the text must be sent
            - classname: Any class of the input element to consider while selecting the input element to send the keys to.
            - number: If there are multiple elements matching the criteria of other parameters, number specifies which element to select for the operation. This defaults to 1 and selects the first element to perform the action.
            - multiple: If True, the specified action is performed on all the elements matching the criteria and not just the first element. If it is true, number parameter is ignored. Defaults to False
            - css_selector: css_selector expression for better control over selecting the elements to perform the action.
            - xpath: xpath expression for better control over selecting the elements to perform the action.
            - loose_match: If loose_match is True then if no element of specified tag is found, all other tags are considered to search for the text, else only specified tag is considered for matching elements. Defaults to True

        :Usage:

        .. code-block:: python

           driver = Browser()
           driver.go_to('mail.google.com')

           driver.type('Myemail@gmail.com' , into = 'Email' )
           driver.type('mysecretpassword' , into = 'Password' , id = 'passwdfieldID' )
           driver.type("hello" , tag='span' , number = 2 )  # if there are multiple elements , then 2nd one is considered for operation (since number paramter is 2 ) .

        """

        self.__reset_error()
        if not (into or id or classname or css_selector or xpath):
            ActionChains(self.driver).send_keys(text).perform()
            return

        maxElements = self.__find_element(
            into, tag, classname, id, number, css_selector, xpath, loose_match
        )

        temp_element_index_ = 1

        for element in maxElements:

            try:
                if (number == temp_element_index_) or multiple:
                    if clear:
                        element.clear()
                    element.send_keys(text)

                    if not multiple:
                        break

                temp_element_index_ += 1

            except exceptions.WebDriverException as E:
                self.__set_error(
                    E,
                    element,
                    """ tagname : {} , id : {}  , classname : {} , id_attribute : {}
                """.format(
                        element.tag_name,
                        element.id,
                        element.get_attribute("class"),
                        element.get_attribute("id"),
                    ),
                )

    def scroll_bottom(self, range_int):
        if range_int > 50:
            range_int = 50
        for _ in range(int(range_int / 2)):
            self.driver.execute_script("window.scrollBy(0, 1000)")
            sleep(1)
        return

    def click_element(self, element, tryNum=0):
        try:
            element.click()
        except Exception:
            if tryNum == 0:
                self.driver.execute_script(
                    "document.getElementsByClassName('"
                    + element.get_attribute("class")
                    + "')[0].scrollIntoView({ inline: 'center' });"
                )
            elif tryNum == 1:
                self.driver.execute_script("window.scrollTo(0,0);")

            elif tryNum == 2:
                self.driver.execute_script(
                    "window.scrollTo(0,document.body.scrollHeight);"
                )

            else:
                print("attempting last ditch effort for click, `execute_script`")
                self.driver.execute_script(
                    "document.getElementsByClassName('"
                    + element.get_attribute("class")
                    + "')[0].click()"
                )
                return
            sleep_actual(1)
            tryNum += 1
            click_element(self.driver, element, tryNum)

    def web_address_navigator(self, link):
        """Checks and compares current URL of web page and the URL to be
        navigated and if it is different, it does navigate"""
        current_url = get_current_url(self.driver)
        total_timeouts = 0
        page_type = None  # file or directory
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
                    self.driver.get(link)
                    # update server calls
                    update_activity(self.driver, state=None)
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


def retries(max_tries, delay=1, backoff=2, exceptions=(Exception,), hook=None):
    def dec(func):
        def f2(*args, **kwargs):
            mydelay = delay
            tries = range(max_tries)
            tries.reverse()
            for tries_remaining in tries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if tries_remaining > 0:
                        if hook is not None:
                            hook(tries_remaining, e, mydelay)
                        sleep(mydelay)
                        mydelay = mydelay * backoff
                    else:
                        raise
                else:
                    break

        return f2

    return dec


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
            if not start_page:
                _start_page = browser.current_url
            rv = None
            retry_count = 0
            while True:
                try:
                    rv = org_func(*args, **kwargs)
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count > max_retry_count:
                        raise e
                    rv = None
                    browser.get(_start_page)
            return rv

        return wrapper

    return real_decorator


def clean_link(url, domain, link):
    if link.startswith("//"):
        link = "{}:{}".format(urlparse(url).scheme, link)
    elif link.startswith("://"):
        link = "{}{}".format(urlparse(url).scheme, link)
    else:
        link = urljoin(domain, link)
    return link


def get_links(html, link_regex):
    webpage_regex = re.compile("""<a[^>]+href=["'](.*?)["']""", re.IGNORECASE)
    links = webpage_regex.findall(html)
    links = (link for link in links if re.match(link_regex, link))
    return links


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
