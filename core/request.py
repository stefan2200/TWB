import requests

try:
    from urllib.parse import urljoin, urlencode
except ImportError:
    from urlparse import urljoin, urlencode
import logging
import re
import time
import random
import json
import os
from core.reporter import ReporterObject


class WebWrapper:
    web = None
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36",
        "upgrade-insecure-requests": "1",
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

    def __init__(
        self,
        url,
        server=None,
        endpoint=None,
        reporter_enabled=False,
        reporter_constr=None,
    ):
        self.web = requests.session()
        self.auth_endpoint = url
        self.server = server
        self.endpoint = endpoint
        self.reporter = ReporterObject(
            enabled=reporter_enabled, connection_string=reporter_constr
        )

    def post_process(self, response):
        xsrf = re.search('<meta content="(.+?)" name="csrf-token"', response.text)
        if xsrf:
            self.headers["x-csrf-token"] = xsrf.group(1)
            self.logger.debug("Set CSRF token")
        elif "x-csrf-token" in self.headers:
            del self.headers["x-csrf-token"]
        self.headers["Referer"] = response.url
        self.last_response = response
        get_h = re.search(r"&h=(\w+)", response.text)
        if get_h:
            self.last_h = get_h.group(1)

    def get_url(self, url, headers=None):
        self.headers["Origin"] = (
            self.endpoint if self.endpoint else self.auth_endpoint
        ).rstrip("/")
        if not self.priority_mode:
            time.sleep(random.randint(int(3 * self.delay), int(7 * self.delay)))
        url = urljoin(self.endpoint if self.endpoint else self.auth_endpoint, url)
        if not headers:
            headers = self.headers
        try:
            res = self.web.get(url=url, headers=headers)
            self.logger.debug("GET %s [%d]" % (url, res.status_code))
            self.post_process(res)
            if 'data-bot-protect="forced"' in res.text:
                self.logger.warning("Bot protection hit! cannot continue")
                self.reporter.report(
                    0,
                    "TWB_RECAPTCHA",
                    "Stopping bot, press any key once captcha has been solved",
                )
                input("Press any key...")
                return self.get_url(url, headers)
            return res
        except Exception as e:
            self.logger.warning("GET %s: %s" % (url, str(e)))
            return None

    def post_url(self, url, data, headers=None):
        if not self.priority_mode:
            time.sleep(random.randint(int(3 * self.delay), int(7 * self.delay)))
        self.headers["Origin"] = (
            self.endpoint if self.endpoint else self.auth_endpoint
        ).rstrip("/")
        url = urljoin(self.endpoint if self.endpoint else self.auth_endpoint, url)
        enc = urlencode(data)
        if not headers:
            headers = self.headers
        try:
            res = self.web.post(url=url, data=data, headers=headers)
            self.logger.debug("POST %s %s [%d]" % (url, enc, res.status_code))
            self.post_process(res)
            return res
        except Exception as e:
            self.logger.warning("POST %s %s: %s" % (url, enc, str(e)))
            return None

    def start(
        self,
    ):
        session_file = os.path.join(
            os.path.dirname(__file__), "..", "cache", "session.json"
        )
        if os.path.exists(session_file):
            with open(session_file) as f:
                session_data = json.load(f)
                self.web.cookies.update(session_data["cookies"])
                get_test = self.get_url("game.php?screen=overview")
                if "game.php" in get_test.url:
                    return True
                else:
                    self.logger.warning("Current session cache not valid")
        self.web.cookies.clear()
        cinp = input("Enter browser cookie string> ")
        cookies = {}
        cinp = cinp.strip()
        for itt in cinp.split(";"):
            itt = itt.strip()
            kvs = itt.split("=")
            k = kvs[0]
            v = "=".join(kvs[1:])
            cookies[k] = v
        self.web.cookies.update(cookies)
        self.logger.info("Game Endpoint: %s" % self.endpoint)

        for c in self.web.cookies:
            cookies[c.name] = c.value

        with open(session_file, "w") as f:
            session = {
                "endpoint": self.endpoint,
                "server": self.server,
                "cookies": cookies,
            }
            json.dump(session, f)

    def get_action(self, village_id, action):
        url = "game.php?village=%s&screen=%s" % (village_id, action)
        response = self.get_url(url)
        return response

    def get_api_data(self, village_id, action, params={}):
        custom = dict(self.headers)
        custom["accept"] = "application/json, text/javascript, */*; q=0.01"
        custom["x-requested-with"] = "XMLHttpRequest"
        custom["tribalwars-ajax"] = "1"
        req = {"ajax": action, "village": village_id, "screen": "api"}
        req.update(params)
        payload = "game.php?%s" % urlencode(req)
        url = urljoin(self.endpoint, payload)
        res = self.get_url(url, headers=custom)
        if res.status_code == 200:
            try:
                return res.json()
            except:
                return res

    def post_api_data(self, village_id, action, params={}, data={}):
        custom = dict(self.headers)
        custom["accept"] = "application/json, text/javascript, */*; q=0.01"
        custom["x-requested-with"] = "XMLHttpRequest"
        custom["tribalwars-ajax"] = "1"
        req = {"ajax": action, "village": village_id, "screen": "api"}
        req.update(params)
        payload = "game.php?%s" % urlencode(req)
        url = urljoin(self.endpoint, payload)
        if "h" not in data:
            data["h"] = self.last_h
        res = self.post_url(url, data=data, headers=custom)
        if res.status_code == 200:
            try:
                return res.json()
            except:
                return res

    def get_api_action(self, village_id, action, params={}, data={}):
        custom = dict(self.headers)
        custom["Accept"] = "application/json, text/javascript, */*; q=0.01"
        custom["X-Requested-With"] = "XMLHttpRequest"
        custom["TribalWars-Ajax"] = "1"
        req = {"ajaxaction": action, "village": village_id, "screen": "api"}
        req.update(params)
        payload = "game.php?%s" % urlencode(req)
        url = urljoin(self.endpoint, payload)
        if "h" not in data:
            data["h"] = self.last_h
        res = self.post_url(url, data=data, headers=custom)
        if res:
            if res.status_code == 200:
                try:
                    return res.json()
                except:
                    return res
        return None
