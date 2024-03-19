"""
TWB - an open source Tribal Wars bot
"""
#
# This file is part of the TWB distribution (https://github.com/stefan2200/TWB).
# Copyright (c) 2024 Stefan2200
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import collections
import copy
import datetime
import json
import logging
import os
import random
import sys
import signal
import time
import traceback
import coloredlogs
import requests

from core.notification import Notification
from core.updater import check_update
from core.filemanager import FileManager
from core.request import WebWrapper
from game.village import Village
from manager import VillageManager
from pages.overview import OverviewPage
from core.exceptions import UnsupportedPythonVersion
from core.extractors import Extractor

coloredlogs.install(
    level=logging.DEBUG if "-q" not in sys.argv else logging.INFO,
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

os.chdir(os.path.dirname(os.path.realpath(__file__)))


def signal_handler(sig, frame):
    print('Exiting...')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


class TWB:
    """
    Core class that manages activating times, sleeps, general web wrapper
    Also verifies, merges and updates the config file automatically
    """
    res = None
    villages = []
    wrapper = None
    should_run = True
    runs = 0
    found_villages = []

    @staticmethod
    def internet_online():
        """
        Checks whether the bot has internet access
        """
        try:
            requests.get("https://github.com/stefan2200/TWB", timeout=(10, 60))
            return True
        except requests.Timeout:
            return False

    def manual_config(self):
        """
        Runs through manual steps of configuring the bot
        """
        logging.info(
            "Hello and welcome, it looks like you don't have a config file (yet)"
        )
        if not FileManager.path_exists("config.example.json"):
            logging.error(
                "Oh no, config.example.json and config.json do not exist. You broke something didn't you?"
            )
            return False
        logging.info(
            "Please enter the current (logged-in) URL of the world you are playing on (or q to exit)"
            "The URL should look something like this:\n"
            "https://nl01.tribalwars.nl/game.php?village=12345&screen=overview"
        )
        input_url = input("URL: ")
        if input_url.strip() == "q":
            return False
        server = input_url.split("://")[1].split("/")[0]
        game_endpoint = input_url.split("?")[0]
        sub_parts = server.split(".")[0]
        logging.info("Game endpoint: %s", game_endpoint)
        logging.info("World: %s", sub_parts.upper())
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

            template = FileManager.load_json_file("config.example.json", object_pairs_hook=collections.OrderedDict)
            if not template:
                logging.error("Unable to open config.example.json")
                return False
            template["server"]["endpoint"] = game_endpoint
            template["server"]["server"] = sub_parts.lower()
            template["bot"]["user_agent"] = browser_ua

            FileManager.save_json_file(template, "config.json")
            print("Deployed new configuration file")
            return True

        print("Make sure your url starts with https:// and contains the game.php? part")
        return self.manual_config()

    def config(self):
        """
        Fetches the config file
        Or the example one of it doesn't exist
        Also updates config file with template data in case of an update
        """
        template = FileManager.load_json_file("config.example.json")

        if not FileManager.path_exists("config.json"):
            if self.manual_config():
                return self.config()

            print("No config file found. Exiting")
            sys.exit(1)

        config = FileManager.load_json_file("config.json", object_pairs_hook=collections.OrderedDict)

        if template and config["build"]["version"] != template["build"]["version"]:
            print(
                "Outdated config file found, merging (old copy saved as config.bak)\n"
                "Remove config.example.json to disable this behavior"
            )
            FileManager.copy_file("config.json", "config.bak")

            config = self.merge_configs(config, template)
            FileManager.save_json_file(config, "config.json")

            print("Deployed new configuration file")

        return config

    @staticmethod
    def merge_configs(old_config, new_config):
        """
        Merges sections of two config files, always ensuring the last version
        """
        to_ignore = ["villages", "build"]
        for section in old_config:
            if section not in to_ignore:
                for entry in old_config.get(section, {}):
                    if entry in new_config.get(section, {}):
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
        """
        Gets the overview page to automatically detect world options and owned villages
        """
        overview_page = OverviewPage(self.wrapper)
        self.found_villages = Extractor.village_ids_from_overview(overview_page.result_get.text)
        if config["bot"].get("add_new_villages", False):
            for found_vid in self.found_villages:
                if found_vid not in config["villages"]:
                    print(
                        f"Village {found_vid} was found but no config entry was found. Adding automatically"
                    )
                    config = self.add_village(village_id=found_vid)

        return overview_page, config

    def add_village(self, village_id, template=None):
        """
        Adds a new village and sets the default template data
        """
        original = self.config()
        FileManager.copy_file("config.json", "config.bak")

        if not template and "village_template" not in original:
            print(f"Village entry {village_id} could not be added to the config file!")
            return

        original["villages"][village_id] = template if template else original["village_template"]

        FileManager.save_json_file(original, "config.json")
        print("Deployed new configuration file")
        return original

    @staticmethod
    def get_world_options(overview_page: OverviewPage, config):
        """
        Detects world options like flags and knight enabled from the overview page
        """

        def check_and_set(option_key, setting, check_string=None):
            nonlocal changed
            if world_config[option_key] is None:
                world_config[option_key] = setting
                if check_string:
                    world_config[option_key] = check_string in overview_page.result_get.text

                changed = True

        changed = False
        world_settings = overview_page.world_settings
        world_config = config["world"]

        check_and_set("flags_enabled", world_settings.flags)
        check_and_set("knight_enabled", world_settings.knight)
        check_and_set("boosters_enabled", world_settings.boosters)
        check_and_set("quests_enabled", world_settings.quests, "Quests.setQuestData")

        return changed, config

    @staticmethod
    def is_active_hours(config):
        """
        Checks if the bot is within active hours
        Allows the bot to run more productive during an active session and ensure stealth at night
        """
        active_h = [int(hour) for hour in config["bot"]["active_hours"].split("-")]
        get_h = time.localtime().tm_hour
        return get_h in range(active_h[0], active_h[1])

    def run(self):
        """
        Run the bot
        TODO: make less messy
        """
        Notification.send("TWB is starting up")
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
                "Dead for %.2f minutes (next run at: %s)" % (sleep / 60, dt_next.time())
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
                    "Dead for %.2f minutes (next run at: %s)" % (sleep / 60, dt_next.time())
                )
                time.sleep(sleep)
            else:
                config = self.config()
                overview_page, config = self.get_overview(config)
                has_changed, new_cf = self.get_world_options(overview_page, config)
                if has_changed:
                    print("Updated world options")
                    config = self.merge_configs(config, new_cf)
                    FileManager.save_json_file(config, "config.json")
                    print("Deployed new configuration file")
                village_number = 1
                for village in self.villages:
                    if village.village_id not in self.found_villages:
                        print(
                            "Village %s will be ignored because it is not available anymore"
                            % village.village_id
                        )
                        continue
                    if not rm:
                        rm = village.rep_man
                    else:
                        village.rep_man = rm
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
                        num_pad = fs % village_number
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
                    village_number += 1

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
                    "Dead for %.2f minutes (next run at: %s)"
                    % (sleep / 60, dt_next.time())
                )
                sys.stdout.flush()
                time.sleep(sleep)

    def start(self):
        """
        First run, verify if dirctory structure exist
        """
        directories = [
            "cache/attacks",
            "cache/reports",
            "cache/villages",
            "cache/world",
            "cache/logs",
            "cache/managed",
            "cache/hunter"
        ]
        FileManager.create_directories(directories)

        self.run()


def main():
    """
    Python main entry function
    """
    check_update()
    for _ in range(3):
        t = TWB()
        try:
            t.start()
        except Exception as e:
            t.wrapper.reporter.report(0, "TWB_EXCEPTION", str(e))
            print("I crashed :(   %s" % str(e))
            Notification.send("TWB crashed: %s" % str(e))
            traceback.print_exc()

    Notification.send("TWB has crashed 3 times, exiting")


def self_config_test():
    """
    Checks if the config file consists of valid json if it exists
    """
    file_location = os.path.join(
        os.path.dirname(__file__),
        "config.json"
    )
    if not os.path.exists(file_location):
        return None
    try:
        with open(file_location, encoding="utf-8") as c_file:
            json.load(c_file)
            return True
    except Exception as e:
        logging.error(e)
        return False


if __name__ == "__main__":
    if "-i" in sys.argv:
        logging.info("Bot integrity check passed")
        check_conf = self_config_test()
        if sys.version_info[0] == 2:
            raise UnsupportedPythonVersion
        if check_conf is True:
            logging.info("Config integrity check passed")
        if check_conf is False:
            logging.error("Config integrity check failed")
            logging.error("It looks like your config file is corrupted and the bot was not able to start.")
            sys.exit(1)
        sys.exit(0)
    main()
