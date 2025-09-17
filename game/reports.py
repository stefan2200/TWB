"""
Report management
"""
import json
import logging
import re
from datetime import datetime

from core.extractors import Extractor
from core.filemanager import FileManager


class ReportManager:
    """Manages reading and parsing battle reports.

    This class can determine if a village is safe to attack based on previous
    reports, and it can also check if there are resources left in a farmed
    village.
    """
    wrapper = None
    village_id = None
    game_state = None
    logger = None
    last_reports = {}

    def __init__(self, wrapper=None, village_id=None):
        """Initializes the ReportManager.

        Args:
            wrapper (WebWrapper, optional): The web wrapper for making requests.
                Defaults to None.
            village_id (int, optional): The ID of the village. Defaults to None.
        """
        self.wrapper = wrapper
        self.village_id = village_id

    def has_resources_left(self, vid):
        """Checks if there are any resources left in a farmed village.

        Args:
            vid (int): The ID of the village to check.

        Returns:
            tuple: A tuple containing a boolean indicating if resources are left
                and a dictionary of the remaining resources.
        """
        possible_reports = []
        for repid in self.last_reports:
            entry = self.last_reports[repid]
            if vid == entry["dest"] and entry["extra"].get("when", None):
                possible_reports.append(entry)
        # self.logger.debug(f"Considered {len(possible_reports)} reports")
        if len(possible_reports) == 0:
            return False, {}

        def highest_when(attack):
            """
            Converts the date of an attack when resource gains were high
            """
            return datetime.fromtimestamp(int(attack["extra"]["when"]))

        entry = max(possible_reports, key=highest_when)
        self.logger.debug("This is the newest? %s", datetime.fromtimestamp(int(entry["extra"]["when"])))
        if entry["extra"].get("resources", None):
            return True, entry["extra"]["resources"]
        return False, {}

    def safe_to_engage(self, vid):
        """Calculates if a village is safe to engage without custom interaction.

        This method checks the latest reports for a given village to determine
        if it is safe to attack.

        Args:
            vid (int): The ID of the village to check.

        Returns:
            int: 1 if it is safe to engage, 0 if it is not, and -1 if there is
                no information.
        """
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
                            return 0  # Lost all units!
                        elif entry["losses"][sent_type] <= 1:
                            # Allow to lose 1 unit (luck depended)
                            return 1  # Lost 'just' one unit

                if entry["losses"] != {}:
                    return 0  # Disengage if anything was lost!
        return -1

    def read(self, page=0, full_run=False):
        """Reads and processes reports.

        Args:
            page (int, optional): The page number of reports to read. Defaults to 0.
            full_run (bool, optional): Whether to read all reports. Defaults to False.
        """
        if not self.logger:
            self.logger = logging.getLogger("Reports")

        if len(self.last_reports) == 0:
            self.logger.info("First run, re-reading cache entries")
            self.last_reports = ReportCache.cache_grab()
            self.logger.info("Got %d reports from cache", len(self.last_reports))
        offset = page * 12
        url = f"game.php?village={self.village_id}&screen=report&mode=all"
        if page > 0:
            url += f"&from={offset}"
        result = self.wrapper.get_url(url)
        self.game_state = Extractor.game_state(result)
        new = 0

        ids = Extractor.report_table(result)
        for report_id in ids:
            if report_id in self.last_reports:
                continue
            new += 1
            url = f"game.php?village={self.village_id}&screen=report&mode=all&group_id=0&view={report_id}"
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
                "%d new reports where added, also checking page %d", new, page
            )
            return self.read(page, full_run=full_run)

    def re_unit(self, inp):
        """Parses a line of units from a report.

        Args:
            inp (list): A list of tuples, where each tuple contains the unit
                name and quantity.

        Returns:
            dict: A dictionary of units and their quantities.
        """
        output = {}
        for row in inp:
            k, v = row
            if int(v) > 0:
                output[k] = int(v)
        return output

    def re_building(self, inp):
        """Parses building levels from a report.

        Args:
            inp (list): A list of dictionaries, where each dictionary contains
                the building ID and level.

        Returns:
            dict: A dictionary of building levels.
        """
        output = {}
        for row in inp:
            k = row["id"]
            v = row["level"]
            if int(v) > 0:
                output[k] = int(v)
        return output

    def attack_report(self, report, report_id):
        """Parses an attack report.

        Args:
            report (str): The HTML content of the report.
            report_id (int): The ID of the report.

        Returns:
            bool: True if the report was parsed successfully, False otherwise.
        """
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
            self.logger.info("attack report %s -> %s", from_village, to_village)

        scout_results = re.search(
            r'(?s)(<table id="attack_spy_resources".+?</table>)', report
        )
        if scout_results:
            self.logger.info("scout report %s -> %s", from_village, to_village)
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
        """Creates a report file in the cache.

        Args:
            report_id (int): The ID of the report.
            report_type (str): The type of the report (e.g., 'attack', 'scout').
            origin_village (int, optional): The ID of the origin village.
                Defaults to None.
            dest_village (int, optional): The ID of the destination village.
                Defaults to None.
            losses (dict, optional): A dictionary of lost units. Defaults to {}.
            data (dict, optional): A dictionary of extra data. Defaults to {}.

        Returns:
            dict: The report data that was saved to the cache.
        """
        output = {
            "type": report_type,
            "origin": origin_village,
            "dest": dest_village,
            "losses": losses,
            "extra": data,
        }
        ReportCache.set_cache(report_id, output)
        self.logger.info(
            "Processed %s report with id %s", report_type, str(report_id)
        )
        return output


class ReportCache:
    """Manages the cache for report data."""
    @staticmethod
    def get_cache(report_id):
        """Gets the cache entry for a specific report.

        Args:
            report_id (int): The ID of the report.

        Returns:
            dict or None: The cache entry as a dictionary, or None if not found.
        """
        return FileManager.load_json_file(f"cache/reports/{report_id}.json")

    @staticmethod
    def set_cache(report_id, entry):
        """Creates or updates a cache entry for a report.

        Args:
            report_id (int): The ID of the report.
            entry (dict): The cache entry to save.
        """
        FileManager.save_json_file(entry, f"cache/reports/{report_id}.json")

    @staticmethod
    def cache_grab():
        """Grabs all cache entries.

        Returns:
            dict: A dictionary of all cache entries, where the keys are report IDs.
        """
        output = {}

        for existing in FileManager.list_directory("cache/reports", ends_with=".json"):
            output[existing.replace(".json", "")] = FileManager.load_json_file(f"cache/reports/{existing}")
        return output
