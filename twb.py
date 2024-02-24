import collections
import copy
import datetime
import json
import logging
import os
import random
import sys
import time
import traceback

import coloredlogs
import requests

from core.request import WebWrapper
from game.village import Village
from manager import VillageManager
from pages.overview import OverviewPage

coloredlogs.install(
    level=logging.DEBUG if "-q" not in sys.argv else logging.INFO,
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

os.chdir(os.path.dirname(os.path.realpath(__file__)))


class TWB:
    res = None
    villages = []
    wrapper = None
    should_run = True
    runs = 0

    def __init__(self):
        self.report_manager = None

    @staticmethod
    def internet_online():
        try:
            requests.get("https://github.com/stefan2200/TWB", timeout=(10, 60))
            return True
        except requests.Timeout:
            return False

    def manual_config(self):
        logging.info(
            "Hello and welcome, it looks like you don't have a config file (yet)"
        )
        if not os.path.exists("config.example.json"):
            logging.error(
                "Oh no, config.example.json and config.json do not exist. You broke something didn't you?"
            )
            return False
        logging.info(
            "Please enter the current (logged-in) URL of the world you are playing on (or q to exit)"
        )
        input_url = input("URL: ")
        if input_url.strip() == "q":
            return False
        server = input_url.split("://")[1].split("/")[0]
        game_endpoint = input_url.split("?")[0]
        sub_parts = server.split(".")[0]
        logging.info("Game endpoint: %s" % game_endpoint)
        logging.info("World: %s" % sub_parts.upper())
        check = input("Does this look correct? [nY]")
        if "y" in check.lower():
            browser_ua = input(
                "Enter your browser user agent "
                "(to lower detection rates). Just google what is my user agent> "
            )
            if browser_ua and len(browser_ua) < 10:
                logging.error(
                    "It should start with Chrome, Firefox or something. Please try again"
                )
                return self.manual_config()
            browser_ua = browser_ua.strip()
            disclaimer = """
            Read carefully: Please note the use of this bot can cause bans, kicks, annoyances and other stuff.
            I do my best to make the bot as undetectable as possible but most issues / bans are config related.
            Make sure you keep your bot sleeps at a reasonable numbers and please don't blame me if your account gets banned ;) 
            PS. make sure to regularly (1-2 per day) logout/login using the browser session and supply the new cookie string. 
            Using a single session for 24h straight will probably result in a ban
            """
            logging.info(disclaimer)
            final_check = input(
                "Do you understand this and still wish to continue, please type: yes and press enter> "
            )
            if "yes" not in final_check.lower():
                logging.info("Goodbye :)")
                sys.exit(0)
            root_directory = os.path.dirname(__file__)
            with open(
                os.path.join(root_directory, "config.example.json"), "r"
            ) as template_file:
                template = json.load(
                    template_file, object_pairs_hook=collections.OrderedDict
                )
                template["server"]["endpoint"] = game_endpoint
                template["server"]["server"] = sub_parts.lower()
                template["bot"]["user_agent"] = browser_ua
                with open(os.path.join(root_directory, "config.json"), "w") as newcf:
                    json.dump(template, newcf, indent=2, sort_keys=False)
                    print("Deployed new configuration file")
                    return True
        print("Make sure your url starts with https:// and contains the game.php? part")
        return self.manual_config()

    def config(self):
        template = None
        root_directory = os.path.dirname(__file__)
        if os.path.exists(os.path.join(root_directory, "config.example.json")):
            with open(
                os.path.join(root_directory, "config.example.json"), "r"
            ) as template_file:
                template = json.load(
                    template_file, object_pairs_hook=collections.OrderedDict
                )
        if not os.path.exists(os.path.join(root_directory, "config.json")):
            if self.manual_config():
                return self.config()
            else:
                print("Unable to start without a valid config file")
                sys.exit(1)
        config = None
        with open(os.path.join(root_directory, "config.json"), "r") as f:
            config = json.load(f, object_pairs_hook=collections.OrderedDict)
        if template and config["build"]["version"] != template["build"]["version"]:
            print(
                "Outdated config file found, merging (old copy saved as config.bak)\n"
                "Remove config.example.json to disable this behaviour"
            )
            with open(os.path.join(root_directory, "config.bak"), "w") as backup:
                json.dump(config, backup, indent=2, sort_keys=False)
            config = self.merge_configs(config, template)
            with open(os.path.join(root_directory, "config.json"), "w") as newcf:
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
        for v in old_config["villages"]:
            nc = new_config["village_template"]
            vdata = old_config["villages"][v]
            for entry in nc:
                if entry not in vdata:
                    vdata[entry] = nc[entry]
            villages[v] = vdata
        new_config["villages"] = villages
        return new_config

    def get_overview(self, config):
        overview_page = OverviewPage(self.wrapper)
        if config["bot"].get("add_new_villages", False):
            for found_vid in overview_page.villages_data.keys():
                if found_vid not in config["villages"]:
                    print(
                        "Village %s was found but no config entry was found. Adding automatically"
                        % found_vid
                    )
                    self.add_village(vid=found_vid)

        return overview_page, config

    def add_village(self, vid, template=None):
        original = self.config()
        root_directory = os.path.dirname(__file__)
        with open(os.path.join(root_directory, "config.bak"), "w") as backup:
            json.dump(original, backup, indent=2, sort_keys=False)
        if not template and "village_template" not in original:
            print("Village entry %s could not be added to the config file!" % vid)
            return
        original["villages"][vid] = (
            template if template else original["village_template"]
        )
        with open(os.path.join(root_directory, "config.json"), "w") as newcf:
            json.dump(original, newcf, indent=2, sort_keys=False)
            print("Deployed new configuration file")

    @staticmethod
    def get_world_options(overview_page: OverviewPage, config):
        changed = False

        world_settings = overview_page.world_settings
        world_config = config["world"]

        if world_config["flags_enabled"] is None:
            world_config["flags_enabled"] = world_settings.flags
            changed = True

        if world_config["knight_enabled"] is None:
            world_config["knight_enabled"] = world_settings.knight
            changed = True

        if world_config["boosters_enabled"] is None:
            world_config["boosters_enabled"] = world_settings.boosters
            changed = True

        if world_config["quests_enabled"] is None:
            world_config["quests_enabled"] = world_settings.quests
            changed = True

        return changed, config

    def is_active_hours(self, config):
        active_h = [int(x) for x in config["bot"]["active_hours"].split("-")]
        get_h = time.localtime().tm_hour
        return get_h in range(active_h[0], active_h[1])

    def run(self):
        config = self.config()
        if not self.internet_online():
            print("Internet seems to be down, waiting till its back online...")
            sleep = 0
            if self.is_active_hours(config=config):
                sleep = config["bot"]["active_delay"]
            else:
                if config["bot"]["inactive_still_active"]:
                    sleep = config["bot"]["inactive_delay"]

            sleep += random.randint(20, 120)
            dtn = datetime.datetime.now()
            dt_next = dtn + datetime.timedelta(0, sleep)
            print(
                "Dead for %f.2 minutes (next run at: %s)" % (sleep / 60, dt_next.time())
            )
            time.sleep(sleep)
            return False

        self.wrapper = WebWrapper(
            config["server"]["endpoint"],
            server=config["server"]["server"],
            endpoint=config["server"]["endpoint"],
            reporter_enabled=config["reporting"]["enabled"],
            reporter_constr=config["reporting"]["connection_string"],
        )

        self.wrapper.start()
        if not config["bot"].get("user_agent", None):
            print(
                "No custom user agent was supplied, this will likely get you banned."
                "Please set the bot -> user_agent parameter to your browsers one. "
                "Just google what is my user agent"
            )
            return
        self.wrapper.headers["user-agent"] = config["bot"]["user_agent"]
        for vid in config["villages"]:
            v = Village(wrapper=self.wrapper, village_id=vid)
            self.villages.append(copy.deepcopy(v))
        # setup additional builder
        rm = None
        defense_states = {}
        while self.should_run:
            if not self.internet_online():
                print("Internet seems to be down, waiting till its back online...")
                sleep = 0
                if self.is_active_hours(config=config):
                    sleep = config["bot"]["active_delay"]
                else:
                    if config["bot"]["inactive_still_active"]:
                        sleep = config["bot"]["inactive_delay"]

                sleep += random.randint(20, 120)
                dtn = datetime.datetime.now()
                dt_next = dtn + datetime.timedelta(0, sleep)
                print(
                    "Dead for %f.2 minutes (next run at: %s)"
                    % (sleep / 60, dt_next.time())
                )
                time.sleep(sleep)
            else:
                config = self.config()
                overview_page, config = self.get_overview(config)
                has_changed, new_cf = self.get_world_options(overview_page, config)
                if has_changed:
                    print("Updated world options")
                    config = self.merge_configs(config, new_cf)
                    with open(
                        os.path.join(os.path.dirname(__file__), "config.json"), "w"
                    ) as newcf:
                        json.dump(config, newcf, indent=2, sort_keys=False)
                        print("Deployed new configuration file")
                vnum = 1
                for village in self.villages:
                    if overview_page.villages_data and village.village_id not in overview_page.villages_data:
                        print(
                            "Village %s will be ignored because it is not available anymore"
                            % village.village_id
                        )
                        continue
                    if not self.report_manager:
                        self.report_manager = village.report_manager
                    else:
                        village.report_manager = self.report_manager
                    if (
                        "auto_set_village_names" in config["bot"]
                        and config["bot"]["auto_set_village_names"]
                    ):
                        template = config["bot"]["village_name_template"]
                        fs = (
                            "%0"
                            + str(config["bot"]["village_name_number_length"])
                            + "d"
                        )
                        num_pad = fs % vnum
                        template = template.replace("{num}", num_pad)
                        village.village_set_name = template

                    village.run(config=config)
                    if (
                        village.get_config(
                            section="units", parameter="manage_defence", default=False
                        )
                        and village.def_man
                    ):
                        defense_states[village.village_id] = (
                            village.def_man.under_attack
                            if village.def_man.allow_support_recv
                            else False
                        )
                    vnum += 1

                if len(defense_states) and config["farms"]["farm"]:
                    for village in self.villages:
                        print("Syncing attack states")
                        village.def_man.my_other_villages = defense_states

                sleep = 0
                if self.is_active_hours(config=config):
                    sleep = config["bot"]["active_delay"]
                else:
                    if config["bot"]["inactive_still_active"]:
                        sleep = config["bot"]["inactive_delay"]

                sleep += random.randint(20, 120)
                dtn = datetime.datetime.now()
                dt_next = dtn + datetime.timedelta(0, sleep)
                self.runs += 1

                VillageManager.farm_manager(verbose=True)
                print(
                    "Dead for %f.2 minutes (next run at: %s)"
                    % (sleep / 60, dt_next.time())
                )
                sys.stdout.flush()
                time.sleep(sleep)

    def start(self):
        root_directory = os.path.dirname(__file__)
        if not os.path.exists(os.path.join(root_directory, "cache")):
            os.mkdir(os.path.join(root_directory, "cache"))
        if not os.path.exists(os.path.join(root_directory, "cache", "attacks")):
            os.mkdir(os.path.join(root_directory, "cache", "attacks"))
        if not os.path.exists(os.path.join(root_directory, "cache", "reports")):
            os.mkdir(os.path.join(root_directory, "cache", "reports"))
        if not os.path.exists(os.path.join(root_directory, "cache", "villages")):
            os.mkdir(os.path.join(root_directory, "cache", "villages"))
        if not os.path.exists(os.path.join(root_directory, "cache", "world")):
            os.mkdir(os.path.join(root_directory, "cache", "world"))
        if not os.path.exists(os.path.join(root_directory, "cache", "logs")):
            os.mkdir(os.path.join(root_directory, "cache", "logs"))
        if not os.path.exists(os.path.join(root_directory, "cache", "managed")):
            os.mkdir(os.path.join(root_directory, "cache", "managed"))
        if not os.path.exists(os.path.join(root_directory, "cache", "hunter")):
            os.mkdir(os.path.join(root_directory, "cache", "hunter"))

        self.run()


for x in range(3):
    t = TWB()
    try:
        t.start()
    except Exception as e:
        t.wrapper.reporter.report(0, "TWB_EXCEPTION", str(e))
        print("I crashed :(   %s" % str(e))
        traceback.print_exc()
