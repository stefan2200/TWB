import logging
import json
import re
from core.extractors import Extractor


class DefenceManager:
    wrapper = None
    village_id = None
    units = None
    map = None

    under_attack = False
    auto_evacuate = False
    attacks = []

    # list of village_id, attack_state
    my_other_villages = {}
    allow_support_send = True
    allow_support_recv = True

    defensive_units = ["spear", "sword", "archer", "marcher", "spy"]

    hide_units = ["snob", "axe"]

    flags = {}

    runs = 0
    logger = None
    manage_flags_enabled = False
    support_factor = 0.25
    support_max_villages = 2

    # flag_index, flag_level
    current_flag = []

    _can_change_flag = False

    # increased production
    set_flag_not_under_attack = 1
    # increased defence
    set_flag_under_attack = 4

    _sf_logged = False

    supported = []

    def __init__(self, village_id=None, wrapper=None):
        self.village_id = village_id
        self.wrapper = wrapper
        self.logger = logging.getLogger("Defence Manager")

    def support_other(self, requesting_village):

        if self.under_attack or not self.allow_support_send:
            return False
        if not self.units:
            return False
        send_support = {}
        for u in self.defensive_units:
            if u in self.units.troops and int(self.units.troops[u]) > 0:
                send_support[u] = int(int(self.units.troops[u]) * self.support_factor)

        self.logger.info(
            "Sending requested support to village %s: %s"
            % (requesting_village, str(send_support))
        )
        return self.support(requesting_village, troops=send_support)

    def update(self, main, with_defence=False):
        ok = True
        self.manage_flags()
        self.runs += 1
        if "command/attack.png" in main:
            self.under_attack = True
            ok = False
            self.flag_logic(self.set_flag_under_attack)
            if self.auto_evacuate and with_defence:
                self.evacuate()
        else:
            if not with_defence:
                self.under_attack = False
                return False
            self.under_attack = False
            self.flag_logic(self.set_flag_not_under_attack)
            index = 0

            for vil in self.my_other_villages:
                if vil != self.village_id:
                    continue
                if len(self.supported) >= self.support_max_villages:
                    self.logger.debug("Already supported 2 villages, ignoring")
                    break
                if (
                    not self.under_attack
                    and self.my_other_villages[vil]
                    and self.allow_support_send
                ):
                    if vil in self.supported:
                        continue
                    if index >= 2:
                        continue
                    if self.support_other(vil):
                        self.supported.append(vil)
                    ok = False
                index += 1
        if ok:
            self.logger.info("Area OK for village %s, nice and quiet" % self.village_id)
            # All is well
            self.flag_logic(self.set_flag_not_under_attack)

    def evacuate(self):
        if not self.units:
            return False
        to_hide = {}
        for u in self.hide_units:
            if u in self.units.troops and int(self.units.troops[u]) > 0:
                to_hide[u] = int(self.units.troops[u])
        if to_hide and len(self.my_other_villages) == 1:
            # good luck ;)
            return False
        for v_obj in self.my_other_villages:
            vid, attack_state = v_obj
            if vid == self.village_id:
                continue
            if not attack_state:
                self.logger.info(
                    "Evacuating troops from village %s: %s" % (vid, str(to_hide))
                )
                self.support(vid, troops=to_hide)
                return True

    def flag_logic(self, set_flag):
        if not self.manage_flags_enabled:
            return
        if not self._can_change_flag:
            if not self._sf_logged:
                self.logger.info(
                    "Unable to set new flag on village %s because of cool down"
                    % self.village_id
                )
                self._sf_logged = True
            return
        self._sf_logged = False
        if (
            not self.current_flag
            or self.current_flag[0] is not set_flag
            or self.get_highest_flag_possible(flag_id=set_flag) > self.current_flag[1]
        ):
            self.flag_set(
                set_flag, level=self.get_highest_flag_possible(flag_id=set_flag)
            )
            self.logger.info(
                "Setting flag %d level %d for village %s"
                % (
                    set_flag,
                    self.get_highest_flag_possible(flag_id=set_flag),
                    self.village_id,
                )
            )

    def flag_upgrade(self, flag, level):
        return self.wrapper.get_api_action(
            self.village_id,
            action="upgrade_flag",
            params={"screen": "flags", "h": self.wrapper.last_h},
            data={"flag_type": flag, "from_level": level},
        )

    def flag_set(self, flag, level):
        return self.wrapper.get_api_action(
            self.village_id,
            action="assign_flag",
            params={"screen": "flags", "h": self.wrapper.last_h},
            data={
                "flag_type": str(flag),
                "level": str(level),
                "village_id": self.village_id,
            },
        )

    def get_highest_flag_possible(self, flag_id=1):
        if flag_id not in self.flags:
            return None
        return self.flags[flag_id]

    def manage_flags(self):
        if not self.manage_flags_enabled:
            return
        if self.runs != 0 and self.runs % 5 != 0:
            return
        self.logger.info("Managing flags")

        url = "game.php?village=%s&screen=flags" % self.village_id
        result = self.wrapper.get_url(url=url)

        self._can_change_flag = '<span class="timer cooldown">' not in result.text

        get_flag_data = re.search(r"FlagsScreen\.setFlagCounts\((.+?)\);", result.text)
        if not get_flag_data:
            self.logger.warning("Error reading flag data")
            return
        get_current_flag = re.search(
            r'(?s)<div id="current_flag".+?/(\d+)_(\d+)\.png.+?<p>(.+?)</p>.+?</div>',
            result.text,
        )
        if get_current_flag:
            cflag = [int(get_current_flag.group(1)), int(get_current_flag.group(2))]
            if cflag != self.current_flag:
                self.current_flag = cflag
                self.logger.info(
                    "Current village flag: %s" % get_current_flag.group(3).strip()
                )
        upgraded = 0
        raw_flags = json.loads(get_flag_data.group(1))
        self.flags = {}
        for flag_type in raw_flags:
            for level in raw_flags[flag_type]:
                for amount in raw_flags[flag_type][level]:
                    if int(amount) >= 3:
                        self.flag_upgrade(flag=flag_type, level=level)
                        self.logger.info("Upgraded flag %s" % flag_type)
                        upgraded += 1
                    if int(amount) > 0:
                        if int(flag_type) not in self.flags or self.flags[
                            int(flag_type)
                        ] < int(level):
                            self.flags[int(flag_type)] = int(level)
        if upgraded:
            return self.manage_flags()

    def support(self, vid, troops=None):
        url = "game.php?village=%s&screen=place&target=%s" % (self.village_id, vid)
        pre_support = self.wrapper.get_url(url)
        pre_data = {}
        for u in Extractor.attack_form(pre_support):
            k, v = u
            pre_data[k] = v
        if troops:
            pre_data.update(troops)
        else:
            pre_data.update(self.units.troops)

        if vid not in self.map.map_pos:
            return False

        x, y = self.map.map_pos[vid]
        post_data = {"x": x, "y": y, "target_type": "coord", "support": "Ondersteunen"}
        pre_data.update(post_data)

        confirm_url = "game.php?village=%s&screen=place&try=confirm" % self.village_id
        conf = self.wrapper.post_url(url=confirm_url, data=pre_data)
        if '<div class="error_box">' in conf.text:
            return False
        duration = Extractor.attack_duration(conf)
        self.logger.info(
            "[Support] %s -> %s duration %f.1 h"
            % (self.village_id, vid, duration / 3600)
        )

        confirm_data = {}
        for u in Extractor.attack_form(conf):
            k, v = u
            if k == "attack":
                continue
            confirm_data[k] = v
        new_data = {"h": self.wrapper.last_h}
        confirm_data.update(new_data)
        if x not in confirm_data:
            confirm_data[x] = x
        result = self.wrapper.get_api_action(
            village_id=self.village_id,
            action="popup_command",
            params={"screen": "place"},
            data=confirm_data,
        )

        return result
