import json
import logging
import time
from codecs import decode
from datetime import datetime

from core.extractors import Extractor
from core.filemanager import FileManager
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
from core.exceptions import *


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
    snobman = None
    attack = None
    resman = None
    def_man = None
    rep_man = None
    config = None
    forced_peace_today = False
    village_set_name = None
    last_attack = None
    build_config = None
    current_unit_entry = None
    forced_peace = False
    forced_peace_today_start = None
    disabled_units = []

    twp = TwStats()

    def __init__(self, village_id=None, wrapper=None):
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
                "Village %s configuration parameter %s does not exist!",
                village_id, parameter
            )
            return default
        return vdata[parameter]

    def village_init(self):
        """
        Init the village entry and send first request
        """
        if not self.village_id:
            data = self.wrapper.get_url("game.php?screen=overview&intro")
            if data:
                self.game_data = Extractor.game_state(data)
            if self.game_data:
                self.village_id = str(self.game_data["village"]["id"])
                self.logger = logging.getLogger(
                    "Village %s" % self.game_data["village"]["name"]
                )
                self.logger.info("Read game state for village")
        else:
            data = self.wrapper.get_url(
                f"game.php?village={self.village_id}&screen=overview"
            )
            if data:
                self.game_data = Extractor.game_state(data)
                self.logger = logging.getLogger(
                    "Village %s" % self.game_data["village"]["name"]
                )
                self.logger.info("Read game state for village")
                self.wrapper.reporter.report(
                    self.village_id,
                    "TWB_START",
                    "Starting run for village: %s" % self.game_data["village"]["name"],
                )
        if (
                self.village_set_name
                and self.game_data["village"]["name"] != self.village_set_name
        ):
            self.logger.name = f"Village {self.village_set_name}"
        return data

    def set_world_config(self):
        """
        Sets basic world options
        """
        self.disabled_units = []
        if not self.get_config(
                section="world", parameter="archers_enabled", default=True
        ):
            self.disabled_units.extend(["archer", "marcher"])

        if not self.get_config(
                section="world", parameter="building_destruction_enabled", default=True
        ):
            self.disabled_units.extend(["ram", "catapult"])

        if self.get_config(
                section="server", parameter="server_on_twstats", default=False
        ):
            self.twp.run(world=self.get_config(section="server", parameter="server"))

    def update_pre_run(self):
        """
        Manage defence, resources and reports
        """
        if not self.resman:
            self.resman = ResourceManager(
                wrapper=self.wrapper, village_id=self.village_id
            )

        self.resman.update(self.game_data)
        self.wrapper.reporter.report(
            self.village_id, "TWB_PRE_RESOURCE", str(self.resman.actual)
        )

        if not self.rep_man:
            self.rep_man = ReportManager(
                wrapper=self.wrapper, village_id=self.village_id
            )
        self.rep_man.read(full_run=False)

        if not self.def_man:
            self.def_man = DefenceManager(
                wrapper=self.wrapper, village_id=self.village_id
            )
            self.def_man.map = self.area

        if not self.def_man.units and self.units:
            self.def_man.units = self.units

    def setup_defence_manager(self, data):
        """
        Set-up the defence manager
        """
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
            data.text,
            with_defence=self.get_config(
                section="units", parameter="manage_defence", default=False
            ),
        )
        if self.def_man.under_attack and not self.last_attack:
            self.logger.warning("Village under attack!")
            self.wrapper.reporter.report(
                self.village_id,
                "TWB_ATTACK",
                "Village: %s under attack" % self.game_data["village"]["name"],
            )
        self.last_attack = self.def_man.under_attack

    def run_quest_actions(self, config):
        if self.get_config(section="world", parameter="quests_enabled", default=False):
            if self.get_quests():
                self.logger.info("There where completed quests, re-running function")
                self.wrapper.reporter.report(
                    self.village_id, "TWB_QUEST", "Completed quest"
                )
                return self.run(config=config)

            if self.get_quest_rewards():
                self.wrapper.reporter.report(
                    self.village_id, "TWB_QUEST", "Collected quest reward(s)"
                )

    def units_get_template(self):
        """
        Fetches the unit template
        """
        if not self.units:
            self.units = TroopManager(wrapper=self.wrapper, village_id=self.village_id)
            self.units.resman = self.resman
        self.units.max_batch_size = self.get_config(
            section="units", parameter="batch_size", default=25
        )

        # set village templates
        unit_config = self.get_village_config(
            self.village_id, parameter="units", default=None
        )
        if not unit_config:
            self.logger.warning(
                "Village %d does not have 'units' config override!", self.village_id
            )
            unit_config = self.get_config(
                section="units", parameter="default", default="basic"
            )
        try:
            self.units.template = TemplateManager.get_template(
                category="troops", template=unit_config, output_json=True
            )
        except Exception as e:
            self.logger.error(
                "Looks like the unit template file %s is either missing or corrupted", unit_config
            )
            raise InvalidUnitTemplateException

    def run_builder(self):
        """
        Run building construction actions
        """
        if not self.builder:
            self.builder = BuildingManager(
                wrapper=self.wrapper, village_id=self.village_id
            )
            self.builder.resman = self.resman
            # manage buildings (has to always run because recruit check depends on building levels)
        self.build_config = self.get_village_config(
            self.village_id, parameter="building", default=None
        )
        if self.build_config is False:
            self.logger.debug("Builder is disabled for village %s", self.village_id)
            return
        if not self.build_config:
            self.logger.warning(
                "Village %d does not have 'building' config override!", self.village_id
            )
            self.build_config = self.get_config(
                section="building", parameter="default", default="purple_predator"
            )
        new_queue = TemplateManager.get_template(
            category="builder", template=self.build_config
        )
        if not self.builder.raw_template or self.builder.raw_template != new_queue:
            self.builder.queue = new_queue
            self.builder.raw_template = new_queue
            if not self.get_config(
                    section="world", parameter="knight_enabled", default=False
            ):
                self.builder.queue = [
                    x for x in self.builder.queue if "statue" not in x
                ]
        self.builder.max_lookahead = self.get_config(
            section="building", parameter="max_lookahead", default=2
        )
        self.builder.max_queue_len = self.get_config(
            section="building", parameter="max_queued_items", default=2
        )
        self.builder.start_update(
            build=self.get_config(
                section="building", parameter="manage_buildings", default=True
            ),
            set_village_name=self.village_set_name,
        )

    def run_snob_recruit(self):
        """
        Uses the snob to mint coins, store resources and recruit snobs
        """
        if (
                self.get_village_config(self.village_id, parameter="snobs", default=None)
                and self.builder.levels["snob"] > 0
        ):
            if not self.snobman:
                self.snobman = SnobManager(
                    wrapper=self.wrapper, village_id=self.village_id
                )
                self.snobman.troop_manager = self.units
                self.snobman.resman = self.resman
            self.snobman.wanted = self.get_village_config(
                self.village_id, parameter="snobs", default=0
            )
            self.snobman.building_level = self.builder.get_level("snob")
            self.snobman.run()

    def check_forced_peace(self):
        """
        Checks if farming is disabled for the current time
        """
        # Set timeslots in order to prevent farming during events like national holidays
        forced_peace_times = self.get_config(section="farms", parameter="forced_peace_times", default=[])
        self.forced_peace = False
        self.forced_peace_today = False
        self.forced_peace_today_start = None
        for time_pairs in forced_peace_times:
            start_dt = datetime.strptime(time_pairs["start"], "%d.%m.%y %H:%M:%S")
            end_dt = datetime.strptime(time_pairs["end"], "%d.%m.%y %H:%M:%S")
            now = datetime.now()
            if start_dt.date() == datetime.today().date():
                forced_peace_today = True
                forced_peace_today_start = start_dt
            if start_dt < now < end_dt:
                self.logger.debug("Currently in a forced peace time! No attacks will be send.")
                self.forced_peace = True
                break

    def set_unit_wanted_levels(self):
        """
        Fetches wanted units for the current buildings
        """
        self.current_unit_entry = self.units.get_template_action(self.builder.levels)

        if self.current_unit_entry and self.units.wanted != self.current_unit_entry["build"]:
            # update wanted units if template has changed
            self.logger.info(
                "%s as wanted units for current village", str(self.current_unit_entry["build"])
            )
            self.units.wanted = self.current_unit_entry["build"]

        if self.units.wanted_levels != {}:
            # Remove disabled units
            for disabled in self.disabled_units:
                self.units.wanted_levels.pop(disabled, None)
            self.logger.info(
                "%s as wanted upgrades for current village", str(self.units.wanted_levels)
            )

    def run_unit_upgrades(self):
        """
        Uses smith to research or upgrade units
        """
        if (
                self.get_config(section="units", parameter="upgrade", default=False)
                and self.units.wanted_levels != {}
        ):
            self.units.attempt_upgrade()

    def do_recruit(self):
        """
        Recruits new units
        """
        if self.get_config(section="units", parameter="recruit", default=False):
            self.units.can_fix_queue = self.get_config(
                section="units", parameter="remove_manual_queued", default=False
            )
            self.units.randomize_unit_queue = self.get_config(
                section="units", parameter="randomize_unit_queue", default=True
            )
            # prioritize_building: will only recruit when builder has sufficient funds for queue items
            if (
                    self.get_village_config(
                        self.village_id, parameter="prioritize_building", default=False
                    )
                    and not self.resman.can_recruit()
            ):
                self.logger.info(
                    "Not recruiting because builder has insufficient funds"
                )
                for x in list(self.resman.requested.keys()):
                    if "recruitment_" in x:
                        self.resman.requested.pop(f"{x}", None)
            elif (
                    self.get_village_config(
                        self.village_id, parameter="prioritize_snob", default=False
                    )
                    and self.snobman
                    and self.snobman.can_snob
                    and self.snobman.is_incomplete
            ):
                self.logger.info("Not recruiting because snob has insufficient funds")
                for x in list(self.resman.requested.keys()):
                    if "recruitment_" in x:
                        self.resman.requested.pop(f"{x}", None)
            else:
                # do a build run for every
                for building in self.units.wanted:
                    if not self.builder.get_level(building):
                        self.logger.debug(
                            "Recruit of %s will be ignored because building is not (yet) available", building
                        )
                        continue
                    self.units.start_update(building, self.disabled_units)

    def manage_local_resources(self):
        to_dell = []
        for x in self.resman.requested:
            if all(res == 0 for res in self.resman.requested[x].values()):
                # remove empty requests!
                to_dell.append(x)

        for x in to_dell:
            self.resman.requested.pop(x)

        self.logger.debug("Current resources: %s", str(self.resman.actual))
        self.logger.debug("Requested resources: %s", str(self.resman.requested))

    def set_farm_options(self):
        """
        Sets various options for farming management
        """
        self.attack.target_high_points = self.get_config(
            section="farms", parameter="attack_higher_points", default=False
        )
        self.attack.farm_minpoints = self.get_config(
            section="farms", parameter="min_points", default=24
        )
        self.attack.farm_maxpoints = self.get_config(
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
        self.attack.scout_farm_amount = self.get_config(
            section="farms", parameter="farm_scout_amount", default=5
        )
        if self.current_unit_entry:
            self.attack.template = self.current_unit_entry["farm"]

    def run_farming(self):
        """
        Runs the farming logic
        """
        if not self.forced_peace and self.units.can_attack:
            if not self.area:
                self.area = Map(wrapper=self.wrapper, village_id=self.village_id)
            self.area.get_map()
            if self.area.villages:
                self.units.can_scout = self.get_config(
                    section="farms", parameter="force_scout_if_available", default=True
                )
                self.logger.info(
                    "%d villages from map cache, (your location: %s)",
                        len(self.area.villages),
                        ":".join([str(x) for x in self.area.my_location])
                )
                if not self.attack:
                    self.attack = AttackManager(
                        wrapper=self.wrapper,
                        village_id=self.village_id,
                        troopmanager=self.units,
                        map=self.area,
                    )
                    self.attack.repman = self.rep_man

                if self.forced_peace_today:
                    self.logger.info("Forced peace time coming up today!")
                    self.attack.forced_peace_time = self.forced_peace_today_start
                self.set_farm_options()

                if (
                        self.get_config(section="farms", parameter="farm", default=False)
                        and not self.def_man.under_attack
                ):
                    self.attack.extra_farm = self.get_village_config(
                        self.village_id, parameter="additional_farms", default=[]
                    )
                    self.attack.max_farms = self.get_config(
                        section="farms", parameter="max_farms", default=25
                    )
                    self.attack.run()

    def do_gather(self):
        """
        Runs gathering if unlocked and active
        """
        self.units.can_gather = self.get_village_config(
            self.village_id, parameter="gather_enabled", default=False
        )
        if not self.def_man or not self.def_man.under_attack:
            self.units.gather(
                selection=self.get_village_config(
                    self.village_id, parameter="gather_selection", default=1
                ),
                disabled_units=self.disabled_units,
                advanced_gather=self.get_village_config(self.village_id, parameter="advanced_gather", default=1)
            )

    def go_manage_market(self):
        """
        Manages the market
        """
        if self.get_config(
                section="market", parameter="auto_trade", default=False
        ) and self.builder.get_level("market"):
            self.logger.info("Managing market")
            self.resman.trade_max_per_hour = self.get_config(
                section="market", parameter="trade_max_per_hour", default=1
            )
            self.resman.trade_max_duration = self.get_config(
                section="market", parameter="max_trade_duration", default=1
            )
            if self.get_config(
                    section="market", parameter="trade_multiplier", default=False
            ):
                self.resman.trade_bias = self.get_config(
                    section="market", parameter="trade_multiplier_value", default=1.0
                )
            self.resman.manage_market(
                drop_existing=self.get_config(
                    section="market", parameter="auto_remove", default=True
                )
            )

        res = self.wrapper.get_action(village_id=self.village_id, action="overview")
        self.game_data = Extractor.game_state(res)
        self.resman.update(self.game_data)
        if self.get_config(
                section="world", parameter="trade_for_premium", default=False
        ) and self.get_village_config(
            self.village_id, parameter="trade_for_premium", default=False
        ):
            # Set the parameter correctly when the config says so.
            self.resman.do_premium_trade = True
            self.resman.do_premium_stuff()

    def run(self, config=None, first_run=False):
        # setup and check if village still exists / is accessible
        self.config = config
        self.wrapper.delay = self.get_config(
            section="bot", parameter="delay_factor", default=1.0
        )

        data = self.village_init()

        if not self.game_data:
            self.logger.error(
                "Error reading game data for village %s", self.village_id
            )
            raise VillageInitException

        self.set_world_config()

        if not self.get_config(section="villages", parameter=self.village_id):
            raise VillageInitException

        vdata = self.get_config(section="villages", parameter=self.village_id)
        if not self.get_village_config(
                self.village_id, parameter="managed", default=False
        ):
            return False
        if not self.game_data:
            raise InvalidGameStateException

        self.update_pre_run()

        self.setup_defence_manager(data=data)
        self.run_quest_actions(config=config)

        self.run_builder()
        self.units_get_template()
        self.set_unit_wanted_levels()

        self.units.update_totals()
        self.run_unit_upgrades()
        self.run_snob_recruit()
        self.do_recruit()
        self.manage_local_resources()

        self.run_farming()

        self.do_gather()
        self.go_manage_market()

        self.set_cache_vars()
        self.logger.info("Village cycle done, returning to overview")
        self.wrapper.reporter.report(
            self.village_id, "TWB_POST_RESOURCE", str(self.resman.actual)
        )
        self.wrapper.reporter.add_data(
            self.village_id,
            data_type="village.resources",
            data=json.dumps(self.resman.actual),
        )
        self.wrapper.reporter.add_data(
            self.village_id,
            data_type="village.buildings",
            data=json.dumps(self.builder.levels),
        )
        self.wrapper.reporter.add_data(
            self.village_id,
            data_type="village.troops",
            data=json.dumps(self.units.total_troops),
        )
        self.wrapper.reporter.add_data(
            self.village_id, data_type="village.config", data=json.dumps(vdata)
        )

    def get_quests(self):
        result = Extractor.get_quests(self.wrapper.last_response)
        if result:
            qres = self.wrapper.get_api_action(
                action="quest_complete",
                village_id=self.village_id,
                params={"quest": result, "skip": "false"},
            )
            if qres:
                self.logger.info("Completed quest: %s", str(result))
                return True
        self.logger.debug("There where no completed quests")
        return False

    def get_quest_rewards(self):
        result = self.wrapper.get_api_data(
            action="quest_popup",
            village_id=self.village_id,
            params={"screen": 'new_quests', "tab": "main-tab", "quest": 0},
        )
        # The data is escaped for JS, so unescape it before sending it to the extractor.
        rewards = Extractor.get_quest_rewards(decode(result["response"]["dialog"], 'unicode-escape'))
        for reward in rewards:
            # First check if there is enough room for storing the reward
            for t_resource in reward["reward"]:
                if self.resman.storage - self.resman.actual[t_resource] < reward["reward"][t_resource]:
                    self.logger.info("Not enough room to store the %s part of the reward", t_resource)
                    return False

            qres = self.wrapper.post_api_data(
                action="claim_reward",
                village_id=self.village_id,
                params={"screen": "new_quests"},
                data={"reward_id": reward["id"]}
            )
            if qres:
                if not qres['response']:
                    self.logger.debug("Error getting reward! %s", qres)
                    return False
                else:
                    self.logger.info("Got quest reward: %s", str(reward))
                    for t_resource in reward["reward"]:
                        self.resman.actual[t_resource] += reward["reward"][t_resource]

        self.logger.debug("There where no (more) quest rewards")
        return len(rewards) > 0

    def set_cache_vars(self):
        village_entry = {
            "name": self.game_data["village"]["name"],
            "public": self.area.in_cache(self.village_id) if self.area else None,
            "resources": self.resman.actual,
            "required_resources": self.resman.requested,
            "available_troops": self.units.troops,
            "buidling_levels": self.builder.levels,
            "building_queue": self.builder.queue,
            "troops": self.units.total_troops,
            "under_attack": self.def_man.under_attack,
            "last_run": int(time.time()),
        }
        FileManager.save_json_file(village_entry, f"cache/managed/{self.village_id}.json")
