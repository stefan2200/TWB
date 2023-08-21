import math
from core.extractors import Extractor
import os
import json
import time


class Map:
    wrapper = None
    village_id = None
    map_data = []
    villages = {}
    my_location = None
    map_pos = {}
    last_fetch = 0
    fetch_delay = 8

    def __init__(self, wrapper=None, village_id=None):
        self.wrapper = wrapper
        self.village_id = village_id

    def get_map(self):
        if self.last_fetch + (self.fetch_delay * 3600) > time.time():
            return
        self.last_fetch = time.time()
        res = self.wrapper.get_action(village_id=self.village_id, action="map")
        game_state = Extractor.game_state(res)
        self.map_data = Extractor.map_data(res)
        if self.map_data:
            for tile in self.map_data:
                data = tile["data"]
                x = int(data["x"])
                y = int(data["y"])
                vdata = data["villages"]
                # Fix broken parsing                 
                if type(vdata) is dict:
                    cdata = [{}] * 20
                    for k, v in vdata.items():
                        if type(v) is not dict:
                            cdata[int(k)] = {0: item[0:] for item in v}
                        else:
                            cdata[int(k)] = v
                    vdata = cdata
                for lon, val in enumerate(vdata):
                    if not val:
                        continue
                    # Force dict type to iterate properly
                    if type(val) != dict:
                        val = {i: val[i] for i in range(0, len(val))}
                    for lat, entry in val.items():
                        if not lat:
                            continue
                        coords = [x + int(lon), y + int(lat)]
                        if entry[0] == str(self.village_id):
                            self.my_location = coords

                        self.build_cache_entry(location=coords, entry=entry)
                if not self.my_location:
                    self.my_location = [
                        game_state["village"]["x"],
                        game_state["village"]["y"],
                    ]
        if not self.map_data or not self.villages:
            return self.get_map_old(game_state=game_state)
        return True

    def get_map_old(self, game_state):
        if self.map_data:
            for tile in self.map_data:
                data = tile["data"]
                x = int(data["x"])
                y = int(data["y"])
                vdata = data["villages"]
                for lon, lon_val in enumerate(vdata):
                    try:
                        for lat in vdata[lon]:
                            coords = [x + int(lon), y + int(lat)]
                            entry = vdata[lon][lat]
                            if entry[0] == str(self.village_id):
                                self.my_location = coords

                            self.build_cache_entry(location=coords, entry=entry)
                    except:
                        raise
            if not self.my_location:
                self.my_location = [
                    game_state["village"]["x"],
                    game_state["village"]["y"],
                ]
        if not self.map_data or not self.villages:
            print(
                "Error reading map state for village %s, farming might not work properly"
                % self.village_id
            )
            return False
        return True

    def build_cache_entry(self, location, entry):
        vid = entry[0]
        name = entry[2]
        points = int(entry[3].replace(".", ""))
        player = entry[4]
        bonus = entry[6]
        clan = entry[11]
        structure = {
            "id": vid,
            "name": name,
            "location": location,
            "bonus": bonus,
            "points": points,
            "safe": False,
            "scout": False,
            "tribe": clan,
            "owner": player,
            "buildings": {},
            "resources": {},
        }
        self.map_pos[vid] = location
        cached = self.in_cache(vid)
        if not cached:
            MapCache.set_cache(village_id=vid, entry=structure)
        if cached and cached != structure:
            MapCache.set_cache(village_id=vid, entry=structure)
        self.villages[vid] = structure

    def in_cache(self, vid):
        entry = MapCache.get_cache(village_id=vid)
        return entry

    def get_dist(self, ext_loc):
        distance = math.sqrt(
            ((self.my_location[0] - ext_loc[0]) ** 2)
            + ((self.my_location[1] - ext_loc[1]) ** 2)
        )
        return distance


class MapCache:
    @staticmethod
    def get_cache(village_id):
        t_path = os.path.join(os.path.dirname(__file__), "..", "cache", "villages", village_id + ".json")
        if os.path.exists(t_path):
            with open(t_path, "r") as f:
                return json.load(f)
        return None

    @staticmethod
    def set_cache(village_id, entry):
        t_path = os.path.join(os.path.dirname(__file__), "..", "cache", "villages", village_id + ".json")
        with open(t_path, "w") as f:
            return f.write(json.dumps(entry))
