import time
import logging
import datetime

from core.extractors import Extractor
from game.simulator import Simulator


class Hunter:
    game_map = None
    schedule = {}
    target_villages = {}
    villages = []
    sim = Simulator()

    wrapper = None
    targets = {}
    # start timing 2m before attack start
    window = 120
    logger = logging.getLogger("Hunter")
    """
    attack 1: village 2: {axe: 12500, light: 1250, ram:100} 2000 sec
    attack 2: village 1: {axe: 7500, light: 2000, snob: 1} 4300 sec
    """

    def nearing_schedule_window(self):
        for item in self.schedule:
            wait = time.time() - item
            if wait < self.window:
                return item

    def nearing_window_in_sleep(self, sleep):
        lowest = None
        for item in self.schedule:
            wait = time.time() + sleep
            if item - self.window < wait:
                if not lowest or item < lowest:
                    lowest = item
        return lowest

    def troops_in_village(self, source=None, troops={}):
        if source:
            if self.villages[source].attack.has_troops_available(troops):
                return source
        for v in self.villages:
            if v.attack.has_troops_available(troops):
                return v

    def send_attack_chain(
        self, source, item, exact_send_time=0, min_sleep_amount_millis=100
    ):
        data = self.schedule[item]
        attack_set = []
        self.logger.info("Nearing timing window, preparing %d attacks" % len(data))
        for attack in data:
            result, duration = self.attack(source, item, troops=attack)
            attack_set.append(result)
        self.wrapper.priority_mode = True
        while time.time() < exact_send_time:
            time.sleep(0.001)
        a = datetime.datetime.now()
        for attk in attack_set:
            time.sleep(1000 / min_sleep_amount_millis)
            self.send_attack(source, attk)
        b = datetime.datetime.now()
        diff = b - a
        millis = 0
        millis += diff.seconds * 1000
        millis += diff.microseconds / 1000
        self.logger.info(
            "Sent %d attacks in %d milliseconds" % (len(attack_set), millis)
        )
        self.wrapper.priority_mode = False

    def attack(self, source, vid, troops=None):
        url = "game.php?village=%s&screen=place&target=%s" % (source, vid)
        pre_attack = self.wrapper.get_url(url)
        pre_data = {}
        for u in Extractor.attack_form(pre_attack):
            k, v = u
            pre_data[k] = v
        if troops:
            pre_data.update(troops)

        if vid not in self.game_map.map_pos:
            return False

        x, y = self.game_map.map_pos[vid]
        post_data = {"x": x, "y": y, "target_type": "coord", "attack": "Aanvallen"}
        pre_data.update(post_data)

        confirm_url = "game.php?village=%s&screen=place&try=confirm" % self.village_id
        conf = self.wrapper.post_url(url=confirm_url, data=pre_data)
        if '<div class="error_box">' in conf.text:
            return False
        duration = Extractor.attack_duration(conf)
        confirm_data = {}
        for u in Extractor.attack_form(conf):
            k, v = u
            if k == "support":
                continue
            confirm_data[k] = v
        new_data = {
            "building": "main",
            "h": self.wrapper.last_h,
        }
        confirm_data.update(new_data)
        if "x" not in confirm_data:
            confirm_data["x"] = x

        return confirm_data, duration

    def send_attack(self, source, data):
        return self.wrapper.get_api_action(
            village_id=source,
            action="popup_command",
            params={"screen": "place"},
            data=data,
        )

    def prepare(self, vid, troops=None):
        url = "game.php?village=%s&screen=place&target=%s" % (self.village_id, vid)
        pre_attack = self.wrapper.get_url(url)
        pre_data = {}
        for u in Extractor.attack_form(pre_attack):
            k, v = u
            pre_data[k] = v
        if troops:
            pre_data.update(troops)

        x, y = self.map.map_pos[vid]
        post_data = {"x": x, "y": y, "target_type": "coord", "attack": "Aanvallen"}
        pre_data.update(post_data)

        confirm_url = "game.php?village=%s&screen=place&try=confirm" % self.village_id
        conf = self.wrapper.post_url(url=confirm_url, data=pre_data)
        if '<div class="error_box">' in conf.text:
            return False
        duration = Extractor.attack_duration(conf)

        confirm_data = {}
        for u in Extractor.attack_form(conf):
            k, v = u
            if k == "support":
                continue
            confirm_data[k] = v
        new_data = {
            "building": "main",
            "h": self.wrapper.last_h,
        }
        confirm_data.update(new_data)
        if "x" not in confirm_data:
            confirm_data["x"] = x
        result = self.wrapper.get_api_action(
            village_id=self.village_id,
            action="popup_command",
            params={"screen": "place"},
            data=confirm_data,
        )

        return result
