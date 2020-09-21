import logging
import json

from game.buildingmanager import BuildingManager
from game.troopmanager import TroopManager
from game.attack import AttackManager
from game.map import Map
from game.resources import ResourceManager
from game.defence_manager import DefenceManager
from game.reports import ReportManager
from game.snobber import SnobManager

from core.extractors import Extractor
from core.templates import TemplateManager
from core.twplus import TwPlus


class Village:
    village_id = None
    builder = None
    units = None
    wrapper = None
    resources = {

    }
    game_data = {

    }
    logger = None
    force_troops = False
    area = None
    snobman = None
    attack = None
    resman = None
    def_man = None
    rep_man = None
    config = None
    twp = TwPlus()

    def __init__(self, village_id=None, wrapper=None):
        self.village_id = village_id
        self.wrapper = wrapper

    def run(self, config=None):
        # setup and check if village still exists / is accessible
        self.config = config
        if not self.village_id:
            data = self.wrapper.get_url("game.php?screen=overview&intro")
            if data:
                self.game_data = Extractor.game_state(data)
            if self.game_data:
                self.village_id = str(self.game_data['village']['id'])
                self.logger = logging.getLogger("Village %s" % self.game_data['village']['name'])
                self.logger.info("Read game state for village")
        else:
            data = self.wrapper.get_url("game.php?village=%s&screen=overview" % self.village_id)
            if data:
                self.game_data = Extractor.game_state(data)
                self.logger = logging.getLogger("Village %s" % self.game_data['village']['name'])
                self.logger.info("Read game state for village")
                self.wrapper.reporter.report(self.village_id, "TWB_START", "Starting run for village: %s" % self.game_data['village']['name'])

        if str(self.village_id) not in self.config['villages']:
            return False
        if config['server']['server_on_twplus']:
            self.twp.run(world=self.config['server']['world'])

        vdata = self.config['villages'][str(self.village_id)]
        if not vdata['managed']:
            return False
        if not self.game_data:
            return False

        # setup modules
        if not self.resman:
            self.resman = ResourceManager(wrapper=self.wrapper, village_id=self.village_id)

        self.resman.update(self.game_data)
        self.wrapper.reporter.report(self.village_id, "TWB_PRE_RESOURCE", str(self.resman.actual))

        if not self.rep_man:
            self.rep_man = ReportManager(wrapper=self.wrapper, village_id=self.village_id)
        self.rep_man.read(full_run=False)

        if not self.def_man:
            self.def_man = DefenceManager(wrapper=self.wrapper, village_id=self.village_id)
        last_attack = self.def_man.under_attack
        self.def_man.manage_flags_enabled = config['world']['flags_enabled']
        self.def_man.update(data.text)
        if self.def_man.under_attack and not last_attack:
            self.logger.warning("Village under attack!")
            self.wrapper.reporter.report(self.village_id, "TWB_ATTACK",
                                 "Village: %s under attack" % self.game_data['village']['name'])

        # setup and check if village still exists / is accessible
        if self.config['world']['quests_enabled']:
            if self.get_quests():
                self.logger.info("There where completed quests, re-running function")
                self.wrapper.reporter.report(self.village_id, "TWB_QUEST",
                                     "Completed quest")
                return self.run(config=config)

        if not self.builder:
            self.builder = BuildingManager(wrapper=self.wrapper, village_id=self.village_id)
            self.builder.resman = self.resman
            # manage buildings (has to always run because recruit check depends on building levels)
            build_config = vdata['building'] if vdata['building'] else self.config['building']['default']

            self.builder.queue = TemplateManager.get_template(category="builder", template=build_config)
        self.builder.max_lookahead = self.config['building']['max_lookahead']
        self.builder.max_queue_len = self.config['building']['max_queued_items']
        self.builder.start_update(build=self.config['building']['manage_buildings'])

        if not self.units:
            self.units = TroopManager(wrapper=self.wrapper, village_id=self.village_id)
            self.units.max_batch_size = self.config['units']['batch_size']
            self.units.resman = self.resman

        # set village templates
        unit_config = vdata['units'] if vdata['units'] else self.config['units']['default']
        self.units.template = TemplateManager.get_template(category="troops", template=unit_config, output_json=True)
        entry = self.units.get_template_action(self.builder.levels)

        if entry and self.units.wanted != entry["build"]:
            # update wanted units if template has changed
            self.logger.info("%s as wanted units for current village" % (str(entry["build"])))
            self.units.wanted = entry["build"]

        if entry and 'upgrades' in entry and self.units.wanted_levels != entry['upgrades']:
            self.logger.info("%s as wanted upgrades for current village" % (str(entry["upgrades"])))
            self.units.wanted_levels = entry['upgrades']

        # get total amount of troops in village
        self.units.update_totals()
        if self.config['units']['upgrade'] and self.units.wanted_levels != {}:
            self.units.attempt_upgrade(self.units.wanted_levels)

        if 'snobs' in vdata and self.builder.levels['snob'] > 0:
            if not self.snobman:
                self.snobman = SnobManager(wrapper=self.wrapper, village_id=self.village_id)
                self.snobman.troop_manager = self.units
                self.snobman.resman = self.resman
            self.snobman.wanted = vdata['snobs']
            self.snobman.building_level = self.builder.levels['snob']
            self.snobman.run()

        # recruitment management
        if self.config['units']['recruit']:
            # prioritize_building: will only recruit when builder has sufficient funds for queue items
            if vdata['prioritize_building'] and not self.resman.can_recruit():
                self.logger.info("Not recruiting because builder has insufficient funds")
            elif vdata['prioritize_snob'] and self.snobman and self.snobman.can_snob and self.snobman.is_incomplete:
                self.logger.info("Not recruiting because snob has insufficient funds")
            else:
                # do a build run for every
                for building in self.units.wanted:
                    if building not in self.builder.levels or self.builder.levels[building] == 0:
                        self.logger.debug("Recruit of %s will be ignored because building is not available" % building)
                        continue
                    self.units.start_update(building)

        self.logger.debug("Current resources: %s" % str(self.resman.actual))
        self.logger.debug("Requested resources: %s" % str(self.resman.requested))
        # attack management
        if self.units.can_attack:
            if not self.area:
                self.area = Map(wrapper=self.wrapper, village_id=self.village_id)
            self.area.get_map()
            if self.area.villages:
                self.units.can_scout = config['farms']['force_scout_if_available']
                self.logger.info("%d villages from map cache, (your location: %s)" % (
                len(self.area.villages), ':'.join([str(x) for x in self.area.my_location])))
                if not self.attack:
                    self.attack = AttackManager(wrapper=self.wrapper, village_id=self.village_id,
                                                troopmanager=self.units, map=self.area)
                    self.attack.repman = self.rep_man
                    self.attack.target_high_points = config['farms']['attack_higher_points']
                    self.attack.farm_minpoints = config['farms']['min_points']
                    self.attack.farm_maxpoints = config['farms']['max_points']
                if entry:
                    self.attack.template = entry['farm']
                if self.config['farms']['farm'] and not self.def_man.under_attack:
                    self.attack.extra_farm = vdata['additional_farms']
                    self.attack.max_farms = self.config['farms']['max_farms']
                    self.attack.run()

        self.units.can_gather = vdata['gather_enabled']
        if not self.def_man.under_attack:
            self.units.gather(selection=vdata['gather_selection'])
        # market management
        if self.config['market']['auto_trade'] and "market" in self.builder.levels and self.builder.levels["market"] > 0:
            self.logger.info("Managing market")
            self.resman.trade_max_per_hour = self.config['market']['trade_max_per_hour']
            self.resman.trade_max_duration = self.config['market']['max_trade_duration']
            if self.config['market']['trade_multiplier']:
                self.resman.trade_bias = self.config['market']['trade_multiplier_value']
            self.resman.manage_market(drop_existing=self.config['market']['auto_remove'])

        res = self.wrapper.get_action(village_id=self.village_id, action="overview")
        self.game_data = Extractor.game_state(res)
        self.resman.update(self.game_data)
        if config['world']['trade_for_premium'] and vdata['trade_for_premium']:
            self.resman.do_premium_trade()

        self.logger.info("Village cycle done, returning to overview")
        self.wrapper.reporter.report(self.village_id, "TWB_POST_RESOURCE", str(self.resman.actual))
        self.wrapper.reporter.add_data(self.village_id, data_type="village.resources", data=json.dumps(self.resman.actual))
        self.wrapper.reporter.add_data(self.village_id, data_type="village.buildings", data=json.dumps(self.builder.levels))
        self.wrapper.reporter.add_data(self.village_id, data_type="village.troops", data=json.dumps(self.units.total_troops))
        self.wrapper.reporter.add_data(self.village_id, data_type="village.config", data=json.dumps(vdata))

    def get_quests(self):
        result = Extractor.get_quests(self.wrapper.last_response)
        if result:
            qres = self.wrapper.get_api_action(action="quest_complete", village_id=self.village_id, params={'quest': result, 'skip': 'false'})
            if qres:
                self.logger.info("Completed quest: %s" % str(result))
                return True
        self.logger.debug("There where no completed quests")
        return False
