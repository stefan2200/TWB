import os
import json
import re
import logging

from core.extractors import Extractor
from datetime import datetime


class ReportManager:
    wrapper = None
    village_id = None
    game_state = None
    logger = None
    last_reports = {}

    def __init__(self, wrapper=None, village_id=None):
        self.wrapper = wrapper
        self.village_id = village_id

    def has_resources_left(self, vid):
        possible_reports = []
        for repid in self.last_reports:
            entry = self.last_reports[repid]
            if vid == entry["dest"] and entry["extra"].get("when", None):
                possible_reports.append(entry)
        #self.logger.debug(f"Considered {len(possible_reports)} reports")
        if len(possible_reports) == 0:
            return False, {}

        def highest_when(attack):
            return datetime.fromtimestamp(int(attack["extra"]["when"]))

        #self.logger.debug(f"Reports: {possible_reports}")
        entry = max(possible_reports, key=highest_when)
        self.logger.debug(f'This is the newest? {datetime.fromtimestamp(int(entry["extra"]["when"]))}')
        #self.logger.debug(f'{entry["extra"]["when"]} seems to be the last attack.')
        # last_loot = entry["extra"]["loot"] if "loot" in entry["extra"] else None
        if entry["extra"].get("resources", None):
            return True, entry["extra"]["resources"]
        return False, {}

    def safe_to_engage(self, vid):
        for repid in self.last_reports:
            entry = self.last_reports[repid]
            if vid == entry["dest"]:
                if entry["type"] == "attack" and entry["losses"] == {}:
                    return 1
                if (
                    entry["type"] == "scout"
                    and entry["losses"] == {}
                    and (
                        entry["extra"]["defence_units"] == {}
                        or entry["extra"]["defence_units"]
                        == entry["extra"]["defence_losses"]
                    )
                ):
                    return 1
                
                if entry["losses"] != {}:
                    # Acceptable losses for attacks
                    print(f'Units sent: {entry["extra"]["units_sent"]}')
                    print(f'Units lost: {entry["losses"]}')

                for sent_type in entry["extra"]["units_sent"]:
                    amount = entry["extra"]["units_sent"][sent_type]
                    if sent_type in entry["losses"]:
                        if amount == entry["losses"][sent_type]:
                            return 0 # Lost all units!
                        elif entry["losses"][sent_type] <= 1:
                            # Allow to lose 1 unit (luck depended)
                            return 1 # Lost 'just' one unit

                if entry["losses"] != {}:
                    return 0 # Disengage if anything was lost!
        return -1

    def read(self, page=0, full_run=False):
        if not self.logger:
            self.logger = logging.getLogger("Reports")

        if len(self.last_reports) == 0:
            self.logger.info("First run, re-reading cache entries")
            self.last_reports = ReportCache.cache_grab()
            self.logger.info("Got %d reports from cache" % len(self.last_reports))
        offset = page * 12
        url = "game.php?village=%s&screen=report&mode=all" % (
            self.village_id
        )
        if page > 0:
            url += "&from=%d" % offset
        result = self.wrapper.get_url(url)
        self.game_state = Extractor.game_state(result)
        new = 0

        ids = Extractor.report_table(result)
        for report_id in ids:
            if report_id in self.last_reports:
                continue
            new += 1
            url = "game.php?village=%s&screen=report&mode=all&group_id=0&view=%s" % (
                self.village_id,
                report_id,
            )
            data = self.wrapper.get_url(url)

            get_type = re.search(r'class="report_(\w+)', data.text)
            if get_type:
                report_type = get_type.group(1)
                if report_type == "ReportAttack":
                    self.attack_report(data.text, report_id)
                    continue

                else:
                    res = self.put(report_id, report_type=report_type)
                    self.last_reports[report_id] = res
        if new == 12 or full_run and page < 20:
            page += 1
            self.logger.debug(
                "%d new reports where added, also checking page %d" % (new, page)
            )
            return self.read(page, full_run=full_run)

    def re_unit(self, inp):
        output = {}
        for row in inp:
            k, v = row
            if int(v) > 0:
                output[k] = int(v)
        return output

    def re_building(self, inp):
        output = {}
        for row in inp:
            k = row["id"]
            v = row["level"]
            if int(v) > 0:
                output[k] = int(v)
        return output

    def attack_report(self, report, report_id):
        from_village = None
        from_player = None

        to_village = None
        to_player = None

        extra = {}

        losses = {}

        attacked = re.search(r'(\d{2}\.\d{2}\.\d{2} \d{2}\:\d{2}\:\d{2})<span class=\"small grey\">', report)
        if attacked:
            extra["when"] = int(datetime.strptime(attacked.group(1), "%d.%m.%y %H:%M:%S").timestamp())

        attacker = re.search(r'(?s)(<table id="attack_info_att".+?</table>)', report)
        if attacker:
            attacker_data = re.search(
                r'data-player="(\d+)" data-id="(\d+)"', attacker.group(1)
            )
            if attacker_data:
                from_player = attacker_data.group(1)
                from_village = attacker_data.group(2)
                units = re.search(
                    r'(?s)<table id="attack_info_att_units"(.+?)</table>',
                    attacker.group(1),
                )
                if units:
                    sent_units = re.findall("(?s)<tr>(.+?)</tr>", units.group(1))
                    extra["units_sent"] = self.re_unit(
                        Extractor.units_in_total(sent_units[0])
                    )
                    if len(sent_units) == 2:
                        extra["units_losses"] = self.re_unit(
                            Extractor.units_in_total(sent_units[1])
                        )
                        if from_player == self.game_state["player"]["id"]:
                            losses = extra["units_losses"]

        defender = re.search(r'(?s)(<table id="attack_info_def".+?</table>)', report)
        if defender:
            defender_data = re.search(
                r'data-player="(\d+)" data-id="(\d+)"', defender.group(1)
            )
            if defender_data:
                to_player = defender_data.group(1)
                to_village = defender_data.group(2)
                units = re.search(
                    r'(?s)<table id="attack_info_def_units"(.+?)</table>',
                    defender.group(1),
                )
                if units:
                    def_units = re.findall("(?s)<tr>(.+?)</tr>", units.group(1))
                    extra["defence_units"] = self.re_unit(
                        Extractor.units_in_total(def_units[0])
                    )
                    if len(def_units) == 2:
                        extra["defence_losses"] = self.re_unit(
                            Extractor.units_in_total(def_units[1])
                        )
                        if to_player == self.game_state["player"]["id"]:
                            losses = extra["defence_losses"]
        results = re.search(r'(?s)(<table id="attack_results".+?</table>)', report)
        report = report.replace('<span class="grey">.</span>', "")
        if results:
            loot = {}
            for loot_entry in re.findall(
                r'<span class="icon header (wood|stone|iron)".+?</span>(\d+)', report
            ):
                loot[loot_entry[0]] = loot_entry[1]
            extra["loot"] = loot
            self.logger.info("attack report %s -> %s" % (from_village, to_village))

        scout_results = re.search(
            r'(?s)(<table id="attack_spy_resources".+?</table>)', report
        )
        if scout_results:
            self.logger.info("scout report %s -> %s" % (from_village, to_village))
            scout_buildings = re.search(
                r'(?s)<input id="attack_spy_building_data" type="hidden" value="(.+?)"',
                report,
            )
            if scout_buildings:
                raw = scout_buildings.group(1).replace("&quot;", '"')
                extra["buildings"] = self.re_building(json.loads(raw))
            found_res = {}
            for loot_entry in re.findall(
                r'<span class="icon header (wood|stone|iron)".+?</span>(\d+)', scout_results.group(1)
            ):
                found_res[loot_entry[0]] = loot_entry[1]
            extra["resources"] = found_res
            units_away = re.search(
                r'(?s)(<table id="attack_spy_away".+?</table>)', report
            )
            if units_away:
                data_away = self.re_unit(Extractor.units_in_total(units_away.group(1)))
                extra["units_away"] = data_away

        attack_type = "scout" if scout_results and not results else "attack"
        res = self.put(
            report_id, attack_type, from_village, to_village, data=extra, losses=losses
        )
        self.last_reports[report_id] = res
        return True

    def put(
        self,
        report_id,
        report_type,
        origin_village=None,
        dest_village=None,
        losses={},
        data={},
    ):
        output = {
            "type": report_type,
            "origin": origin_village,
            "dest": dest_village,
            "losses": losses,
            "extra": data,
        }
        ReportCache.set_cache(report_id, output)
        self.logger.info(
            "Processed %s report with id %s" % (report_type, str(report_id))
        )
        return output


class ReportCache:
    @staticmethod
    def get_cache(report_id):
        t_path = os.path.join(os.path.dirname(__file__), "..", "cache", "reports", report_id + ".json")
        if os.path.exists(t_path):
            with open(t_path, "r") as f:
                return json.load(f)
        return None

    @staticmethod
    def set_cache(report_id, entry):
        t_path = os.path.join(os.path.dirname(__file__), "..", "cache", "reports", report_id + ".json")
        with open(t_path, "w") as f:
            return json.dump(entry, f)

    @staticmethod
    def cache_grab():
        output = {}
        c_path = os.path.join(os.path.dirname(__file__), "..", "cache", "reports")
        for existing in os.listdir(c_path):
            if not existing.endswith(".json"):
                continue
            t_path = os.path.join(os.path.dirname(__file__), "..", "cache", "reports", existing)
            with open(t_path, "r") as f:
                output[existing.replace(".json", "")] = json.load(f)
        return output
