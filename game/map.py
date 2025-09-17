"""
Map management, pls don't read this code.
"""
import logging
import math
import time

from core.extractors import Extractor
from core.filemanager import FileManager


class Map:
    """Manages the in-game map and data about surrounding villages.

    This class fetches and parses map data to extract information about
    villages, such as their location, points, and owner. It also caches this
    data to avoid repeated requests.
    """
    wrapper = None
    village_id = None
    map_data = []
    villages = {}
    my_location = None
    map_pos = {}
    last_fetch = 0
    fetch_delay = 8

    def __init__(self, wrapper=None, village_id=None):
        """Initializes the Map.

        Args:
            wrapper (WebWrapper, optional): The web wrapper for making requests.
                Defaults to None.
            village_id (int, optional): The ID of the village. Defaults to None.
        """
        self.wrapper = wrapper
        self.village_id = village_id

    def get_map(self):
        """Fetches and updates the map data.

        This method fetches the map every 24ish hours and updates the cache
        entries for all visible villages.

        Returns:
            bool: True if the map was fetched and parsed successfully, False
                otherwise.
        """
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
        """Fetches and updates the map data using an older parsing method.

        This method is a fallback for when the primary `get_map` method fails.

        Args:
            game_state (dict): The current game state.

        Returns:
            bool: True if the map was fetched and parsed successfully, False
                otherwise.
        """
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
            logging.warning(
                "Error reading map state for village %s, farming might not work properly",
                self.village_id
            )
            return False
        return True

    def build_cache_entry(self, location, entry):
        """Builds a cache entry for a village.

        Args:
            location (list): The coordinates of the village.
            entry (list): The raw data for the village.
        """
        vid = entry[0]
        name = entry[2]
        try:
            points = int(entry[3].replace(".", ""))
        except ValueError:
            # Breaks farming logic on event villages
            return
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
        """Checks if a village is already in the cache.

        Args:
            vid (int): The ID of the village.

        Returns:
            dict or None: The cache entry if found, otherwise None.
        """
        entry = MapCache.get_cache(village_id=vid)
        return entry

    def get_dist(self, ext_loc):
        """Calculates the distance from the current village to a set of coordinates.

        Args:
            ext_loc (list): The coordinates of the external location.

        Returns:
            float: The distance to the external location.
        """
        distance = math.sqrt(
            ((self.my_location[0] - ext_loc[0]) ** 2)
            + ((self.my_location[1] - ext_loc[1]) ** 2)
        )
        return distance


class MapCache:
    """Manages the cache for map data."""
    @staticmethod
    def get_cache(village_id):
        """Gets the cache entry for a specific village.

        Args:
            village_id (int): The ID of the village.

        Returns:
            dict or None: The cache entry as a dictionary, or None if not found.
        """
        return FileManager.load_json_file(f"cache/villages/{village_id}.json")

    @staticmethod
    def set_cache(village_id, entry):
        """Creates or updates a cache entry for a village.

        Args:
            village_id (int): The ID of the village.
            entry (dict): The cache entry to save.
        """
        FileManager.save_json_file(entry, f"cache/villages/{village_id}.json")
