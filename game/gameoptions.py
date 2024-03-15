"""
Class that handles connection between server options and local cache
"""

import logging
import re

import requests
import random
from time import sleep
from xml.etree import ElementTree

from core.filemanager import FileManager, FileNotFoundException


class GameOptions:
    game_options = None
    building_options = None
    unit_options = None
    logger = logging.getLogger("WorldOptions")

    def __init__(self, endpoint):
        """

        """
        logging.info("Reading world options")
        self.try_get_files(game_endpoint=endpoint)

    @staticmethod
    def try_parse(obj):
        """
        Parses a bunch of strings into a more usable form
        """
        if obj is None:
            return None
        try:
            return int(obj)
        except ValueError:
            pass
        try:
            return float(obj)
        except ValueError:
            return obj

    @staticmethod
    def xml_to_json(xml):
        """
        Tries to create dict from config data
        """
        response = {}

        for child in list(xml):
            fixed_tag = GameOptions.fix_tokens(child.tag)
            if len(list(child)) > 0:
                response[fixed_tag] = GameOptions.xml_to_json(child)
            else:
                response[fixed_tag] = GameOptions.try_parse(child.text) or None
        return response

    @staticmethod
    def gen_fake_agent():
        """
        Generates a kinda modern user agent since the endpoints require no auth
        """
        fake_user_agent_segments = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:"]
        random_revision = random.randint(100, 123)
        random_gecko = random.randint(1, 200)
        fake_user_agent_segments.append(f"{random_revision})")
        fake_user_agent_segments.append(f" Gecko/20100{random_gecko} ")
        fake_user_agent_segments.append(f"Firefox/{random_revision}.0")
        return "".join(fake_user_agent_segments)

    @staticmethod
    def fix_tokens(name):
        """
        Fixes keys
        """
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        return name

    def do_sync(self, game_endpoint, action):
        """
        Reads the remote config data and saves it locally
        """
        generate_ua = GameOptions.gen_fake_agent()
        game_endpoint = game_endpoint.replace("game.php", "interface.php")
        test = requests.get(
            game_endpoint,
            headers={
                "User-Agent": generate_ua
            },
            params={
                "func": action
            }
        )
        return GameOptions.xml_to_json(ElementTree.XML(test.text))

    def try_get_files(self, game_endpoint):
        """
        Tries to get the cache files
        """
        read_config_file = FileManager.load_json_file("cache/world_options/world.json")
        if not read_config_file:
            self.logger.warning(
                "World options are not found locally, syncing it automatically"
            )
            read_config_file = self.do_sync(game_endpoint, action="get_config")
            FileManager.save_json_file(read_config_file, path="cache/world_options/world.json")
            sleep(random.randint(1, 3))
        self.game_options = read_config_file

        read_building_file = FileManager.load_json_file("cache/world_options/building.json")
        if not read_building_file:
            self.logger.warning(
                "Building options are not found locally, syncing it automatically"
            )
            read_building_file = self.do_sync(game_endpoint, action="get_building_info")
            FileManager.save_json_file(read_building_file, path="cache/world_options/building.json")
            sleep(random.randint(1, 3))
        self.building_options = read_building_file

        read_units_file = FileManager.load_json_file("cache/world_options/units.json")
        if not read_units_file:
            self.logger.warning(
                "Unit options are not found locally, syncing it automatically"
            )
            read_units_file = self.do_sync(game_endpoint, action="get_unit_info")
            FileManager.save_json_file(read_units_file, path="cache/world_options/units.json")
            sleep(random.randint(1, 3))
        self.unit_options = read_units_file

