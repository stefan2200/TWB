import time
import os
import json
from core.extractors import Extractor
import logging
import time
from datetime import datetime
from datetime import timedelta

from game.reports import ReportCache


class AttackManager:
    map = None
    village_id = None
    troopmanager = None
    wrapper = None
    targets = {}
    logger = logging.getLogger("Attacks")
    max_farms = 15
    template = {}
    extra_farm = []
    repman = None
    target_high_points = False
    farm_radius = 50
    farm_minpoints = 0
    farm_maxpoints = 1000
    ignored = []

    forced_peace_time = None

    # blocks villages which cannot be attacked at the moment (too low points, beginners protection etc..)
    _unknown_ignored = []

    farm_high_prio_wait = 1200
    farm_default_wait = 3600
    farm_low_prio_wait = 7200

    def __init__(self, wrapper=None, village_id=None, troopmanager=None, map=None):
        self.wrapper = wrapper
        self.village_id = village_id
        self.troopmanager = troopmanager
        self.map = map

    def enough_in_village(self, units):
        for u in units:
            if u not in self.troopmanager.troops:
                return "%s (0/%d)" % (u, units[u])
            if units[u] > int(self.troopmanager.troops[u]):
                return "%s (%s/%d)" % (u, self.troopmanager.troops[u], units[u])
        return False

    def run(self):
        if not self.troopmanager.can_attack or self.troopmanager.troops == {}:
            return False
        self.get_targets()
        ignored = []
        for target in self.targets[0 : self.max_farms]:
            if type(self.template) == list:
                f = False
                for template in self.template:
                    if template in ignored:
                        continue
                    out_res = self.send_farm(target, template)
                    if out_res == 1:
                        f = True
                        break
                    elif out_res == -1:
                        ignored.append(template)
                if not f:
                    continue
            else:
                out_res = self.send_farm(target, self.template)
                if out_res == -1:
                    break

    def send_farm(self, target, template):
        target, distance = target
        missing = self.enough_in_village(template)
        if not missing:
            cached = self.can_attack(vid=target["id"], clear=False)
            if cached:
                attack_result = self.attack(target["id"], troops=template)
                if attack_result == "forced_peace":
                    return 0
                self.logger.info(
                    "Attacking %s -> %s (%s)"
                    % (self.village_id, target["id"], str(template))
                )
                self.wrapper.reporter.report(
                    self.village_id,
                    "TWB_FARM",
                    "Attacking %s -> %s (%s)"
                    % (self.village_id, target["id"], str(template)),
                )
                if attack_result:
                    for u in template:
                        self.troopmanager.troops[u] = str(
                            int(self.troopmanager.troops[u]) - template[u]
                        )
                    self.attacked(
                        target["id"],
                        scout=True,
                        safe=True,
                        high_profile=cached["high_profile"]
                        if type(cached) == dict
                        else False,
                        low_profile=cached["low_profile"]
                        if type(cached) == dict and "low_profile" in cached
                        else False,
                    )
                    return 1
                else:
                    self.logger.debug(
                        "Ignoring target %s because unable to attack" % target["id"]
                    )
                    self._unknown_ignored.append(target["id"])
        else:
            self.logger.debug(
                "Not sending additional farm because not enough units: %s" % missing
            )
            return -1
        return 0

    def get_targets(self):
        output = []
        my_village = (
            self.map.villages[self.village_id]
            if self.village_id in self.map.villages
            else None
        )
        for vid in self.map.villages:
            village = self.map.villages[vid]
            if village["owner"] != "0" and vid not in self.extra_farm:
                if vid not in self.ignored:
                    self.logger.debug(
                        "Ignoring village %s because player owned, add to additional_farms to auto attack"
                        % vid
                    )
                    self.ignored.append(vid)
                continue
            if my_village and "points" in my_village and "points" in village:
                if village["points"] >= self.farm_maxpoints:
                    if vid not in self.ignored:
                        self.logger.debug(
                            "Ignoring village %s because points %d exceeds limit %d"
                            % (vid, village["points"], self.farm_maxpoints)
                        )
                        self.ignored.append(vid)
                    continue
                if village["points"] <= self.farm_minpoints:
                    if vid not in self.ignored:
                        self.logger.debug(
                            "Ignoring village %s because points %d below limit %d"
                            % (vid, village["points"], self.farm_minpoints)
                        )
                        self.ignored.append(vid)
                    continue
                if (
                    village["points"] >= my_village["points"]
                    and not self.target_high_points
                ):
                    if vid not in self.ignored:
                        self.logger.debug(
                            "Ignoring village %s because of higher points %d -> %d"
                            % (vid, my_village["points"], village["points"])
                        )
                        self.ignored.append(vid)
                    continue
                if vid in self._unknown_ignored:
                    continue
            if village["owner"] != "0":
                get_h = time.localtime().tm_hour
                if get_h in range(0, 8) or get_h == 23:
                    self.logger.debug(
                        "Village %s will be ignored because it is player owned and attack between 23h-8h"
                        % vid
                    )
                    continue
            distance = self.map.get_dist(village["location"])
            if distance > self.farm_radius:
                if vid not in self.ignored:
                    self.logger.debug(
                        "Village %s will be ignored because it is too far away: distance is %f, max is %d"
                        % (vid, distance, self.farm_radius)
                    )
                    self.ignored.append(vid)
                continue
            if vid in self.ignored:
                self.logger.debug("Removed %s from farm ignore list" % vid)
                self.ignored.remove(vid)

            output.append([village, distance])
        self.logger.info(
            "Farm targets: %d Ignored targets: %d" % (len(output), len(self.ignored))
        )
        self.targets = sorted(output, key=lambda x: x[1])

    def attacked(
        self, vid, scout=False, high_profile=False, safe=True, low_profile=False
    ):
        cache_entry = {
            "scout": scout,
            "safe": safe,
            "high_profile": high_profile,
            "low_profile": low_profile,
            "last_attack": int(time.time()),
        }
        AttackCache.set_cache(vid, cache_entry)

    def scout(self, vid):
        if (
            "spy" not in self.troopmanager.troops
            or int(self.troopmanager.troops["spy"]) < 5
        ):
            self.logger.debug(
                "Cannot scout %s at the moment because insufficient unit: spy" % vid
            )
            return False
        troops = {"spy": 5}
        if self.attack(vid, troops=troops):
            self.attacked(vid, scout=True, safe=False)

    def can_attack(self, vid, clear=False):
        cache_entry = AttackCache.get_cache(vid)

        if cache_entry and cache_entry["last_attack"]:
            last_attack = datetime.fromtimestamp(cache_entry["last_attack"])
            now = datetime.now()
            if last_attack < now - timedelta(hours=12):
                self.logger.debug(
                    f"Attacked long ago({last_attack}), trying scout attack"
                )
                if self.scout(vid):
                    return False

        if not cache_entry:
            status = self.repman.safe_to_engage(vid)
            if status == 1:
                return True

            if self.troopmanager.can_scout:
                self.scout(vid)
                return False
            self.logger.warning(
                "%s will be attacked but scouting is not possible (yet), going in blind!"
                % vid
            )
            return True

        if not cache_entry["safe"] or clear:
            if cache_entry["scout"] and self.repman:
                status = self.repman.safe_to_engage(vid)
                if status == -1:
                    self.logger.info(
                        "Checking %s: scout report not yet available" % vid
                    )
                    return False
                if status == 0:
                    if cache_entry["last_attack"] + self.farm_low_prio_wait * 2 > int(
                        time.time()
                    ):
                        self.logger.info(
                            f"{vid}: Old scout report found ({cache_entry['last_attack']}), re-scouting"
                        )
                        self.scout(vid)
                        return False
                    else:
                        self.logger.info(
                            "%s: scout report noted enemy units, ignoring" % vid
                        )
                        return False
                self.logger.info(
                    "%s: scout report noted no enemy units, attacking" % vid
                )
                return True

            self.logger.debug(
                "%s will be ignored for attack because unsafe, set safe:true to override"
                % vid
            )
            return False

        if not cache_entry["scout"] and self.troopmanager.can_scout:
            self.scout(vid)
            return False
        min_time = self.farm_default_wait
        if cache_entry["high_profile"]:
            min_time = self.farm_high_prio_wait
        if "low_profile" in cache_entry and cache_entry["low_profile"]:
            min_time = self.farm_low_prio_wait

        if cache_entry and self.repman:
            res_left, res = self.repman.has_resources_left(vid)
            total_loot = 0
            for x in res:
                total_loot += int(res[x])

            if res_left and total_loot > 100:
                self.logger.debug(
                    f"Draining farm of resources! Sending attack to get {res}."
                )
                min_time = int(self.farm_high_prio_wait / 2)

        if cache_entry["last_attack"] + min_time > int(time.time()):
            self.logger.debug(
                "%s will be ignored because of previous attack (%d sec delay between attacks)"
                % (vid, min_time)
            )
            return False
        return cache_entry

    def has_troops_available(self, troops):
        for t in troops:
            if (
                t not in self.troopmanager.troops
                or int(self.troopmanager.troops[t]) < troops[t]
            ):
                return False
        return True

    def attack(self, vid, troops=None):
        url = "game.php?village=%s&screen=place&target=%s" % (self.village_id, vid)
        pre_attack = self.wrapper.get_url(url)
        pre_data = {}
        for u in Extractor.attack_form(pre_attack):
            k, v = u
            pre_data[k] = v
        if troops:
            pre_data.update(troops)
        else:
            pre_data.update(self.troopmanager.troops)

        if vid not in self.map.map_pos:
            return False

        x, y = self.map.map_pos[vid]
        post_data = {"x": x, "y": y, "target_type": "coord", "attack": "Aanvallen"}
        pre_data.update(post_data)

        confirm_url = "game.php?village=%s&screen=place&try=confirm" % self.village_id
        conf = self.wrapper.post_url(url=confirm_url, data=pre_data)
        if (
            conf is not None
            and hasattr(conf, "text")
            and '<div class="error_box">' in conf.text
        ):
            return False
        duration = Extractor.attack_duration(conf)
        if self.forced_peace_time:
            now = datetime.now()
            if now + timedelta(seconds=duration) > self.forced_peace_time:
                self.logger.info(
                    "Attack would arrive after the forced peace timer, not sending attack!"
                )
                return "forced_peace"

        self.logger.info(
            "[Attack] %s -> %s duration %f.1 h"
            % (self.village_id, vid, duration / 3600)
        )

        confirm_data = {}
        for u in Extractor.attack_form(conf):
            k, v = u
            if k == "support":
                continue
            confirm_data[k] = v
        new_data = {"building": "main", "h": self.wrapper.last_h}
        confirm_data.update(new_data)
        # The extractor doesn't like the empty cb value, and mistakes its value for x. So I add it here.
        if "x" not in confirm_data:
            confirm_data["x"] = x

        result = self.wrapper.get_api_action(
            village_id=self.village_id,
            action="popup_command",
            params={"screen": "place"},
            data=confirm_data,
        )

        return result


class AttackCache:
    @staticmethod
    def get_cache(village_id):
        t_path = os.path.join(
            os.path.dirname(__file__), "..", "cache", "attacks", village_id + ".json"
        )
        if os.path.exists(t_path):
            with open(t_path, "r") as f:
                return json.load(f)
        return None

    @staticmethod
    def set_cache(village_id, entry):
        t_path = os.path.join(
            os.path.dirname(__file__), "..", "cache", "attacks", village_id + ".json"
        )
        with open(t_path, "w") as f:
            return json.dump(entry, f)

    @staticmethod
    def cache_grab():
        output = {}
        c_path = os.path.join(os.path.dirname(__file__), "..", "cache", "attacks")
        for existing in os.listdir(c_path):
            if not existing.endswith(".json"):
                continue
            t_path = os.path.join(
                os.path.dirname(__file__), "..", "cache", "attacks", existing
            )
            with open(t_path, "r") as f:
                output[existing.replace(".json", "")] = json.load(f)
        return output
