import logging
import time
import datetime
import random
import coloredlogs
import sys
import json
import copy
import os
import collections

from core.request import WebWrapper
from game.village import Village

coloredlogs.install(level=logging.DEBUG, fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
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
        template = None
        if os.path.exists('config.example.json'):
            with open('config.example.json', 'r') as template_file:
                template = json.load(template_file, object_pairs_hook=collections.OrderedDict)
        if not os.path.exists('config.json'):
            print("No configuration file found. Stopping!")
            sys.exit(1)
        config = None
        with open('config.json', 'r') as f:
            config = json.load(f, object_pairs_hook=collections.OrderedDict)
        if template and config['build']['version'] != template['build']['version']:
            print("Outdated config file found, merging (old copy saved as config.bak)\n"
                  "Remove config.example.json to disable this behaviour")
            with open('config.bak', 'w') as backup:
                json.dump(config, backup, indent=2, sort_keys=False)
            config = self.merge_configs(config, template)
            with open('config.json', 'w') as newcf:
                json.dump(config, newcf, indent=2, sort_keys=False)
                print("Deployed new configuration file")
        return config

    def merge_configs(self, old_config, new_config):
        to_ignore = ["villages", "build"]
        for section in old_config:
            if section not in to_ignore:
                for entry in old_config[section]:
                    if entry in new_config[section]:
                        new_config[section][entry] = old_config[section][entry]
        villages = collections.OrderedDict()
        for v in old_config['villages']:
            nc = new_config["villages"]["enter_village_id_here_between_these_quotes"]
            vdata = old_config['villages'][v]
            for entry in nc:
                if entry not in vdata:
                    vdata[entry] = nc[entry]
            villages[v] = vdata
        new_config['villages'] = villages
        return new_config

    def run(self):
        config = self.config()
        self.wrapper = WebWrapper(config['server']['endpoint'],
                                  server=config['server']['server'],
                                  endpoint=config['server']['endpoint'],
                                  reporter_enabled=config['reporting']['enabled'],
                                  reporter_constr=config['reporting']['connection_string'])

        self.wrapper.start(username="dontcare",
                           password="dontcare", keep_session=True)

        for vid in config['villages']:
            v = Village(wrapper=self.wrapper, village_id=vid)
            self.villages.append(copy.deepcopy(v))
        # setup additional builder
        rm = None
        defense_states = {}
        while self.should_run:
            config = self.config()
            for vil in self.villages:
                if not rm:
                    rm = vil.rep_man
                else:
                    vil.rep_man = rm
                vil.run(config=config)
                if vil.get_config(section="units", parameter="manage_defence", default=False):
                    defense_states[vil.village_id] = vil.def_man.under_attack if vil.def_man.allow_support_recv else False

            if len(defense_states):
                for vil in self.villages:
                    print("Syncing attack states")
                    vil.def_man.my_other_villages = defense_states

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
        if not os.path.exists(os.path.join("cache", "attacks")):
            os.mkdir(os.path.join("cache", "attacks"))
        if not os.path.exists(os.path.join("cache", "reports")):
            os.mkdir(os.path.join("cache", "reports"))
        if not os.path.exists(os.path.join("cache", "villages")):
            os.mkdir(os.path.join("cache", "villages"))
        if not os.path.exists(os.path.join("cache", "world")):
            os.mkdir(os.path.join("cache", "world"))
        if not os.path.exists(os.path.join("cache", "logs")):
            os.mkdir(os.path.join("cache", "logs"))
        if not os.path.exists(os.path.join("cache", "managed")):
            os.mkdir(os.path.join("cache", "managed"))

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


for x in range(3):
    t = TWB()
    try:
        t.start()
    except Exception as e:
        t.wrapper.reporter.report(0, "TWB_EXCEPTION", str(e))
        print("I crashed :(   %s" % str(e))
        pass
