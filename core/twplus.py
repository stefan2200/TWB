import requests
import re
import json
import os
import sys
import logging


class TwPlus:
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
    logger = logging.getLogger("TwPlus")

    def buildings_to_farm_pop(self, buildings):
        total = 0
        for b in buildings:
            if b in self.max_levels:
                total += self.max_levels[b][buildings[str(b)]]
        return total

    def get_building_data(self, world):
        output = {

        }
        for x in range(1, 31):
            out_params = {}
            for building in self.max_levels:
                if self.max_levels[building] >= x:
                    out_params[building] = x
            geturl = "http://%s.twplus.org/calculator/building/" % world
            res = requests.get(geturl, params=out_params)
            bdata = re.search('(?s)<form.+?id="buildingform">(.+?)</form>', res.text)
            if not bdata:
                print("Error reading twplus information for world: %s!!!!" % world)
                return

            table = bdata.group(1)
            body = table.split('<tbody>')[1].split('</tbody>')[0].strip()

            for tr in re.findall(r'(?s)<tr.*?>(.+?)</tr>', body):
                tds = re.findall(r'(?s)<td.*?>(.+?)</td>', tr)
                vil_pop = tds[3]
                vil_pop = re.search(r'(?s)<div.+?</div>\s*(\d+)', vil_pop)
                vil_pop = int(vil_pop.group(1)) if vil_pop else 0
                building_name = re.search(r'name="(\w+)"', tds[1]).group(1)
                if building_name not in self.max_levels:
                    continue
                if building_name not in output:
                    output[building_name] = {x: vil_pop}
                else:
                    output[building_name][x] = vil_pop
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
            template = TwpCache.get_cache(world=world)
            if not template:
                self.logger.info("Syncing building -> pop levels with twplus.org")
                return self.get_building_data(world=world)
            self.output = template
            self.logger.debug("Using existing building -> pop levels")
            return template


class TwpCache:
    @staticmethod
    def get_cache(world):
        t_path = os.path.join("cache", "world", "buildings_%s" % world + ".json")
        if os.path.exists(t_path):
            with open(t_path, 'r') as f:
                return json.load(f)
        else:
            t_path = os.path.join("../", "cache", "world", "buildings_%s" % world + ".json")
            if os.path.exists(t_path):
                with open(t_path, 'r') as f:
                    return json.load(f)
        return None


if __name__ == '__main__':
    TwPlus().run(world=sys.argv[1])
