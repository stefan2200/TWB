"""
Class for using one generic cookie jar, emulating a single tab
"""

import requests

from core.filemanager import FileManager
from core.notification import Notification

import logging
import re
import time
import random
from urllib.parse import urljoin, urlencode

from core.reporter import ReporterObject


class WebWrapper:
    """WebWrapper object for sending HTTP requests.

    This class manages a single requests session to emulate a browser tab,
    handling cookies, headers, and CSRF tokens automatically.
    """
    web = None
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36',
        'upgrade-insecure-requests': '1'
    }
    endpoint = None
    logger = logging.getLogger("Requests")
    server = None
    last_response = None
    last_h = None
    priority_mode = False
    auth_endpoint = None
    reporter = None
    delay = 1.0

    def __init__(self, url, server=None, endpoint=None, reporter_enabled=False, reporter_constr=None):
        """Initializes the WebWrapper.

        Args:
            url (str): The base URL for the game server.
            server (str, optional): The server name. Defaults to None.
            endpoint (str, optional): The game endpoint. Defaults to None.
            reporter_enabled (bool, optional): Whether the reporter is enabled.
                Defaults to False.
            reporter_constr (str, optional): The connection string for the reporter.
                Defaults to None.
        """
        self.web = requests.session()
        self.auth_endpoint = url
        self.server = server
        self.endpoint = endpoint
        self.reporter = ReporterObject(enabled=reporter_enabled, connection_string=reporter_constr)

    def post_process(self, response):
        """Post-processes all requests and stores data used for the next request.

        Args:
            response (requests.Response): The response object from the request.
        """
        xsrf = re.search('<meta content="(.+?)" name="csrf-token"', response.text)
        if xsrf:
            self.headers['x-csrf-token'] = xsrf.group(1)
            self.logger.debug("Set CSRF token")
        elif 'x-csrf-token' in self.headers:
            del self.headers['x-csrf-token']
        self.headers['Referer'] = response.url
        self.last_response = response
        get_h = re.search(r'&h=(\w+)', response.text)
        if get_h:
            self.last_h = get_h.group(1)

    def get_url(self, url, headers=None):
        """Fetches a URL using a basic GET request.

        Args:
            url (str): The URL to fetch.
            headers (dict, optional): Custom headers to use for the request.
                Defaults to None.

        Returns:
            requests.Response: The response object, or None if the request fails.
        """
        self.headers['Origin'] = (self.endpoint if self.endpoint else self.auth_endpoint).rstrip('/')
        if not self.priority_mode:
            time.sleep(random.randint(int(3 * self.delay), int(7 * self.delay)))
        url = urljoin(self.endpoint if self.endpoint else self.auth_endpoint, url)
        if not headers:
            headers = self.headers
        try:
            res = self.web.get(url=url, headers=headers)
            self.logger.debug("GET %s [%d]", url, res.status_code)
            self.post_process(res)
            if 'data-bot-protect="forced"' in res.text:
                self.logger.warning("Bot protection hit! cannot continue")
                self.reporter.report(
                    0, "TWB_RECAPTCHA", "Stopping bot, press any key once captcha has been solved")
                Notification.send("Bot protection hit! cannot continue")
                input("Press any key...")
                return self.get_url(url, headers)
            return res
        except Exception as e:
            self.logger.warning("GET %s: %s", url, str(e))
            return None

    def post_url(self, url, data, headers=None):
        """Sends a basic POST request with urlencoded postdata.

        Args:
            url (str): The URL to send the POST request to.
            data (dict): The data to send in the request body.
            headers (dict, optional): Custom headers to use for the request.
                Defaults to None.

        Returns:
            requests.Response: The response object, or None if the request fails.
        """
        if not self.priority_mode:
            time.sleep(
                random.randint(int(3 * self.delay), int(7 * self.delay))
            )
        self.headers['Origin'] = (self.endpoint if self.endpoint else self.auth_endpoint).rstrip('/')
        url = urljoin(self.endpoint if self.endpoint else self.auth_endpoint, url)
        enc = urlencode(data)
        if not headers:
            headers = self.headers
        try:
            res = self.web.post(url=url, data=data, headers=headers)
            self.logger.debug("POST %s %s [%d]", url, enc, res.status_code)
            self.post_process(res)
            return res
        except Exception as e:
            self.logger.warning("POST %s %s: %s", url, enc, str(e))
            return None

    def start(self, ):
        """Starts the bot and verifies whether the last session is still valid.

        Returns:
            bool: True if the session is valid, False otherwise.
        """
        session_data = FileManager.load_json_file("cache/session.json")
        if session_data:
            self.web.cookies.update(session_data['cookies'])
            get_test = self.get_url("game.php?screen=overview")
            if "game.php" in get_test.url:
                return True
            self.logger.warning("Current session cache not valid")

        self.web.cookies.clear()
        cinp = input("Enter browser cookie string> ")
        cookies = {}
        cinp = cinp.strip()
        for itt in cinp.split(';'):
            itt = itt.strip()
            kvs = itt.split("=")
            k = kvs[0]
            v = '='.join(kvs[1:])
            cookies[k] = v
        self.web.cookies.update(cookies)
        self.logger.info("Game Endpoint: %s", self.endpoint)

        for c in self.web.cookies:
            cookies[c.name] = c.value

        FileManager.save_json_file({
            'endpoint': self.endpoint,
            'server': self.server,
            'cookies': cookies
        }, "cache/session.json")

    def get_action(self, village_id, action):
        """Runs an action on a specific village.

        Args:
            village_id (int): The ID of the village.
            action (str): The action to perform.

        Returns:
            requests.Response: The response object.
        """
        url = "game.php?village=%s&screen=%s" % (village_id, action)
        response = self.get_url(url)
        return response

    def get_api_data(self, village_id, action, params={}):
        """Gets data from the game's API.

        Args:
            village_id (int): The ID of the village.
            action (str): The API action to call.
            params (dict, optional): Additional parameters for the request.
                Defaults to {}.

        Returns:
            dict or requests.Response: The JSON response from the API, or the
                full response object if JSON decoding fails.
        """
        custom = dict(self.headers)
        custom['accept'] = "application/json, text/javascript, */*; q=0.01"
        custom['x-requested-with'] = "XMLHttpRequest"
        custom['tribalwars-ajax'] = "1"
        req = {
            'ajax': action,
            'village': village_id,
            'screen': 'api'
        }
        req.update(params)
        payload = f"game.php?{urlencode(req)}"
        url = urljoin(self.endpoint, payload)
        res = self.get_url(url, headers=custom)
        if res.status_code == 200:
            try:
                return res.json()
            except:
                return res

    def post_api_data(self, village_id, action, params={}, data={}):
        """Simulates an API request.

        Args:
            village_id (int): The ID of the village.
            action (str): The API action to call.
            params (dict, optional): Additional parameters for the request URL.
                Defaults to {}.
            data (dict, optional): Data to send in the POST request body.
                Defaults to {}.

        Returns:
            dict or requests.Response: The JSON response from the API, or the
                full response object if JSON decoding fails.
        """
        custom = dict(self.headers)
        custom['accept'] = "application/json, text/javascript, */*; q=0.01"
        custom['x-requested-with'] = "XMLHttpRequest"
        custom['tribalwars-ajax'] = "1"
        req = {
            'ajax': action,
            'village': village_id,
            'screen': 'api'
        }
        req.update(params)
        payload = f"game.php?{urlencode(req)}"
        url = urljoin(self.endpoint, payload)
        if 'h' not in data:
            data['h'] = self.last_h
        res = self.post_url(url, data=data, headers=custom)
        if res.status_code == 200:
            try:
                return res.json()
            except:
                return res

    def get_api_action(self, village_id, action, params={}, data={}):
        """Simulates an API action being triggered.

        Args:
            village_id (int): The ID of the village.
            action (str): The API action to call.
            params (dict, optional): Additional parameters for the request URL.
                Defaults to {}.
            data (dict, optional): Data to send in the POST request body.
                Defaults to {}.

        Returns:
            dict or None: The JSON response from the API, or None if the
                request fails.
        """
        custom = dict(self.headers)
        custom['Accept'] = "application/json, text/javascript, */*; q=0.01"
        custom['X-Requested-With'] = "XMLHttpRequest"
        custom['TribalWars-Ajax'] = "1"
        req = {
            'ajaxaction': action,
            'village': village_id,
            'screen': 'api'
        }
        req.update(params)
        payload = f"game.php?{urlencode(req)}"
        url = urljoin(self.endpoint, payload)
        if 'h' not in data:
            data['h'] = self.last_h
        res = self.post_url(url, data=data, headers=custom)
        if res.status_code == 200:
            try:
                return res.json()
            except:
                return res
        return None
