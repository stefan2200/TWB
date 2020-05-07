import threading
from selenium.webdriver import Chrome, ChromeOptions
import time


class GameDriver:
    url = None
    cookies = None
    ua = "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36'"
    driver = None
    active = True
    base = None

    def __init__(self, url, cookies, base=None):
        self.url = url
        self.cookies = cookies
        self.base = base

    def run(self):
        driver = "chromedriver.exe"
        chrome_options = ChromeOptions()
        #chrome_options.add_argument('--headless')
        chrome_options.add_argument('--user-agent="%s"' % self.ua)

        self.driver = Chrome(executable_path=driver, chrome_options=chrome_options)
        self.driver.get(url=self.base)
        time.sleep(1)
        for c in self.cookies:
            self.driver.add_cookie({'name': c.name, 'value': c.value, 'domain': c.domain})
            print("Setting Driver cookie: %s=%s (%s)" % (c.name, c.value, c.domain))
        self.driver.get(url=self.url)

    def close(self):
        if self.driver:
            self.driver.close()
