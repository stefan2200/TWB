import logging
import time
import datetime
import sys
import random
import coloredlogs
import sys
import json
import copy
import os

from core.request import WebWrapper
from core.driver import GameDriver
from game.village import Village

coloredlogs.install(level=logging.INFO if "-d" in sys.argv else logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.ERROR)

os.chdir(os.path.dirname(os.path.realpath(__file__)))


class TWB:
    res = None
    villages = [

    ]
    wrapper = None
    should_run = True
    gd = None
    daemon = "-d" in sys.argv

    def config(self):
        with open('config.json', 'r') as f:
            return json.load(f)

    def run(self):
        config = self.config()
        self.wrapper = WebWrapper(config['server']['endpoint'], server=config['server']['server'], endpoint=config['server']['endpoint'])

        self.wrapper.start(username=config['server']['username'],
                           password=config['server']['password'], keep_session=True)

        for vid in config['villages']:
            v = Village(wrapper=self.wrapper, village_id=vid)
            self.villages.append(copy.deepcopy(v))
        self.gd = GameDriver(url=self.wrapper.endpoint + "?screen=overview&intro",
                             cookies=self.wrapper.web.cookies,
                             base=self.wrapper.auth_endpoint)
        # setup additional builder
        rm = None
        while self.should_run:
            config = self.config()
            for vil in self.villages:
                if not rm:
                    rm = vil.rep_man
                else:
                    vil.rep_man = rm
                vil.run(config=config)
            sleep = 0
            active_h = [int(x) for x in config['bot']['active_hours'].split('-')]
            get_h = time.localtime().tm_hour
            if get_h in range(active_h[0], active_h[1]):
                sleep = config['bot']['active_delay']
            else:
                if config['bot']['inactive_still_active']:
                    sleep = config['bot']['inactive_delay']

            sleep += random.randint(20, 120)
            dtn = datetime.datetime.now()
            dt_next = dtn + datetime.timedelta(0, sleep)
            print("Dead for %f.2 minutes (next run at: %s)" % (sleep / 60, dt_next.time()))
            time.sleep(sleep)

        if self.gd:
            self.gd.close()

    def start(self):
        if not os.path.exists("cache"):
            os.mkdir("cache")
            os.mkdir(os.path.join("cache", "attacks"))
            os.mkdir(os.path.join("cache", "reports"))
            os.mkdir(os.path.join("cache", "villages"))
            os.mkdir(os.path.join("cache", "world"))

        self.daemon = True
        if self.daemon:
            print("Running in daemon mode")
            self.run()
            while 1:
                self.should_run = True
                self.wrapper.endpoint = None
                self.run()
        else:
            self.run()


t = TWB()
t.start()
