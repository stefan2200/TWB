import collections
import logging
import sys
from pathlib import Path

from twb.core.filemanager import FileManager


class ConfigManager:
    @staticmethod
    def load_config() -> collections.OrderedDict:
        config_template = (
            Path(__file__).resolve().parent.parent / "templates" / "config.example.json"
        )
        template = FileManager.load_json_file(config_template)

        if not FileManager.path_exists(f"{Path.cwd()}/config.json"):
            if ConfigManager.manual_config():
                return ConfigManager.load_config()

            logging.error("No config file found. Exiting")
            sys.exit(1)

        config = FileManager.load_json_file(
            f"{Path.cwd()}/config.json", object_pairs_hook=collections.OrderedDict
        )

        if template and config["build"]["version"] != template["build"]["version"]:
            logging.warning(
                "Outdated config file found, merging (old copy saved as config.bak)\n"
                "Remove config.example.json to disable this behavior"
            )
            FileManager.copy_file(
                f"{Path.cwd()}/config.json", f"{Path.cwd()}/config.bak"
            )

            config = ConfigManager.merge_configs(config, template)
            FileManager.save_json_file(config, f"{Path.cwd()}/config.json")

            logging.info("Deployed new configuration file")

        return config

    @staticmethod
    def manual_config():
        logging.info(
            "Hello and welcome, it looks like you don't have a config file (yet)"
        )
        config_template = (
            Path(__file__).resolve().parent.parent / "templates" / "config.example.json"
        )
        if not FileManager.path_exists(config_template):
            logging.error(
                "Oh no, config.example.json and config.json do not exist. You broke something didn't you?"
            )
            return False

        logging.info(
            "Please enter the current (logged-in) URL of the world you are playing on (or q to exit)"
            "The URL should look something like this:\n"
            "https://nl01.tribalwars.nl/game.php?village=12345&screen=overview"
        )
        input_url = input("URL: ").strip()
        if input_url.strip() == "q":
            return False

        server = input_url.split("://")[1].split("/")[0]
        game_endpoint = input_url.split("?")[0]
        sub_parts = server.split(".")[0]

        logging.info("Game endpoint: %s", game_endpoint)
        logging.info("World: %s", sub_parts.upper())

        if input("Does this look correct? [nY]").lower() != "y":
            logging.info(
                "Make sure your URL starts with https:// and contains the game.php? part"
            )
            return ConfigManager.manual_config()

        browser_ua = input(
            "Enter your browser user agent (to lower detection rates). Just google 'what is my user agent'> "
        ).strip()
        if len(browser_ua) < 10:
            logging.error(
                "It should start with Chrome, Firefox or something. Please try again"
            )
            return ConfigManager.manual_config()

        disclaimer = """
        Read carefully: Please note the use of this bot can cause bans, kicks, annoyances and other stuff.
        I do my best to make the bot as undetectable as possible but most issues / bans are config related.
        Make sure you keep your bot sleeps at a reasonable numbers and please don't blame me if your account gets banned ;)
        PS. make sure to regularly (1-2 per day) logout/login using the browser session and supply the new cookie string.
        Using a single session for 24h straight will probably result in a ban
        """
        logging.info(disclaimer)

        if (
            input(
                "Do you understand this and still wish to continue, please type: yes and press enter> "
            ).lower()
            != "yes"
        ):
            logging.info("Goodbye :)")
            sys.exit(0)
        config_template = (
            Path(__file__).resolve().parent.parent / "templates" / "config.example.json"
        )
        template = FileManager.load_json_file(
            config_template, object_pairs_hook=collections.OrderedDict
        )
        if not template:
            logging.error("Unable to open config.example.json")
            return False

        template["server"]["endpoint"] = game_endpoint
        template["server"]["server"] = sub_parts.lower()
        template["bot"]["user_agent"] = browser_ua

        FileManager.save_json_file(template, f"{Path.cwd()}/config.json")
        logging.info("Deployed new configuration file")
        return True

    @staticmethod
    def merge_configs(old_config, new_config):
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
