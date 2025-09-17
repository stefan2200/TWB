"""
Used to create snobs
"""
import json
import logging
import re

from core.extractors import Extractor


class SnobManager:
    """Manages the recruitment of nobles (snobs) in a village.

    This class can handle both coin-based and resource-based recruitment
    systems, and it will automatically store resources or mint coins as needed.
    """
    wrapper = None
    village_id = None
    resman = None
    can_snob = True
    troop_manager = None
    wanted = 1
    building_level = 0
    is_incomplete = False
    using_coin_system = False

    def level_system(self):
        """Returns the level of the snob recruitment system.

        Returns:
            int: The level of the snob recruitment system.
        """
        return 0

    def __init__(self, wrapper=None, village_id=None):
        """Initializes the SnobManager.

        Args:
            wrapper (WebWrapper, optional): The web wrapper for making requests.
                Defaults to None.
            village_id (int, optional): The ID of the village. Defaults to None.
        """
        self.wrapper = wrapper
        self.village_id = village_id
        self.logger = logging.getLogger(f"Snob:{self.village_id}")

    def need_reserve(self, text):
        """Checks if there are enough resources or gold coins to recruit a snob.

        Args:
            text (str): The HTML content of the snob recruitment page.

        Returns:
            int: The amount of resources or gold coins needed, or 0 if enough
                are available.
        """
        if not self.using_coin_system:
            need_amount = re.search(
                r'(?s)<th colspan="3">[\w\s]+</th>.+?data-unit="snob">.+?<td.+?>\s*(\d+)\sx',
                text,
            )
            if need_amount:
                return int(need_amount.group(1))
            return 0

        if "gold_big.png" not in text:
            self.logger.warning("Error parsing snob content")
            return 0
        splits = text.split("gold_big.png")[1].split("<table")[1].split("</table")[0]
        rows = re.search(r'<td class="nowrap">(\d+)', splits)
        if rows:
            return int(rows.group(1))
        return 0

    def attempt_recruit(self, amount):
        """Attempts to recruit a new snob.

        Args:
            amount (int): The number of snobs to recruit.

        Returns:
            bool: True if the recruitment was successful, False otherwise.
        """
        result = self.wrapper.get_action(action="snob", village_id=self.village_id)
        if '"id":"coin"' in result.text:
            self.using_coin_system = True
        game_data = Extractor.game_state(result)
        self.resman.update(game_data)

        can_recruit = re.search(
            r"(?s)</th><th>(\d+)</th></tr>\s*</table><br />", result.text
        )
        if not can_recruit or int(can_recruit.group(1)) == 0:
            nres = self.need_reserve(result.text)
            if nres > 0:
                self.logger.debug(
                    "Not enough resources available, still %d needed, attempting storage", nres
                )
                cres = (
                    self.storage_item(result.text)
                    if not self.using_coin_system
                    else self.coin_item(result.text)
                )
                if cres:
                    return self.attempt_recruit(amount)
                self.is_incomplete = True
                self.logger.debug("Not enough resources available")
                return False
        self.is_incomplete = False
        r_num = int(can_recruit.group(1))
        if r_num == 0:
            self.logger.debug(
                "No more snobs available, awaiting snob creating, snob death or village loss"
            )
            return False
        train_snob_url = f"game.php?village={self.village_id}&screen=snob&action=train&h={self.wrapper.last_h}"
        self.wrapper.get_url(train_snob_url)
        return True

    def storage_item(self, result):
        """Stores resources for future snob creation.

        Args:
            result (str): The HTML content of the snob recruitment page.

        Returns:
            bool: True if the resources were stored successfully, False otherwise.
        """
        storage_re = re.search(r"train\.storage_item = (\{.+?})", result)
        if not storage_re:
            self.logger.warning(
                "Snob recruit is called but storage data not on page, error?"
            )
            return False
        raw_coin = storage_re.group(1)
        data = json.loads(raw_coin)

        if self.has_enough(data):
            get_post = f"game.php?village={self.village_id}&screen=snob&action=reserve"
            data = {"factor": "1", "h": self.wrapper.last_h}
            self.wrapper.post_url(url=get_post, data=data)
            return True
        else:
            self.is_incomplete = True
            return False

    def coin_item(self, result):
        """Mints a new gold coin.

        Args:
            result (str): The HTML content of the snob recruitment page.

        Returns:
            bool: True if the coin was minted successfully, False otherwise.
        """
        storage_re = re.search(r"train\.storage_item = (\{.+?})", result)
        if not storage_re:
            self.logger.warning(
                "Snob recruit is called but storage data not on page, error?"
            )
            return False
        raw_coin = storage_re.group(1)
        data = json.loads(raw_coin)

        if self.has_enough(data):
            get_post = f"game.php?village={self.village_id}&screen=snob&action=coin"
            data = {"coin_mint_count": "1", "count": "1", "h": self.wrapper.last_h}
            self.wrapper.post_url(url=get_post, data=data)
            return True
        else:
            self.is_incomplete = True
            return False

    def has_enough(self, build_item):
        """Checks if there are enough resources to recruit a snob.

        If not, it will request the missing resources from the resource manager.

        Args:
            build_item (dict): A dictionary of the required resources.

        Returns:
            bool: True if there are enough resources, False otherwise.
        """
        r = True
        if build_item["wood"] > self.resman.actual["wood"]:
            req = build_item["wood"] - self.resman.actual["wood"]
            self.resman.request(source="snob", resource="wood", amount=req)
            r = False
        if build_item["stone"] > self.resman.actual["stone"]:
            req = build_item["stone"] - self.resman.actual["stone"]
            self.resman.request(source="snob", resource="stone", amount=req)
            r = False
        if build_item["iron"] > self.resman.actual["iron"]:
            req = build_item["iron"] - self.resman.actual["iron"]
            self.resman.request(source="snob", resource="iron", amount=req)
            r = False
        return r

    def run(self):
        """Runs the snob recruitment logic.

        This method checks if new snobs are needed and attempts to recruit them
        if all conditions are met.
        """
        if not self.can_snob:
            return False
        if self.building_level == 0:
            return False
        if self.wanted > 0:
            if "snob" not in self.troop_manager.total_troops:
                return self.attempt_recruit(amount=self.wanted)

            current = int(self.troop_manager.total_troops["snob"])
            if current < self.wanted:
                return self.attempt_recruit(amount=self.wanted - current)
            self.logger.info("Snob up-to-date (%d/%d)", current, self.wanted)
