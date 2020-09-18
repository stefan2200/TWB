from core.extractors import Extractor
import logging
import math
import time


class TroopManager:
    can_recruit = True
    can_attack = True
    can_dodge = False
    can_scout = False
    can_farm = True
    can_gather = False

    queue = []
    troops = {

    }

    total_troops = {

    }

    wrapper = None
    village_id = None
    recruit_data = {}
    game_data = {}
    logger = None
    max_batch_size = 50
    wait_for = {
        'barracks': 0,
        'stable': 0,
        'garage': 0
    }

    wanted = {
        'barracks': {

        }
    }

    unit_building = {
        "spear": "barracks",
        "sword": "barracks",
        "axe": "barracks",
        "archer": "barracks",
        "spy": "stable",
        "light": "stable",
        "marcher": "stable",
        "heavy": "stable"
    }

    wanted_levels = {

    }

    last_gather = 0

    resman = None
    template = None

    def __init__(self, wrapper=None, village_id=None):
        self.wrapper = wrapper
        self.village_id = village_id

    def update_totals(self):
        main_data = self.wrapper.get_action(action="overview", village_id=self.village_id)
        self.game_data = Extractor.game_state(main_data)
        if not self.logger:
            self.logger = logging.getLogger("Recruitment: %s" % self.game_data['village']['name'])
        self.troops = {}
        for u in Extractor.units_in_village(main_data):
            k, v = u
            self.troops[k] = v

        self.logger.debug("Units in village: %s" % str(self.troops))

        if not self.can_recruit:
            return

        get_all = "game.php?village=%s&screen=place&mode=units&display=units" % self.village_id
        result_all = self.wrapper.get_url(get_all)
        self.total_troops = {}
        for u in Extractor.units_in_total(result_all):
            k, v = u
            if k in self.total_troops:
                self.total_troops[k] = self.total_troops[k] + int(v)
            else:
                self.total_troops[k] = int(v)
        self.logger.debug("Village units total: %s" % str(self.total_troops))

    def start_update(self, building="barracks"):

        if self.wait_for[building] > time.time():
            self.logger.info("%s still busy for %d seconds" % (building, self.wait_for[building] - time.time()))
            return False

        if True:
            for wanted in self.wanted[building]:
                if wanted not in self.total_troops:
                    if self.recruit(wanted, self.wanted[building][wanted], building=building):
                        return True
                    continue

                if self.wanted[building][wanted] > self.total_troops[wanted]:
                    if self.recruit(wanted, self.wanted[building][wanted] - self.total_troops[wanted], building=building):
                        return True

        self.logger.info("Recruitment:%s up-to-date" % building)
        return False

    def get_min_possible(self, entry):
        # why i love python
        return min([
            math.floor(self.game_data['village']['wood'] / entry['wood']),
            math.floor(self.game_data['village']['stone'] / entry['stone']),
            math.floor(self.game_data['village']['iron'] / entry['iron']),
            math.floor((self.game_data['village']['pop_max'] - self.game_data['village']['pop']) / entry['pop'])])

    def get_template_action(self, levels):
        last = None
        for x in self.template:
            if x['building'] not in levels:
                return last

            if x['level'] > levels[x['building']]:
                return last

            last = x
        return last

    def attempt_upgrade(self, unit_levels):
        self.logger.debug("Managing Upgrades")
        result = self.wrapper.get_action(village_id=self.village_id, action="smith")
        smith_data = Extractor.smith_data(result)
        for unit_type in unit_levels:
            if not smith_data or unit_type not in smith_data['available']:
                self.logger.warning("Unit %s does not appear to be available or smith not built yet" % unit_type)
                continue
            wanted_level = unit_levels[unit_type]
            current_level = int(smith_data['available'][unit_type]['level'])
            if current_level < wanted_level:
                attempt = self.attempt_research(unit_type, smith_data=smith_data)
                if attempt:
                    self.logger.info("Started smith upgrade of %s %d -> %d" % (unit_type, current_level, current_level+1))
                    return True
        return False

    def attempt_research(self, unit_type, smith_data=None):
        if not smith_data:
            result = self.wrapper.get_action(village_id=self.village_id, action="smith")
            smith_data = Extractor.smith_data(result)
        if not smith_data or unit_type not in smith_data['available']:
            self.logger.warning("Unit %s does not appear to be available or smith not built yet" % unit_type)
            return
        data = smith_data['available'][unit_type]
        if 'can_research' in data and data['can_research']:
            if 'research_error' in data and data['research_error']:
                return False
            if 'error_buildings' in data and data['error_buildings']:
                return False
            res = self.wrapper.get_api_action(village_id=self.village_id,
                                              action="research",
                                              params={"screen": "smith"},
                                              data={
                                                  "tech_id": unit_type,
                                                  "source": self.village_id,
                                                  'h': self.wrapper.last_h
                                              })
            if res:
                self.logger.info("Started research of %s" % unit_type)
                self.resman.update(res['game_data'])
                return True
        self.logger.info("Research of %s not yet possible" % unit_type)

    def gather(self):
        if not self.can_gather:
            return False
        url = "game.php?village=%s&screen=place&mode=scavenge" % self.village_id
        result = self.wrapper.get_url(url=url)
        if '"scavenging_squad":{' in result.text:
            self.logger.debug("Ignoring scavenge because already one underway")
            return False
        troops = dict(self.troops)

        can_use = ["spear:25", "sword:15", "axe:10", "archer:10", "light:80", "marcher:50", "heavy:50", "knight:100"]
        payload = {
            'squad_requests[0][village_id]': self.village_id,
            'squad_requests[0][option_id]': '1',
            'squad_requests[0][use_premium]': 'false'
        }

        total_carry = 0
        for item in can_use:
            item, carry = item.split(':')
            if item == "knight":
                continue
            if item in troops and int(troops[item]) > 0:
                payload["squad_requests[0][candidate_squad][unit_counts][%s]" % item] = troops[item]
                total_carry += int(carry) * int(troops[item])
            else:
                payload["squad_requests[0][candidate_squad][unit_counts][%s]" % item] = '0'
        payload['squad_requests[0][candidate_squad][carry_max]'] = str(total_carry)
        if total_carry > 0:
            payload['h'] = self.wrapper.last_h
            self.wrapper.get_api_action(action="send_squads", params={'screen': 'scavenge_api'}, data=payload, village_id=self.village_id)
            self.last_gather = int(time.time())
            self.logger.info("Using troops for gather operation: 1")
            return True

    def recruit(self, unit_type, amount=10, wait_for=False, building="barracks"):
        data = self.wrapper.get_action(action=building, village_id=self.village_id)
        self.recruit_data = Extractor.recruit_data(data)
        self.game_data = Extractor.game_state(data)
        self.logger.info("Attempting recruitment of %d %s" % (amount, unit_type))

        if amount > self.max_batch_size:
            amount = self.max_batch_size

        if unit_type not in self.recruit_data:
            self.logger.warning("Recruitment of %d %s failed because it is not researched" % (amount, unit_type))
            self.attempt_research(unit_type)
            return False

        resources = self.recruit_data[unit_type]
        if not resources:
            self.logger.warning("Recruitment of %d %s failed because invalid identifier" % (amount, unit_type))
            return False
        if not resources['requirements_met']:
            self.logger.warning("Recruitment of %d %s failed because it is not researched" % (amount, unit_type))
            self.attempt_research(unit_type)
            return False

        get_min = self.get_min_possible(resources)
        if get_min == 0:
            self.logger.info("Recruitment of %d %s failed because of not enough resources" % (amount, unit_type))
            return False
        if get_min < amount:
            if wait_for:
                self.logger.warning("Recruitment of %d %s failed because of not enough resources" % (amount, unit_type))
                return False
            if get_min > 0:
                self.logger.info("Recruitment of %d %s was set to %d because of resources" % (amount, unit_type, get_min))
                amount = get_min
        result = self.wrapper.get_api_action(village_id=self.village_id, action="train",
                                           params={"screen": building, "mode": "train"},
                                           data={"units[%s]" % unit_type: str(amount)})
        if 'game_data' in result:
            self.resman.update(result['game_data'])
            self.wait_for[building] = int(time.time()) + (amount * int(resources['build_time']))
            # self.troops[unit_type] = str((int(self.troops[unit_type]) if unit_type in self.troops else 0) + amount)
            self.logger.info("Recruitment of %d %s started (%s idle till %d)" %
                              (amount, unit_type, building, self.wait_for[building]))
            return True
        return False










