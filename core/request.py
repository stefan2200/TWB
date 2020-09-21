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
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36'}
    endpoint = None
    logger = logging.getLogger("Requests")
    server = None
    last_response = None
    last_h = None
    priority_mode = False
    auth_endpoint = None
    driver_sync = None
    reporter = None

    def __init__(self, url, server=None, endpoint=None, reporter_enabled=False, reporter_constr=None):
        self.web = requests.session()
        self.auth_endpoint = url
        self.server = server
        self.endpoint = endpoint
        self.reporter = ReporterObject(enabled=reporter_enabled, connection_string=reporter_constr)

    def post_process(self, response):
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
        self.headers['Origin'] = (self.endpoint if self.endpoint else self.auth_endpoint).rstrip('/')
        if not self.priority_mode:
            time.sleep(random.randint(3, 7))
        url = urljoin(self.endpoint if self.endpoint else self.auth_endpoint, url)
        if self.driver_sync:
            self.driver_sync.driver.get(url)
        if not headers:
            headers = self.headers
        try:
            res = self.web.get(url=url, headers=headers)
            self.logger.debug("GET %s [%d]" % (url, res.status_code))
            self.post_process(res)
            return res
        except Exception as e:
            self.logger.warning("GET %s: %s" % (url, str(e)))
            return None

    def post_url(self, url, data, headers=None):
        if not self.priority_mode:
            time.sleep(random.randint(3, 7))
        self.headers['Origin'] = (self.endpoint if self.endpoint else self.auth_endpoint).rstrip('/')
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

    def attempt_login(self, username, password):
        payload = {
            'username': username,
            'clear': 'true',
            'password': password,
            'token': '03AOLTBLRabZE2hQv8NPD11xEiNE-OKzn3dVoCE6WkTSPQ3W53D6aVjPTGcq2z7qPcSpSIp5Wz52H4xOepSOB5nZBd8Jc2vn_tZVz27nqN23_O62NTjJZzMUyCALNP45m6ziEbEZ9KBhDiHDHBEsdJOXOfXGFEy82rO5WaKYBjCVy6gDMFWZqDA-JkQYUtt5JnAKcRq_U7_uaAelIjMPZezSvDqfLswjuJa1NAVuy4OgqyC7krFNndFfv__xOSwygIaiGg_r1Tdh2jbD4fQOqPkWbTnwSWDQKjLoNriWaxbdJPjwsjrmIBExHD1jZhSGY-8KPCmjLX1c7Dh0CRqipZbGBSA63rXYligJ9x2RN8HPkFAdZc1V8ivI50s6Oy9YFuUM7TMF42dd69Kf9bqTq0Yif7xK_JGG_rNPm5Ztb_66UhjIgJ0xP6oTUNenNvNBh0zaud1Tu0k8V7lD3y2gmrjzzpDydb7-bgIyQxEWzwLrajFBBmxZU6SfjIRKdhUiRDjk3IGgJZ81iS'
        }
        custom = dict(self.headers)
        custom['accept'] = "application/json, text/javascript, */*; q=0.01"
        custom['x-requested-with'] = "XMLHttpRequest"

        res = self.post_url("/page/auth", data=payload, headers=custom)
        return res.status_code == 200

    def start(self, username, password, keep_session=True):
        if os.path.exists('cache/session.json') and keep_session:
            with open('cache/session.json') as f:
                session_data = json.load(f)
                self.web.cookies.update(session_data['cookies'])
                get_test = self.get_url("game.php?screen=overview")
                if "game.php" in get_test.url:
                    return True
                else:
                    self.logger.warning("Current session cache not valid")
        self.web.cookies.clear()
        cinp = input("Enter browser cookie string> ")
        cookies = {}
        for itt in cinp.split(';'):
            itt = itt.strip()
            kvs = itt.split("=")
            k = kvs[0]
            v = '='.join(kvs[1:])
            cookies[k] = v
        self.web.cookies.update(cookies)
        self.logger.info("Game Endpoint: %s" % self.endpoint)

        for c in self.web.cookies:
            cookies[c.name] = c.value

        with open('cache/session.json', 'w') as f:
            session = {
                'endpoint': self.endpoint,
                'server': self.server,
                'cookies': cookies
            }
            json.dump(session, f)

    def get_action(self, village_id, action):
        url = "game.php?village=%s&screen=%s" % (village_id, action)
        response = self.get_url(url)
        return response

    def get_api_action(self, village_id, action, params={}, data={}):

        custom = dict(self.headers)
        custom['accept'] = "application/json, text/javascript, */*; q=0.01"
        custom['x-requested-with'] = "XMLHttpRequest"
        custom['tribalwars-ajax'] = "1"
        req = {
            'ajaxaction': action,
            'village': village_id,
            'screen': 'api'
        }
        req.update(params)
        payload = "game.php?%s" % urlencode(req)
        url = urljoin(self.endpoint, payload)
        if 'h' not in data:
            data['h'] = self.last_h
        res = self.post_url(url, data=data, headers=custom)
        if res.status_code == 200:
            try:
                return res.json()
            except:
                return res
