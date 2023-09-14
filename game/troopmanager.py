import logging
import math
import re
import time
import random

from core.extractors import Extractor
from game.resources import ResourceManager


class TroopManager:
    can_recruit = True
    can_attack = True
    can_dodge = False
    can_scout = True
    can_farm = True
    can_gather = True
    can_fix_queue = True
    randomize_unit_queue = True

    queue = []
    troops = {}

    total_troops = {}

    _research_wait = 0

    wrapper = None
    village_id = None
    recruit_data = {}
    game_data = {}
    logger = None
    max_batch_size = 50
    wait_for = {}

    _waits = {}

    wanted = {"barracks": {}}

    unit_building = {
        "spear": "barracks",
        "sword": "barracks",
        "axe": "barracks",
        "archer": "barracks",
        "spy": "stable",
        "light": "stable",
        "marcher": "stable",
        "heavy": "stable",
        "ram": "garage",
        "catapult": "garage",
    }

    wanted_levels = {}

    last_gather = 0

    resman = None
    template = None

    def __init__(self, wrapper=None, village_id=None):
        self.wrapper = wrapper
        self.village_id = village_id
        self.wait_for[village_id] = {"barracks": 0, "stable": 0, "garage": 0}
        if not self.resman:
            self.resman = ResourceManager(
                wrapper=self.wrapper, village_id=self.village_id
            )

    def update_totals(self):
        main_data = self.wrapper.get_action(
            action="overview", village_id=self.village_id
        )
        self.game_data = Extractor.game_state(main_data)

        if self.resman:
            if "research" in self.resman.requested:
                # new run, remove request
                self.resman.requested["research"] = {}

        if not self.logger:
            self.logger = logging.getLogger(
                "Recruitment: %s" % self.game_data["village"]["name"]
            )
        self.troops = {}

        get_all = (
            "game.php?village=%s&screen=place&mode=units&display=units"
            % self.village_id
        )
        result_all = self.wrapper.get_url(get_all)

        for u in Extractor.units_in_village(result_all):
            k, v = u
            self.troops[k] = v

        self.logger.debug("Units in village: %s" % str(self.troops))

        if not self.can_recruit:
            return

        self.total_troops = {}
        for u in Extractor.units_in_total(result_all):
            k, v = u
            if k in self.total_troops:
                self.total_troops[k] = self.total_troops[k] + int(v)
            else:
                self.total_troops[k] = int(v)
        self.logger.debug("Village units total: %s" % str(self.total_troops))

    def start_update(self, building="barracks", disabled_units=[]):

        if self.wait_for[self.village_id][building] > time.time():
            self.logger.info(
                "%s still busy for %s"
                % (building, self.readable_ts(self.wait_for[self.village_id][building]))
            )
            return False

        run_selection = list(self.wanted[building].keys())
        if self.randomize_unit_queue:
            random.shuffle(run_selection)

        for wanted in run_selection:
            # Ignore disabled units
            if wanted in disabled_units:
                continue

            if wanted not in self.total_troops:
                if self.recruit(
                    wanted, self.wanted[building][wanted], building=building
                ):
                    return True
                continue

            if self.wanted[building][wanted] > self.total_troops[wanted]:
                if self.recruit(
                    wanted,
                    self.wanted[building][wanted] - self.total_troops[wanted],
                    building=building,
                ):
                    return True

        self.logger.info("Recruitment:%s up-to-date" % building)
        return False

    def get_min_possible(self, entry):
        # why i love python
        return min(
            [
                math.floor(self.game_data["village"]["wood"] / entry["wood"]),
                math.floor(self.game_data["village"]["stone"] / entry["stone"]),
                math.floor(self.game_data["village"]["iron"] / entry["iron"]),
                math.floor(
                    (
                        self.game_data["village"]["pop_max"]
                        - self.game_data["village"]["pop"]
                    )
                    / entry["pop"]
                ),
            ]
        )

    def get_template_action(self, levels):
        last = None
        wanted_upgrades = {}
        for x in self.template:
            if x["building"] not in levels:
                return last

            if x["level"] > levels[x["building"]]:
                return last

            last = x
            if "upgrades" in x:
                for unit in x["upgrades"]:
                    if (
                        unit not in wanted_upgrades
                        or x["upgrades"][unit] > wanted_upgrades[unit]
                    ):
                        wanted_upgrades[unit] = x["upgrades"][unit]

            self.wanted_levels = wanted_upgrades
        return last

    def research_time(self, time_str):
        parts = [int(x) for x in time_str.split(":")]
        return parts[2] + (parts[1] * 60) + (parts[0] * 60 * 60)

    def attempt_upgrade(self):
        self.logger.debug("Managing Upgrades")
        if self._research_wait > time.time():
            self.logger.debug(
                "Smith still busy for %d seconds"
                % int(self._research_wait - time.time())
            )
            return
        unit_levels = self.wanted_levels
        if not unit_levels:
            self.logger.debug("Not upgrading because nothing is requested")
            return
        result = self.wrapper.get_action(village_id=self.village_id, action="smith")
        smith_data = Extractor.smith_data(result)
        if not smith_data:
            self.logger.debug("Error reading smith data")
            return False
        for unit_type in unit_levels:
            if not smith_data or unit_type not in smith_data["available"]:
                self.logger.warning(
                    "Unit %s does not appear to be available or smith not built yet"
                    % unit_type
                )
                continue
            wanted_level = unit_levels[unit_type]
            current_level = int(smith_data["available"][unit_type]["level"])
            data = smith_data["available"][unit_type]

            if (
                current_level < wanted_level
                and "can_research" in data
                and data["can_research"]
            ):
                if "research_error" in data and data["research_error"]:
                    self.logger.debug(
                        "Skipping research of %s because of research error" % unit_type
                    )
                    # Add needed resources to res manager?
                    r = True
                    if data["wood"] > self.game_data["village"]["wood"]:
                        req = data["wood"] - self.game_data["village"]["wood"]
                        self.resman.request(source="research", resource="wood", amount=req)
                        r = False
                    if data["stone"] > self.game_data["village"]["stone"]:
                        req = data["stone"] - self.game_data["village"]["stone"]
                        self.resman.request(source="research", resource="stone", amount=req)
                        r = False
                    if data["iron"] > self.game_data["village"]["iron"]:
                        req = data["iron"] - self.game_data["village"]["iron"]
                        self.resman.request(source="research", resource="iron", amount=req)
                        r = False
                    if not r:
                        self.logger.debug("Research needs resources")
                    continue
                if "error_buildings" in data and data["error_buildings"]:
                    self.logger.debug(
                        "Skipping research of %s because of building error" % unit_type
                    )
                    continue

                attempt = self.attempt_research(unit_type, smith_data=smith_data)
                if attempt:
                    self.logger.info(
                        "Started smith upgrade of %s %d -> %d"
                        % (unit_type, current_level, current_level + 1)
                    )
                    self.wrapper.reporter.report(
                        self.village_id,
                        "TWB_UPGRADE",
                        "Started smith upgrade of %s %d -> %d"
                        % (unit_type, current_level, current_level + 1),
                    )
                    return True
        return False

    def attempt_research(self, unit_type, smith_data=None):
        if not smith_data:
            result = self.wrapper.get_action(village_id=self.village_id, action="smith")
            smith_data = Extractor.smith_data(result)
        if not smith_data or unit_type not in smith_data["available"]:
            self.logger.warning(
                "Unit %s does not appear to be available or smith not built yet"
                % unit_type
            )
            return
        data = smith_data["available"][unit_type]
        if "can_research" in data and data["can_research"]:
            if "research_error" in data and data["research_error"]:
                self.logger.debug(
                    "Ignoring research of %s because of resource error %s"
                    % (unit_type, str(data["research_error"]))
                )
                # Add needed resources to res manager?
                r = True
                if data["wood"] > self.game_data["village"]["wood"]:
                    req = data["wood"] - self.game_data["village"]["wood"]
                    self.resman.request(source="research", resource="wood", amount=req)
                    r = False
                if data["stone"] > self.game_data["village"]["stone"]:
                    req = data["stone"] - self.game_data["village"]["stone"]
                    self.resman.request(source="research", resource="stone", amount=req)
                    r = False
                if data["iron"] > self.game_data["village"]["iron"]:
                    req = data["iron"] - self.game_data["village"]["iron"]
                    self.resman.request(source="research", resource="iron", amount=req)
                    r = False
                if not r:
                    self.logger.debug("Research needs resources")
                return False
            if "error_buildings" in data and data["error_buildings"]:
                self.logger.debug(
                    "Ignoring research of %s because of building error %s"
                    % (unit_type, str(data["error_buildings"]))
                )
                return False
            if (
                "level" in data
                and "level_highest" in data
                and data["level_highest"] != 0
                and data["level"] == data["level_highest"]
            ):
                return False
            res = self.wrapper.get_api_action(
                village_id=self.village_id,
                action="research",
                params={"screen": "smith"},
                data={
                    "tech_id": unit_type,
                    "source": self.village_id,
                    "h": self.wrapper.last_h,
                },
            )
            if res:
                if "research_time" in data:
                    self._research_wait = time.time() + self.research_time(
                        data["research_time"]
                    )
                self.logger.info("Started research of %s" % unit_type)
                # self.resman.update(res["game_data"])
                return True
        self.logger.info("Research of %s not yet possible" % unit_type)

    def gather(self, selection=1, disabled_units=[], advanced_gather=True):

        if not self.can_gather:
            return False
        url = "game.php?village=%s&screen=place&mode=scavenge" % self.village_id
        result = self.wrapper.get_url(url=url)
        village_data = Extractor.village_data(result)

        sleep = 0
        available_selection = 0

        self.troops = {}

        get_all = (
            "game.php?village=%s&screen=place&mode=units&display=units"
            % self.village_id
        )
        result_all = self.wrapper.get_url(get_all)

        for u in Extractor.units_in_village(result_all):
            k, v = u
            self.troops[k] = v

        troops = dict(self.troops)

        haul_dict = [
                        "spear:25",
                        "sword:15",
                        "heavy:50",
                        "axe:10",
                        "light:80"
                    ]
        if "archer" in self.total_troops:
            haul_dict.extend(["archer:10", "marcher:50"])

        # ADVANCED GATHER: Goes from gather_selection to 1, trying the same time (approximately) for every gather. Active hours exclude LC and Axes, at night everything is used for gather (except Paladin)

        if advanced_gather:
            selection_map = [15, 21, 24, 26] #Divider in order to split the total carrying capacity of the troops into pieces that can fit into pretty much the same time frame

            batch_multiplier = [15, 6, 3, 2] #Multiplier for equal distribution of troops. Time(gather1) = Time(gather2) if gather2 = 2.5 * gather1

            troops = {key: int(value) for key, value in troops.items()}
            total_carry = 0
            for item in haul_dict:
                item, carry = item.split(":")
                if item == "knight":
                    continue
                if item in disabled_units:
                    continue
                if item in troops and int(troops[item]) > 0:
                    total_carry += int(carry) * int(troops[item])
                else:
                    pass
            gather_batch = math.floor(total_carry/selection_map[selection - 1])


            for option in list(reversed(sorted(village_data['options'].keys())))[4 - selection:]:
                self.logger.debug(f"Option: {option} Locked? {village_data['options'][option]['is_locked']} Is underway? {village_data['options'][option]['scavenging_squad'] != None }")
                if int(option) <= selection and not village_data['options'][option]['is_locked'] and not village_data['options'][option]['scavenging_squad'] != None:
                    available_selection = int(option)
                    self.logger.info(f"Gather operation {available_selection} is ready to start.")
                    
                    

                    payload = {
                        "squad_requests[0][village_id]": self.village_id,
                        "squad_requests[0][option_id]": str(available_selection),
                        "squad_requests[0][use_premium]": "false",
                    }
                    
                    

                    curr_haul = gather_batch * batch_multiplier[available_selection - 1]
                    temp_haul = curr_haul

                    self.logger.debug(f"Current Haul: {curr_haul} = Gather Batch ({gather_batch}) * Batch Multiplier {available_selection} ({batch_multiplier[available_selection - 1]})")
                    
                    for item in haul_dict:
                        item, carry = item.split(":")
                        if item == "knight":
                            continue
                        if item in disabled_units:
                            continue
                        
                        if item in troops and int(troops[item]) > 0:
                            troops_int = int(troops[item])
                            troops_selected = 0
                            for troop in range(troops_int):
                                if (temp_haul - int(carry) < 0):
                                    break
                                else:
                                    troops_selected += 1
                                    temp_haul -= int(carry)
                            troops_int -= troops_selected
                            troops[item] = str(troops_int)
                            payload["squad_requests[0][candidate_squad][unit_counts][%s]" % item] = str(troops_selected)
                        else:
                            payload["squad_requests[0][candidate_squad][unit_counts][%s]" % item] = "0"
                    payload["squad_requests[0][candidate_squad][carry_max]"] = str(curr_haul)
                    payload["h"] = self.wrapper.last_h
                    self.wrapper.get_api_action(
                        action="send_squads",
                        params={"screen": "scavenge_api"},
                        data=payload,
                        village_id=self.village_id,
                    )
                    sleep += random.randint(1, 5)
                    time.sleep(sleep)
                    self.last_gather = int(time.time())
                    self.logger.info(f"Using troops for gather operation: {available_selection}")
                else:
                    # Gathering already exists or locked
                    break
            
        else:
             for option in reversed(sorted(village_data['options'].keys())):
                self.logger.debug(f"Option: {option} Locked? {village_data['options'][option]['is_locked']} Is underway? {village_data['options'][option]['scavenging_squad'] != None }")
                if int(option) <= selection and not village_data['options'][option]['is_locked'] and not village_data['options'][option]['scavenging_squad'] != None:
                    available_selection = int(option)
                    self.logger.info(f"Gather operation {available_selection} is ready to start.")
                    selection = available_selection

                    payload = {
                        "squad_requests[0][village_id]": self.village_id,
                        "squad_requests[0][option_id]": str(available_selection),
                        "squad_requests[0][use_premium]": "false",
                    }
                    total_carry = 0
                    for item in haul_dict:
                        item, carry = item.split(":")
                        if item == "knight":
                            continue
                        if item in disabled_units:
                            continue
                        if item in troops and int(troops[item]) > 0:
                            payload[
                                "squad_requests[0][candidate_squad][unit_counts][%s]" % item
                            ] = troops[item]
                            total_carry += int(carry) * int(troops[item])
                        else:
                            payload[
                                "squad_requests[0][candidate_squad][unit_counts][%s]" % item
                            ] = "0"
                    payload["squad_requests[0][candidate_squad][carry_max]"] = str(total_carry)
                    if total_carry > 0:
                        payload["h"] = self.wrapper.last_h
                        self.wrapper.get_api_action(
                            action="send_squads",
                            params={"screen": "scavenge_api"},
                            data=payload,
                            village_id=self.village_id,
                        )
                        self.last_gather = int(time.time())
                        self.logger.info(f"Using troops for gather operation: {selection}")
                else:
                    # Gathering already exists or locked
                    break
        self.logger.info("All gather operations are underway.")
        return True

    def cancel(self, building, id):
        self.wrapper.get_api_action(
            action="cancel",
            params={"screen": building},
            data={"id": id},
            village_id=self.village_id,
        )

    def recruit(self, unit_type, amount=10, wait_for=False, building="barracks"):
        data = self.wrapper.get_action(action=building, village_id=self.village_id)

        existing = Extractor.active_recruit_queue(data)
        if existing:
            self.logger.warning(
                "Building Village %s %s recruitment queue out-of-sync"
                % (self.village_id, building)
            )
            if not self.can_fix_queue:
                return True
            for entry in existing:
                self.cancel(building=building, id=entry)
                self.logger.info(
                    "Canceled recruit item %s on building %s" % (entry, building)
                )
            return self.recruit(unit_type, amount, wait_for, building)

        self.recruit_data = Extractor.recruit_data(data)
        self.game_data = Extractor.game_state(data)
        self.logger.info("Attempting recruitment of %d %s" % (amount, unit_type))

        if amount > self.max_batch_size:
            amount = self.max_batch_size

        if unit_type not in self.recruit_data:
            self.logger.warning(
                "Recruitment of %d %s failed because it is not researched"
                % (amount, unit_type)
            )
            self.attempt_research(unit_type)
            return False

        resources = self.recruit_data[unit_type]
        if not resources:
            self.logger.warning(
                "Recruitment of %d %s failed because invalid identifier"
                % (amount, unit_type)
            )
            return False
        if not resources["requirements_met"]:
            self.logger.warning(
                "Recruitment of %d %s failed because it is not researched"
                % (amount, unit_type)
            )
            self.attempt_research(unit_type)
            return False

        get_min = self.get_min_possible(resources)
        if get_min == 0:
            self.logger.info(
                "Recruitment of %d %s failed because of not enough resources"
                % (amount, unit_type)
            )
            self.reserve_resources(resources, amount, get_min, unit_type)
            return False
        
        needed_reserve = False
        if get_min < amount:
            if wait_for:
                self.logger.warning(
                    "Recruitment of %d %s failed because of not enough resources"
                    % (amount, unit_type)
                )
                self.reserve_resources(resources, amount, get_min, unit_type)
                needed_reserve = True
                return False
            if get_min > 0:
                self.logger.info(
                    "Recruitment of %d %s was set to %d because of resources"
                    % (amount, unit_type, get_min)
                )
                self.reserve_resources(resources, amount, get_min, unit_type)
                amount = get_min
                needed_reserve = True

        if not needed_reserve:
            # No need to reserve resources anymore!
            if f"recruitment_{unit_type}" in self.resman.requested:
                self.resman.requested.pop(f"recruitment_{unit_type}", None)

        result = self.wrapper.get_api_action(
            village_id=self.village_id,
            action="train",
            params={"screen": building, "mode": "train"},
            data={"units[%s]" % unit_type: str(amount)},
        )
        if "game_data" in result:
            self.resman.update(result["game_data"])
            self.wait_for[self.village_id][building] = int(time.time()) + (
                amount * int(resources["build_time"])
            )
            # self.troops[unit_type] = str((int(self.troops[unit_type]) if unit_type in self.troops else 0) + amount)
            self.logger.info(
                "Recruitment of %d %s started (%s idle till %d)"
                % (
                    amount,
                    unit_type,
                    building,
                    self.wait_for[self.village_id][building],
                )
            )
            self.wrapper.reporter.report(
                self.village_id,
                "TWB_RECRUIT",
                "Recruitment of %d %s started (%s idle till %d)"
                % (
                    amount,
                    unit_type,
                    building,
                    self.wait_for[self.village_id][building],
                ),
            )
            return True
        return False

    def reserve_resources(self, resources, wanted_times, has_times, unit_type):
        # Resources per unit, batch wanted, batch already recruiting
        self.logger.debug(f"Requesting resources to recruit {wanted_times - has_times} {unit_type}")
        for res in ["wood", "stone", "iron"]:
            req = resources[res] * (wanted_times - has_times)
            self.resman.request(source=f"recruitment_{unit_type}", resource=res, amount=req)



    def readable_ts(self, seconds):
        seconds -= time.time()
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60

        return "%d:%02d:%02d" % (hour, minutes, seconds)
