import logging
import json
import re


class DefenceManager:
    wrapper = None
    village_id = None

    under_attack = False
    attacks = []

    dodge_clear = True

    defensive_units = [
        "spear",
        "sword",
        "archer",
        "marcher",
        "spy"
    ]

    hide_units = [
        "snob",
        "axe"
    ]

    flags = {

    }

    runs = 0
    logger = None
    manage_flags_enabled = False

    def __init__(self, village_id=None, wrapper=None):
        self.village_id = village_id
        self.wrapper = wrapper
        self.logger = logging.getLogger("Defence Manager")

    def update(self, main):
        self.manage_flags()
        self.runs += 1
        if "command/attack.png" in main:
            self.under_attack = True

    def flag_upgrade(self, flag, level):
        return self.wrapper.get_api_action(self.village_id, action="upgrade_flag",
                                           params={'screen': "flags"}, data={"flag_type": flag, "from_level": level})

    def manage_flags(self):
        if not self.manage_flags_enabled:
            return
        if self.runs != 0 and self.runs % 5 != 0:
            return
        self.logger.info("Managing flags")

        url = "game.php?village=%s&screen=flags" % self.village_id
        result = self.wrapper.get_url(url=url)

        get_flag_data = re.search(r"FlagsScreen\.setFlagCounts\((.+?)\);", result.text)
        if not get_flag_data:
            self.logger.warning("Error reading flag data")
            return
        upgraded = 0
        raw_flags = json.loads(get_flag_data.group(1))
        for flag_type in raw_flags:
            for level in raw_flags[flag_type]:
                for amount in raw_flags[flag_type][level]:
                    if int(amount) >= 3:
                        self.flag_upgrade(flag=flag_type, level=level)
                        self.logger.info("Upgraded flag %s" % flag_type)
                        upgraded += 1
        if upgraded:
            return self.manage_flags()
