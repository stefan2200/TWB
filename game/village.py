import json
import logging
import os
import time
from codecs import decode
from datetime import datetime

from core.extractors import Extractor
from core.templates import TemplateManager
from core.twstats import TwStats
from game.attack import AttackManager
from game.buildingmanager import BuildingManager
from game.defence_manager import DefenceManager
from game.map import Map
from game.reports import ReportManager
from game.resources import ResourceManager
from game.snobber import SnobManager
from game.troopmanager import TroopManager


class Village:
    village_id = None
    builder = None
    units = None
    wrapper = None
    resources = {}
    game_data = {}
    logger = None
    force_troops = False
    area = None
    snob_man = None
    attack = None
    resource_manager = None
    def_man = None
    report_manager = None
    config = None
    village_set_name = None

    twp = TwStats()

    def __init__(self, village_id=None, wrapper=None):
        self.entry = None
        self.disabled_units = []
        self.data = None
        self.village_id = village_id
        self.wrapper = wrapper

    def get_config(self, section, parameter, default=None):
        if section not in self.config:
            self.logger.warning("Configuration section %s does not exist!" % section)
            return default
        if parameter not in self.config[section]:
            self.logger.warning(
                "Configuration parameter %s:%s does not exist!" % (section, parameter)
            )
            return default
        return self.config[section][parameter]

    def get_village_config(self, village_id, parameter, default=None):
        if village_id not in self.config["villages"]:
            return default
        vdata = self.config["villages"][village_id]
        if parameter not in vdata:
            self.logger.warning(
                "Village %s configuration parameter %s does not exist!"
                % (village_id, parameter)
            )
            return default
        return vdata[parameter]

    def run(self, config=None):
        self.config = config
        self.wrapper.delay = self.get_config(section="bot", parameter="delay_factor", default=1.0)

        if not self.setup_village():
            return None

        if not self.manage_game_data():
            return None

        if not self.verify_village_config():
            return False

        self.manage_resources()
        self.manage_reports()
        self.manage_defense()
        self.manage_buildings()
        self.manage_units()
        self.manage_snobs()
        self.manage_recruitment()
        self.manage_farms()
        self.manage_gathering()
        self.manage_market()
        self.manage_attacks()
        self.handle_quests()

        self.set_cache_vars()
        self.logger.info("Village cycle done, returning to overview")

    def setup_village(self):
        if not self.village_id:
            self.data = self.wrapper.get_url("game.php?screen=overview&intro")
        else:
            self.data = self.wrapper.get_url(f"game.php?village={self.village_id}&screen=overview")

        if not self.data:
            print("Error: No data available to extract game state.")
            return False

        self.game_data = Extractor.game_state(self.data)
        if not self.game_data:
            print("Error: Unable to retrieve village data. Check if self.game_data is properly initialized.")
            return False

        if not self.village_id:
            self.village_id = str(self.game_data["village"]["id"])
            self.logger = logging.getLogger("Village %s" % self.game_data["village"]["name"])
            self.logger.info("Read game state for village")
        else:
            village_name = self.game_data["village"]["name"]
            self.logger = logging.getLogger("Village %s" % village_name)
            self.logger.info("Read game state for village")
            self.wrapper.reporter.report(
                self.village_id,
                "TWB_START",
                f"Starting run for village: {village_name}",
            )

        return True

    def manage_game_data(self):
        if not self.game_data:
            self.logger.error("Error reading game data for village %s" % self.village_id)
            return False

        if self.village_set_name and self.game_data["village"]["name"] != self.village_set_name:
            self.logger.name = "Village %s" % self.village_set_name

        return True

    def verify_village_config(self):
        if not self.get_config(section="villages", parameter=self.village_id):
            return False

        return True

    def manage_resources(self):
        if not self.game_data:
            return

        if not self.resource_manager:
            self.resource_manager = ResourceManager(wrapper=self.wrapper, village_id=self.village_id)

        self.resource_manager.update(self.game_data)
        self.wrapper.reporter.report(
            self.village_id, "TWB_PRE_RESOURCE", str(self.resource_manager.actual)
        )

    def manage_reports(self):
        if not self.game_data:
            return

        if not self.report_manager:
            self.report_manager = ReportManager(wrapper=self.wrapper, village_id=self.village_id)

        self.report_manager.read(full_run=False)

    def manage_defense(self):
        if not self.game_data:
            return

        if not self.def_man:
            self.def_man = DefenceManager(wrapper=self.wrapper, village_id=self.village_id)
            self.def_man.map = self.area

        if not self.def_man.units:
            self.def_man.units = self.units

        last_attack = self.def_man.under_attack
        self.def_man.manage_flags_enabled = self.get_config(
            section="world", parameter="flags_enabled", default=False
        )
        self.def_man.support_factor = self.get_village_config(
            self.village_id, "support_others_factor", default=0.25
        )

        self.def_man.allow_support_send = self.get_village_config(
            self.village_id, parameter="support_others", default=False
        )
        self.def_man.allow_support_recv = self.get_village_config(
            self.village_id, parameter="request_support_on_attack", default=False
        )
        self.def_man.auto_evacuate = self.get_village_config(
            self.village_id, parameter="evacuate_fragile_units_on_attack", default=False
        )
        self.def_man.update(
            self.data.text,
            with_defence=self.get_config(
                section="units", parameter="manage_defence", default=False
            ),
        )

        disabled_units = []
        if not self.get_config(
                section="world", parameter="archers_enabled", default=True
        ):
            disabled_units.extend(["archer", "marcher"])

        if not self.get_config(
                section="world", parameter="building_destruction_enabled", default=True
        ):
            disabled_units.extend(["ram", "catapult"])

        if self.def_man.under_attack and not last_attack:
            self.logger.warning("Village under attack!")
            self.wrapper.reporter.report(
                self.village_id,
                "TWB_ATTACK",
                "Village: %s under attack" % self.game_data["village"]["name"],
            )

    def manage_buildings(self):
        if not self.game_data:
            return

        if not self.builder:
            self.builder = BuildingManager(wrapper=self.wrapper, village_id=self.village_id)
            self.builder.resource_manager = self.resource_manager

        if not self.get_village_config(self.village_id, parameter="managed", default=False):
            return False

        self.builder.start_update(
            build=self.get_config(
                section="building", parameter="manage_buildings", default=True
            ),
            set_village_name=self.village_set_name,
        )

    def manage_units(self):
        if not self.game_data:
            return

        if not self.units:
            self.units = TroopManager(wrapper=self.wrapper, village_id=self.village_id)
            self.units.resource_manager = self.resource_manager

        unit_config = self.get_village_config(
            self.village_id, parameter="units", default=None
        )
        if not unit_config:
            self.logger.warning(
                "Village %d does not have 'building' config override!" % self.village_id
            )
            unit_config = self.get_config(
                section="units", parameter="default", default="basic"
            )
        self.units.template = TemplateManager.get_template(
            category="troops", template=unit_config, output_json=True
        )
        self.entry = self.units.get_template_action(self.builder.levels)

        if self.entry and self.units.wanted != self.entry["build"]:
            self.logger.info(
                "%s as wanted units for current village" % (str(self.entry["build"]))
            )
            self.units.wanted = self.entry["build"]

        if self.units.wanted_levels != {}:
            for disabled in self.disabled_units:
                self.units.wanted_levels.pop(disabled, None)
            self.logger.info(
                "%s as wanted upgrades for current village"
                % (str(self.units.wanted_levels))
            )

        self.units.update_totals()
        if (
                self.get_config(section="units", parameter="upgrade", default=False)
                and self.units.wanted_levels != {}
        ):
            self.units.attempt_upgrade()

    def manage_snobs(self):
        if not self.game_data:
            return

        if (
                self.get_village_config(self.village_id, parameter="snobs", default=None)
                and self.builder.get_level("snob") > 0
        ):
            if not self.snob_man:
                self.snob_man = SnobManager(
                    wrapper=self.wrapper, village_id=self.village_id
                )
                self.snob_man.troop_manager = self.units
                self.snob_man.resource_manager = self.resource_manager
            self.snob_man.wanted = self.get_village_config(
                self.village_id, parameter="snobs", default=0
            )
            self.snob_man.building_level = self.builder.get_level("snob")
            self.snob_man.run()

    def manage_recruitment(self):
        if not self.game_data:
            return

        if self.get_config(section="units", parameter="recruit", default=False):
            self.units.can_fix_queue = self.get_config(
                section="units", parameter="remove_manual_queued", default=False
            )
            self.units.randomize_unit_queue = self.get_config(
                section="units", parameter="randomize_unit_queue", default=True
            )
            if (
                    self.get_village_config(
                        self.village_id, parameter="prioritize_building", default=False
                    )
                    and not self.resource_manager.can_recruit()
            ):
                self.logger.info(
                    "Not recruiting because builder has insufficient funds"
                )
                for x in list(self.resource_manager.requested.keys()):
                    if "recruitment_" in x:
                        self.resource_manager.requested.pop(f"{x}", None)
            elif (
                    self.get_village_config(
                        self.village_id, parameter="prioritize_snob", default=False
                    )
                    and self.snob_man
                    and self.snob_man.can_snob
                    and self.snob_man.is_incomplete
            ):
                self.logger.info("Not recruiting because snob has insufficient funds")
                for x in list(self.resource_manager.requested.keys()):
                    if "recruitment_" in x:
                        self.resource_manager.requested.pop(f"{x}", None)
            else:
                for building in self.units.wanted:
                    if not self.builder.get_level(building):
                        self.logger.debug(
                            "Recruit of %s will be ignored because building is not (yet) available"
                            % building
                        )
                        continue
                    self.units.start_update(building, self.disabled_units)

    def manage_farms(self):
        if not self.game_data:
            return

        if not self.area:
            self.area = Map(wrapper=self.wrapper, village_id=self.village_id)
        self.area.get_map()

        if not self.attack:
            self.attack = AttackManager(
                wrapper=self.wrapper,
                village_id=self.village_id,
                troopmanager=self.units,
                map=self.area,
            )
            self.attack.report_manager = self.report_manager

        self.attack.target_high_points = self.get_config(
            section="farms", parameter="attack_higher_points", default=False
        )
        self.attack.farm_min_points = self.get_config(
            section="farms", parameter="min_points", default=24
        )
        self.attack.farm_max_points = self.get_config(
            section="farms", parameter="max_points", default=1080
        )
        self.attack.farm_radius = self.get_config(
            section="farms", parameter="search_radius", default=50
        )
        self.attack.farm_default_wait = self.get_config(
            section="farms", parameter="default_away_time", default=1200
        )
        self.attack.farm_high_prio_wait = self.get_config(
            section="farms", parameter="full_loot_away_time", default=1800
        )
        self.attack.farm_low_prio_wait = self.get_config(
            section="farms", parameter="low_loot_away_time", default=7200
        )
        if self.entry:
            self.attack.template = self.entry["farm"]
        if (
                self.get_config(section="farms", parameter="farm", default=False)
                # and not self.def_man.under_attack todo fix and add to config
        ):
            self.attack.extra_farm = self.get_village_config(
                self.village_id, parameter="additional_farms", default=[]
            )
            self.attack.max_farms = self.get_config(
                section="farms", parameter="max_farms", default=25
            )
            self.attack.run()

    def manage_gathering(self):
        if not self.game_data:
            return

        if not self.def_man or not self.def_man.under_attack:
            self.units.gather(
                selection=self.get_village_config(
                    self.village_id, parameter="gather_selection", default=1
                ),
                disabled_units=self.disabled_units,
                advanced_gather=self.get_village_config(
                    self.village_id, parameter="advanced_gather", default=1
                ),
            )

    def manage_market(self):
        if not self.game_data:
            return

        if (
                self.get_config(section="market", parameter="auto_trade", default=False)
                and self.builder.get_level("market")
        ):
            self.resource_manager.manage_market(
                drop_existing=self.get_config(
                    section="market", parameter="auto_remove", default=True
                )
            )

    def manage_attacks(self):
        if not self.game_data:
            return

        forced_peace_times = self.get_config(
            section="farms", parameter="forced_peace_times", default=[]
        )
        forced_peace = False
        forced_peace_today = False
        forced_peace_today_start = None
        for time_pairs in forced_peace_times:
            start_dt = datetime.strptime(time_pairs["start"], "%d.%m.%y %H:%M:%S")
            end_dt = datetime.strptime(time_pairs["end"], "%d.%m.%y %H:%M:%S")
            now = datetime.now()
            if start_dt.date() == datetime.today().date():
                forced_peace_today = True
                forced_peace_today_start = start_dt
            if start_dt < now < end_dt:
                self.logger.debug(
                    "Currently in a forced peace time! No attacks will be send."
                )
                forced_peace = True
                break

        if not forced_peace and self.units.can_attack:
            if not self.area:
                self.area = Map(wrapper=self.wrapper, village_id=self.village_id)
            self.area.get_map()

            if self.area.villages:
                self.units.can_scout = self.get_config(
                    section="farms", parameter="force_scout_if_available", default=True
                )

                if forced_peace_today:
                    self.logger.info("Forced peace time coming up today!")
                    self.attack.forced_peace_time = forced_peace_today_start

                self.attack.run()

    def handle_quests(self):
        if not self.game_data:
            return

        if self.get_config(section="world", parameter="quests_enabled", default=False):
            if self.get_quests():
                self.logger.info("There were completed quests, re-running function")
                self.wrapper.reporter.report(
                    self.village_id, "TWB_QUEST", "Completed quest"
                )
                return self.run(config=self.config)

            if self.get_quest_rewards():
                self.wrapper.reporter.report(
                    self.village_id, "TWB_QUEST", "Collected quest reward(s)"
                )

    def get_quests(self):
        result = Extractor.get_quests(self.wrapper.last_response)
        if result:
            quest_response = self.wrapper.get_api_action(
                action="quest_complete",
                village_id=self.village_id,
                params={"quest": result, "skip": "false"},
            )
            if quest_response:
                self.logger.info("Completed quest: %s" % str(result))
                return True
        self.logger.debug("There where no completed quests")
        return False

    def get_quest_rewards(self):
        result = self.wrapper.get_api_data(
            action="quest_popup",
            village_id=self.village_id,
            params={"screen": "new_quests", "tab": "main-tab", "quest": 0},
        )
        # The data is escaped for JS, so unescape it before sending it to the extractor.
        rewards = Extractor.get_quest_rewards(
            decode(result["response"]["dialog"], "unicode-escape")
        )
        for reward in rewards:
            # First check if there is enough room for storing the reward
            for t_resource in reward["reward"]:
                if (
                    self.resource_manager.storage - self.resource_manager.actual[t_resource]
                    < reward["reward"][t_resource]
                ):
                    self.logger.info(
                        f"Not enough room to store the {t_resource} part of the reward"
                    )
                    return False

            quest_response = self.wrapper.post_api_data(
                action="claim_reward",
                village_id=self.village_id,
                params={"screen": "new_quests"},
                data={"reward_id": reward["id"]},
            )
            if quest_response and quest_response["response"]:
                self.logger.info("Got quest reward: %s" % str(reward))
                for t_resource, amount in reward["reward"].items():
                    self.resource_manager.actual[t_resource] += amount
            else:
                self.logger.debug(f"Error getting reward! {quest_response}")
                return False

        self.logger.debug("There where no (more) quest rewards")
        return len(rewards) > 0

    def set_cache_vars(self):
        village_entry = {
            "name": self.game_data["village"]["name"],
            "public": self.area.in_cache(self.village_id) if self.area else None,
            "resources": self.resource_manager.actual,
            "required_resources": self.resource_manager.requested,
            "available_troops": self.units.troops,
            "building_levels": self.builder.levels,
            "building_queue": self.builder.queue,
            "troops": self.units.total_troops,
            "under_attack": self.def_man.under_attack,
            "last_run": int(time.time()),
        }
        self.set_cache(self.village_id, entry=village_entry)

    @staticmethod
    def set_cache(village_id, entry):
        t_path = os.path.join(
            os.path.dirname(__file__), "..", "cache", "managed", village_id + ".json"
        )
        with open(t_path, "w") as f:
            return json.dump(entry, f)
