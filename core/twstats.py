"""
Detects certain building levels from TWStats
"""

import json
import logging
import sys
from collections import defaultdict

import requests
from pyquery import PyQuery as pq

from core.filemanager import FileManager


class TwStats:
    """Fetches and manages building data from twstats.com.

    This class retrieves data such as the maximum population for each building
    level and caches it locally to avoid repeated requests.
    """
    max_levels = {
        'main': 30,
        'barracks': 25,
        'stable': 20,
        'garage': 15,
        'smith': 20,
        'snob': 3,
        'market': 25,
        'wood': 30,
        'stone': 30,
        'iron': 30,
        'wall': 20
    }

    output = {}
    logger = logging.getLogger("TwStats")

    def buildings_to_farm_pop(self, buildings):
        """Calculates the total farm population for a given set of buildings.

        Args:
            buildings (dict): A dictionary where keys are building names and values
                are their levels.

        Returns:
            int: The total farm population.
        """
        total = 0
        for b in buildings:
            if b in self.max_levels:
                total += self.max_levels[b][buildings[str(b)]]
        return total

    def get_building_data(self, world):
        """Fetches building data from twstats.com for a specific world.

        Args:
            world (str): The world to fetch data for (e.g., 'en100').

        Returns:
            defaultdict: A dictionary containing the building data.
        """
        output = defaultdict(dict)
        for upgrade_building in self.max_levels:
            geturl = f"http://twstats.com/{world}/index.php?page=buildings&detail={upgrade_building}"
            res = requests.get(geturl)
            table = pq(res.content).find("table.vis")

            for tr in table("tr")[1:]:
                tds = pq(tr).text().splitlines()
                building_level, village_population = int(tds[0]), int(tds[-1])
                output[upgrade_building][building_level] = village_population

        try:
            with open('cache/world/buildings_%s.json' % world, 'w') as f:
                f.write(json.dumps(output))
        except:
            with open(f"../cache/world/buildings_{world}.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(output))
        self.output = output
        return output

    def run(self, world):
        """Runs the update function to get building data.

        This method first checks for cached data and, if not found, fetches it
        from twstats.com.

        Args:
            world (str): The world to get data for.

        Returns:
            dict: A dictionary containing the building data.
        """
        if self.output == {}:
            template = TwsCache.get_cache(world=world)
            if not template:
                self.logger.info("Syncing building -> pop levels with twstats.com")
                return self.get_building_data(world=world)
            self.output = template
            self.logger.debug("Using existing building -> pop levels")
            return template


class TwsCache:
    """Manages cached data for TwStats."""
    @staticmethod
    def get_cache(world):
        """Gets the cached building data for a specific world.

        Args:
            world (str): The world to get cached data for.

        Returns:
            dict or None: The cached data as a dictionary, or None if no
                cache is found.
        """
        cache_path = f"cache/world/buildings_{world}.json"
        alt_cache_path = f"../cache/world/buildings_{world}.json"

        if FileManager.path_exists(cache_path):
            return FileManager.load_json_file(cache_path)
        elif FileManager.path_exists(alt_cache_path):
            return FileManager.load_json_file(alt_cache_path)
        return None


if __name__ == '__main__':
    TwStats().run(world=sys.argv[1])
