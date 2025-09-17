"""
File used for data extraction
"""

import json
import re


class Extractor:
    """A collection of static methods for extracting data from HTML responses.

    This class uses regular expressions to parse HTML and extract specific
    information from the game's web pages.
    """
    @staticmethod
    def village_data(res):
        """Extracts village data from a page.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            dict or None: A dictionary containing village data, or None if not found.
        """
        if type(res) != str:
            res = res.text
        grabber = re.search(r'var village = (.+);', res)
        if grabber:
            data = grabber.group(1)
            return json.loads(data, strict=False)

    @staticmethod
    def game_state(res):
        """Extracts the game state from a page.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            dict or None: A dictionary containing the game state, or None if not found.
        """
        if type(res) != str:
            res = res.text
        grabber = re.search(r'TribalWars\.updateGameData\((.+?)\);', res)
        if grabber:
            data = grabber.group(1)
            return json.loads(data, strict=False)

    @staticmethod
    def building_data(res):
        """Extracts building data from the main building page.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            dict or None: A dictionary containing building data, or None if not found.
        """
        if type(res) != str:
            res = res.text
        dre = re.search(r'(?s)BuildingMain.buildings = (\{.+?\});', res)
        if dre:
            return json.loads(dre.group(1), strict=False)

        return None

    @staticmethod
    def get_quests(res):
        """Extracts quest data from a page.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            str or None: The ID of the completed quest, or None if no completed quests are found.
        """
        if type(res) != str:
            res = res.text
        get_quests = re.search(r'Quests.setQuestData\((\{.+?\})\);', res)
        if get_quests:
            result = json.loads(get_quests.group(1), strict=False)
            for quest in result:
                data = result[quest]
                if data['goals_completed'] == data['goals_total']:
                    return quest
        return None

    @staticmethod
    def get_quest_rewards(res):
        """Extracts available quest rewards from a page.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            list: A list of available quest rewards.
        """
        if type(res) != str:
            res = res.text
        get_rewards = re.search(r'RewardSystem\.setRewards\(\s*(\[\{.+?\}\]),', res)
        rewards = []
        if get_rewards:
            result = json.loads(get_rewards.group(1), strict=False)
            for reward in result:
                if reward['status'] == "unlocked":
                    rewards.append(reward)
        # Return all off them
        return rewards

    @staticmethod
    def map_data(res):
        """Extracts map data from the map page.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            list or None: A list of villages on the map, or None if not found.
        """
        if type(res) != str:
            res = res.text
        data = re.search(r'(?s)TWMap.sectorPrefech = (\[(.+?)\]);', res)
        if data:
            result = json.loads(data.group(1), strict=False)
            return result

    @staticmethod
    def smith_data(res):
        """Extracts smithy data from a page.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            dict or None: A dictionary containing smithy data, or None if not found.
        """
        if type(res) != str:
            res = res.text
        data = re.search(r'(?s)BuildingSmith.techs = (\{.+?\});', res)
        if data:
            result = json.loads(data.group(1), strict=False)
            return result
        return None

    @staticmethod
    def premium_data(res):
        """Extracts data from the premium exchange page.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            dict or None: A dictionary containing premium exchange data, or None if not found.
        """
        if type(res) != str:
            res = res.text
        data = re.search(r'(?s)PremiumExchange.receiveData\((.+?)\);', res)
        if data:
            result = json.loads(data.group(1), strict=False)
            return result
        return None

    @staticmethod
    def recruit_data(res):
        """Extracts recruitment data for the current building.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            dict or None: A dictionary containing recruitment data, or None if not found.
        """
        if type(res) != str:
            res = res.text
        data = re.search(r'(?s)unit_managers.units = (\{.+?\});', res)
        if data:
            raw = data.group(1)
            quote_keys_regex = r'([\{\s,])(\w+)(:)'
            processed = re.sub(quote_keys_regex, r'\1"\2"\3', raw)
            result = json.loads(processed, strict=False)
            return result

    @staticmethod
    def units_in_village(res):
        """Extracts the units in the current village.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            list: A list of tuples, where each tuple contains the unit name and quantity.
        """
        if type(res) != str:
            res = res.text
        matches = re.search(r'<table id="units_home".*?</tr>(.*?)</tr>', res, re.DOTALL)
        # We get the start of the table and grab the 2nd row (Where "From this village" troops are located)
        if matches:
            table_content = matches.group(1)
            unit_matches = re.findall(r'class=\'unit-item unit-item-(.*?)\'[^>]*>(\d+)</td>', table_content)
            # Find all the tuples (name, quantity) under the class "unit-item unit-item-*troop_name*"
            units = [(re.sub(r'\s*tooltip\s*', '', unit_name), unit_quantity) for unit_name, unit_quantity in
                     unit_matches if int(unit_quantity) > 0]
            # Filter units with quantity = 0, also for the Paladin,
            # the name would be "knight tooltip", so we had to remove that.
            return units
        return []

    @staticmethod
    def active_building_queue(res):
        """Extracts the number of active building queue entries.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            int: The number of active building queue entries.
        """
        if type(res) != str:
            res = res.text
        builder = re.search('(?s)<table id="build_queue"(.+?)</table>', res)
        if not builder:
            return 0

        return builder.group(1).count('<a class="btn btn-cancel"')

    @staticmethod
    def active_recruit_queue(res):
        """Extracts the active recruitment queue entries.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            list: A list of recruitment order IDs.
        """
        if type(res) != str:
            res = res.text
        builder = re.findall(r'(?s)TrainOverview\.cancelOrder\((\d+)\)', res)
        return builder

    @staticmethod
    def village_ids_from_overview(res):
        """Extracts village IDs from the overview page.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            list: A list of village IDs.
        """
        if type(res) != str:
            res = res.text
        villages = re.findall(r'<span class="quickedit-vn" data-id="(\w+)"', res)
        return list(set(villages))

    @staticmethod
    def units_in_total(res):
        """Extracts the total number of units in a village.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            list: A list of tuples, where each tuple contains the unit name and quantity.
        """
        if type(res) != str:
            res = res.text
        # hide units from other villages
        res = re.sub(r'(?s)<span class="village_anchor.+?</tr>', '', res)
        data = re.findall(r'(?s)class=\Wunit-item unit-item-([a-z]+)\W.+?(\d+)</td>', res)
        return data

    @staticmethod
    def attack_form(res):
        """Extracts input fields from the attack form.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            list: A list of tuples, where each tuple contains the input name and value.
        """
        if type(res) != str:
            res = res.text
        data = re.findall(r'(?s)<input.+?name="(.+?)".+?value="(.*?)"', res)
        return data

    @staticmethod
    def attack_duration(.text, res):
        """Extracts the duration of an attack.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            int: The duration of the attack in seconds, or 0 if not found.
        """
        if type(res) != str:
            res = res.text
        data = re.search(r'<span class="relative_time" data-duration="(\d+)"', res)
        if data:
            return int(data.group(1))
        return 0

    @staticmethod
    def report_table(res):
        """Extracts report IDs from a report table.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            list: A list of report IDs.
        """
        if type(res) != str:
            res = res.text
        data = re.findall(r'(?s)class="report-link" data-id="(\d+)"', res)
        return data

    @staticmethod
    def get_daily_reward(res):
        """Detects if there are unopened daily rewards.

        Args:
            res (requests.Response or str): The HTTP response or HTML content.

        Returns:
            str or None: The ID of the unlocked reward, or None if no rewards are found.
        """
        if type(res) != str:
            res = res.text
        get_daily = re.search(r'DailyBonus.init\((\s+\{.*\}),', res)
        res = json.loads(get_daily.group(1))
        reward_count_unlocked = str(res["reward_count_unlocked"])
        if reward_count_unlocked and res["chests"][reward_count_unlocked]["is_collected"]:
            return reward_count_unlocked
        return None
