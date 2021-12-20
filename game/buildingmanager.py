from core.extractors import Extractor
import time
import logging
import re


class BuildingManager:
    logger = None
    levels = {}

    max_lookahead = 2

    queue = []
    waits = []
    waits_building = []

    costs = {}

    wrapper = None
    village_id = None
    game_state = {}
    max_queue_len = 2
    resman = None
    raw_template = None

    def __init__(self, wrapper, village_id):
        self.wrapper = wrapper
        self.village_id = village_id

    def start_update(self, build=False, set_village_name=None):

        main_data = self.wrapper.get_action(village_id=self.village_id, action="main")
        if self.complete_actions(main_data.text):
            return self.start_update(build=build, set_village_name=set_village_name)
        self.costs = Extractor.building_data(main_data)
        self.game_state = Extractor.game_state(main_data)
        if self.resman:
            self.resman.update(self.game_state)
            if "building" in self.resman.requested:
                # new run, remove request
                self.resman.requested["building"] = {}
        vname = self.game_state["village"]["name"]
        if set_village_name and vname != set_village_name:
            self.wrapper.post_url(
                url="game.php?village=%s&screen=main&action=change_name"
                % self.village_id,
                data={"name": set_village_name, "h": self.wrapper.last_h},
            )

        if not self.logger:
            self.logger = logging.getLogger("Builder: %s" % vname)
        self.logger.debug("Updating building levels")
        tmp = self.game_state["village"]["buildings"]
        for e in tmp:
            tmp[e] = int(tmp[e])
        self.levels = tmp
        existing_queue = self.get_existing_items(main_data)
        if existing_queue == 0:
            self.waits = []
            self.waits_building = []
        if self.is_queued():
            self.logger.info(
                "No build operation was executed: queue full, %d left" % len(self.queue)
            )
            return False
        if not build:
            return False

        if existing_queue != 0 and existing_queue != len(self.waits):
            self.logger.warning(
                "Building queue out of sync, waiting until %d manual actions are finished!"
                % existing_queue
            )
            return True

        for x in range(self.max_queue_len - len(self.waits)):
            result = self.get_next_building_action()
            if not result:
                self.logger.info(
                    "No build more operations where executed (%d current, %d left)"
                    % (len(self.waits), len(self.queue))
                )
                return False
        return True

    def complete_actions(self, text):
        res = re.search(
            r'(?s)(\d+),\s*\'BuildInstantFree.+?data-available-from="(\d+)"', text
        )
        if res and int(res.group(2)) <= time.time():
            self.wrapper.get_url(
                "game.php?village=%s&screen=main&ajaxaction=build_order_reduce&h=%s&id=%s&destroy=0"
                % (self.village_id, self.wrapper.last_h, res.group(1))
            )
            self.logger.debug(
                "Quick build action %s was completed, re-running function"
                % res.group(1)
            )
            return True
        return False

    def put_wait(self, wait_time):
        self.is_queued()
        if len(self.waits) == 0:
            f_time = time.time() + wait_time
            self.waits.append(f_time)
            return f_time
        else:
            lastw = self.waits[-1]
            f_time = lastw + wait_time
            self.waits.append(f_time)
            self.logger.debug("Building finish time: %s" % str(f_time))
            return f_time

    def is_queued(self):
        if len(self.waits) == 0:
            return False
        for w in list(self.waits):
            if w < time.time():
                self.waits.pop(0)
        return len(self.waits) >= self.max_queue_len

    def get_existing_items(self, text):
        waits = Extractor.active_building_queue(text)
        return waits

    def has_enough(self, build_item):
        if (
            build_item["iron"] > self.resman.storage
            or build_item["wood"] > self.resman.storage
            or build_item["stone"] > self.resman.storage
        ):
            build_data = "storage:%d" % (int(self.levels["storage"]) + 1)
            if (
                len(self.queue)
                and "storage"
                not in [x.split(":")[0] for x in self.queue[0 : self.max_lookahead]]
                and int(self.levels["storage"]) != 30
            ):
                self.queue.insert(0, build_data)
                self.logger.info(
                    "Adding storage in front of queue because queue item exceeds storage capacity"
                )

        r = True
        if build_item["wood"] > self.game_state["village"]["wood"]:
            req = build_item["wood"] - self.game_state["village"]["wood"]
            self.resman.request(source="building", resource="wood", amount=req)
            r = False
        if build_item["stone"] > self.game_state["village"]["stone"]:
            req = build_item["stone"] - self.game_state["village"]["stone"]
            self.resman.request(source="building", resource="stone", amount=req)
            r = False
        if build_item["iron"] > self.game_state["village"]["iron"]:
            req = build_item["iron"] - self.game_state["village"]["iron"]
            self.resman.request(source="building", resource="iron", amount=req)
            r = False
        if build_item["pop"] > (
            self.game_state["village"]["pop_max"] - self.game_state["village"]["pop"]
        ):
            req = build_item["pop"] - (
                self.game_state["village"]["pop_max"]
                - self.game_state["village"]["pop"]
            )
            self.resman.request(source="building", resource="pop", amount=req)
            r = False
        return r

    def get_level(self, building):
        if building not in self.levels:
            return 0
        return self.levels[building]

    def readable_ts(self, seconds):
        seconds -= time.time()
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60

        return "%d:%02d:%02d" % (hour, minutes, seconds)

    def get_next_building_action(self, index=0):

        if index >= self.max_lookahead:
            self.logger.debug("Not building anything because insufficient resources")
            return False

        queue_check = self.is_queued()
        if queue_check:
            self.logger.debug("Not building because of queued items: %s" % self.waits)
            return False

        if self.resman and self.resman.in_need_of("pop"):
            build_data = "farm:%d" % (int(self.levels["farm"]) + 1)
            if (
                len(self.queue)
                and "farm"
                not in [x.split(":")[0] for x in self.queue[0 : self.max_lookahead]]
                and int(self.levels["farm"]) != 30
            ):
                self.queue.insert(0, build_data)
                self.logger.info("Adding farm in front of queue because low on pop")
                return self.get_next_building_action(0)

        if len(self.queue):
            entry = self.queue[index]
            entry, min_lvl = entry.split(":")
            min_lvl = int(min_lvl)
            if min_lvl <= self.levels[entry]:
                self.queue.pop(index)
                return self.get_next_building_action(index=index)
            if entry not in self.costs:
                self.logger.debug("Ignoring %s because not yet available" % entry)
                return self.get_next_building_action(index + 1)
            check = self.costs[entry]
            if "max_level" in check and min_lvl > check["max_level"]:
                self.logger.debug(
                    "Removing entry %s because max_level exceeded" % entry
                )
                self.queue.pop(index)
                return self.get_next_building_action(index=index)
            if check["can_build"] and self.has_enough(check) and "build_link" in check:
                queue = self.put_wait(check["build_time"])
                self.logger.info(
                    "Building %s %d -> %d (finishes: %s)"
                    % (
                        entry,
                        self.levels[entry],
                        self.levels[entry] + 1,
                        self.readable_ts(queue),
                    )
                )
                self.wrapper.reporter.report(
                    self.village_id,
                    "TWB_BUILD",
                    "Building %s %d -> %d (finishes: %s)"
                    % (
                        entry,
                        self.levels[entry],
                        self.levels[entry] + 1,
                        self.readable_ts(queue),
                    ),
                )
                self.levels[entry] += 1
                result = self.wrapper.get_url(check["build_link"].replace("amp;", ""))
                self.game_state = Extractor.game_state(result)
                self.costs = Extractor.building_data(result)
                return True
            else:
                return self.get_next_building_action(index + 1)
