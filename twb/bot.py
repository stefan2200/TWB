import datetime
import json
import logging
import os
import random
import shutil
import sys
import time
from collections import OrderedDict
from pathlib import Path
from typing import List
from typing import Tuple

import coloredlogs

from twb.core.config import ConfigManager
from twb.core.exceptions import NoInternetException
from twb.core.extractors import Extractor
from twb.core.filemanager import FileManager
from twb.core.notification import Notification
from twb.core.request import WebWrapper
from twb.core.updater import check_update
from twb.manager import VillageManager
from twb.pages.overview import OverviewPage

coloredlogs.install(
    level=logging.DEBUG if "-q" not in sys.argv else logging.INFO,
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)


class TWB:
    def __init__(
        self,
        integrity_check: bool = False,
        config_path: str = "config.json",
        template_path=None,
    ) -> None:
        self.res = None
        self.villages = []
        self.wrapper = None
        self.should_run = True
        self.runs = 0

        if integrity_check:
            self.integrity_check()

        check_update(config_path=config_path)
        self.create_default_template_path(template_path)

    def create_default_template_path(self, template_path=None):
        default_files = [
            {
                "directory": "builder",
                "files": [
                    "basic.txt",
                    "purple_predator_into_def.txt",
                    "purple_predator_into_off.txt",
                    "purple_predator.txt",
                ],
            },
            {"directory": "offensive", "files": ["clear.txt", "scout.txt"]},
            {
                "directory": "troops",
                "files": [
                    "basic_into_def.txt",
                    "basic_into_off.txt",
                    "basic.txt",
                    "defensive.txt",
                    "offensive.txt",
                ],
            },
            {"directory": "", "files": ["config.example.json"]},
        ]

        if template_path is None:
            template_path = f"{Path.cwd()}/templates"

        dir_path = Path(template_path)
        parent_dir = Path(__file__).resolve().parent

        if not dir_path.exists():
            dir_path.mkdir(parents=True)
            logging.info(f"Directory '{template_path}' created.")

        for item in default_files:
            if item["directory"]:
                target_dir_path = Path(f"{template_path}/{item['directory']}")

                source_dir_path = f"{parent_dir}/templates/{item['directory']}"
                if not target_dir_path.exists():
                    target_dir_path.mkdir(parents=True)
                    logging.info(f"Directory '{target_dir_path}' created.")
            else:
                target_dir_path = Path(template_path)
                source_dir_path = f"{parent_dir}/templates"

            for file in item["files"]:
                source_file_path = Path(f"{source_dir_path}/{file}")
                target_file_path = Path(f"{target_dir_path}/{file}")
                if not target_file_path.is_file():
                    shutil.copy(source_file_path, target_file_path)
                    logging.info(f"File '{file}' created in '{target_file_path}'.")

    def config_test(self, config_path="templates/config.example.json"):
        file_location = config_path
        if not os.path.exists(file_location):
            return None
        try:
            with open(file_location, encoding="utf-8") as c_file:
                json.load(c_file)
                return True
        except Exception as e:
            logging.error(e)
            return False

    def integrity_check(self):
        """
        Checks if config is designed correctly

        Raises:
            UnsupportedPythonVersion: Raise if wrong python version is used
        """
        logging.info("Completing an integrity check")
        check_conf = self.config_test()
        if check_conf is True:
            logging.info("Config integrity check passed")
        if check_conf is False:
            logging.error("Config integrity check failed")
            logging.error(
                "It looks like your config file is corrupted and the bot was not able to start."
            )
            sys.exit(1)
        sys.exit(0)

    @staticmethod
    def is_active_hours(config):
        active_h = [int(hour) for hour in config["bot"]["active_hours"].split("-")]
        get_h = time.localtime().tm_hour
        return get_h in range(active_h[0], active_h[1])

    def calculate_sleep_duration(self, config):
        sleep_duration = 0
        if self.is_active_hours(config=config):
            sleep_duration = config["bot"]["active_delay"]
        else:
            if config["bot"]["inactive_still_active"]:
                sleep_duration = config["bot"]["inactive_delay"]

        sleep_duration += random.randint(20, 120)
        return sleep_duration

    def handle_internet_connection(self, config: OrderedDict) -> bool:
        """
        Handles internet connection for the bot

        Args:
            config (_type_): _description_

        Returns:
            _type_: _description_
        """
        if not WebWrapper.internet_online():
            logging.error("Internet seems to be down, waiting till its back online...")
            sleep_duration = self.calculate_sleep_duration(config)
            dtn = datetime.datetime.now()
            dt_next = dtn + datetime.timedelta(0, sleep_duration)
            logging.info(
                "Dead for %.2f minutes (next run at: %s)",
                sleep_duration / 60,
                dt_next.time(),
            )
            time.sleep(sleep_duration)
            return False
        return True

    def get_found_villages_from_overview(
        self, overview_page: OverviewPage
    ) -> List[str]:
        return Extractor.village_ids_from_overview(overview_page.result_get.text)

    def add_new_villages_to_config(
        self, config: OrderedDict, found_villages: List[str]
    ) -> OrderedDict:
        if not config["bot"].get("add_new_villages", False):
            return config

        for found_vid in found_villages:
            if found_vid not in config["villages"]:
                print(
                    f"Village {found_vid} was found but no config entry was found. Adding automatically"
                )
                config = self.add_village(village_id=found_vid)
        return config

    def run(self):
        """
        Main run method for the bot

        Raises:
            NoInternetException: Raises an exception if the bot doesn't have internet
        """
        directories = [
            f"{Path.cwd()}/cache/attacks",
            f"{Path.cwd()}/cache/reports",
            f"{Path.cwd()}/cache/villages",
            f"{Path.cwd()}/cache/world",
            f"{Path.cwd()}/cache/logs",
            f"{Path.cwd()}/cache/managed",
            f"{Path.cwd()}/cache/hunter",
        ]
        FileManager.create_directories(directories)

        Notification.send("TWB is starting up")
        config = ConfigManager.load_config()

        if not self.handle_internet_connection(config):
            raise NoInternetException("No internet connection")

        self.setup_wrapper(config)
        self.set_user_agent(config)

        overview_page = self.get_overview()
        found_villages = self.get_found_villages_from_overview(overview_page)
        config = self.add_new_villages_to_config(config, found_villages)

        village_manager = VillageManager(self.wrapper, found_villages)
        village_manager.initialize_villages(config)

        while self.should_run:
            if not self.handle_internet_connection(config):
                continue

            config = ConfigManager.load_config()
            overview_page = self.get_overview()
            found_villages = self.get_found_villages_from_overview(overview_page)
            village_manager.add_found_villages(found_villages)
            config = self.add_new_villages_to_config(config, found_villages)
            has_changed, new_cf = self.get_world_options(overview_page, config)

            if has_changed:
                logging.info("Updated world options")
                config = ConfigManager.merge_configs(config, new_cf)
                FileManager.save_json_file(config, f"{Path.cwd()}/config.json")
                logging.info("Deployed new configuration file")

            village_manager.process_villages(config)

            sleep_duration = self.calculate_sleep_duration(config)
            self.runs += 1

            village_manager.farm_manager(verbose=True)
            logging.info(
                "Sleeping for %.2f minutes (next run at: %s)",
                sleep_duration / 60,
                (
                    datetime.datetime.now() + datetime.timedelta(0, sleep_duration)
                ).time(),
            )
            time.sleep(sleep_duration)
        self.run()

    def setup_wrapper(self, config: OrderedDict) -> None:
        self.wrapper = WebWrapper(
            config["server"]["endpoint"],
            server=config["server"]["server"],
            endpoint=config["server"]["endpoint"],
            reporter_enabled=config["reporting"]["enabled"],
            reporter_constr=config["reporting"]["connection_string"],
        )
        self.wrapper.start()

    def set_user_agent(self, config: OrderedDict) -> None:
        if not config["bot"].get("user_agent", None):
            logging.warning(
                "No custom user agent was supplied, this will likely get you banned."
                "Please set the bot -> user_agent parameter to your browser's one. "
                "Just google 'what is my user agent'."
            )
            return
        self.wrapper.headers["user-agent"] = config["bot"]["user_agent"]

    def get_overview(self) -> OverviewPage:
        overview_page = OverviewPage(self.wrapper)
        return overview_page

    def add_village(self, village_id, template=None):
        original = ConfigManager.load_config()
        FileManager.copy_file(f"{Path.cwd()}/config.json", f"{Path.cwd()}/config.bak")

        if not template and "village_template" not in original:
            logging.error(
                f"Village entry {village_id} could not be added to the config file!"
            )
            return None

        original["villages"][village_id] = (
            template if template else original["village_template"]
        )

        FileManager.save_json_file(original, f"{Path.cwd()}/config.json")
        logging.info("Deployed new configuration file")
        return original

    @staticmethod
    def get_world_options(
        overview_page: OverviewPage, config: OrderedDict
    ) -> Tuple[bool, OrderedDict]:
        def check_and_set(option_key, setting, check_string=None):
            nonlocal changed
            if world_config[option_key] is None:
                world_config[option_key] = setting
                if check_string:
                    world_config[option_key] = (
                        check_string in overview_page.result_get.text
                    )

                changed = True

        changed = False
        world_settings = overview_page.world_settings
        world_config = config["world"]

        check_and_set("flags_enabled", world_settings.flags)
        check_and_set("knight_enabled", world_settings.knight)
        check_and_set("boosters_enabled", world_settings.boosters)
        check_and_set("quests_enabled", world_settings.quests, "Quests.setQuestData")

        return changed, config
