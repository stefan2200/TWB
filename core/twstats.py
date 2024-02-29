import json
import logging
import sys
from collections import defaultdict

import requests
from pyquery import PyQuery as pq

from core.filemanager import FileManager


class TwStats:
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
        total = 0
        for b in buildings:
            if b in self.max_levels:
                total += self.max_levels[b][buildings[str(b)]]
        return total

    def get_building_data(self, world):
        output = defaultdict(dict)
        for upgrade_building in self.max_levels:
            geturl = "http://twstats.com/%s/index.php?page=buildings&detail=%s" % (world, upgrade_building)
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
            with open('../cache/world/buildings_%s.json' % world, 'w') as f:
                f.write(json.dumps(output))
        self.output = output
        return output

    def run(self, world):
        if self.output == {}:
            template = TwsCache.get_cache(world=world)
            if not template:
                self.logger.info("Syncing building -> pop levels with twstats.com")
                return self.get_building_data(world=world)
            self.output = template
            self.logger.debug("Using existing building -> pop levels")
            return template


class TwsCache:
    @staticmethod
    def get_cache(world):
        cache_path = "cache/world/buildings_%s.json" % world
        alt_cache_path = "../cache/world/buildings_%s.json" % world

        if FileManager.path_exists(cache_path):
            return FileManager.load_json_file(cache_path)
        elif FileManager.path_exists(alt_cache_path):
            return FileManager.load_json_file(alt_cache_path)
        return None


if __name__ == '__main__':
    TwStats().run(world=sys.argv[1])
