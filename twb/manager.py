import copy
import json
import logging
import os
import sys
from collections import OrderedDict
from pathlib import Path
from typing import List

from twb.core.request import WebWrapper
from twb.game.attack import AttackCache
from twb.game.reports import ReportCache
from twb.game.village import Village


class VillageManager:
    def __init__(self, wrapper: WebWrapper, found_villages: List[str]) -> None:
        self.wrapper = wrapper
        self.found_villages = found_villages
        self.villages = []

    def add_found_villages(self, found_villages: List[str]) -> None:
        """_summary_

        Args:
            found_villages (_type_): _description_
        """
        self.found_villages = found_villages

    def initialize_villages(self, config: OrderedDict) -> None:
        for vid in config["villages"]:
            village = Village(wrapper=self.wrapper, village_id=vid)
            self.villages.append(copy.deepcopy(village))

    def process_villages(self, config: OrderedDict):
        village_number = 1
        rm = None
        defense_states = {}

        for village in self.villages:
            if village.village_id not in self.found_villages:
                logging.info(
                    "Village %s will be ignored because it is not available anymore",
                    village.village_id,
                )
                continue

            rm = rm or village.rep_man
            village.rep_man = rm or village.rep_man

            if config["bot"].get("auto_set_village_names", False):
                template = config["bot"]["village_name_template"]
                num_pad = (
                    f"{village_number:0{config['bot']['village_name_number_length']}d}"
                )
                village.village_set_name = template.replace("{num}", num_pad)

            village.run(config=config)

            if (
                village.get_config(
                    section="units", parameter="manage_defence", default=False
                )
                and village.def_man
            ):
                defense_states[village.village_id] = (
                    village.def_man.under_attack
                    if village.def_man.allow_support_recv
                    else False
                )

            village_number += 1

        if defense_states and config["farms"]["farm"]:
            logging.info("Syncing attack states")
            for village in self.villages:
                village.def_man.my_other_villages = defense_states

    @staticmethod
    def farm_manager(verbose=False, clean_reports=False):
        logger = logging.getLogger("FarmManager")
        with open(f"{Path.cwd()}/config.json", encoding="utf-8") as f:
            config = json.load(f)

        if verbose:
            logger.info("Villages: %d", len(config["villages"]))
        attacks = AttackCache.cache_grab()
        reports = ReportCache.cache_grab()

        if verbose:
            logger.info("Reports: %d", len(reports))
            logger.info("Farms: %d", len(attacks))
        t = {"wood": 0, "iron": 0, "stone": 0}
        for farm, attack in attacks.items():
            data = attack

            num_attack = []
            loot = {"wood": 0, "iron": 0, "stone": 0}
            total_loss_count = 0
            total_sent_count = 0
            for _id, report in reports.items():
                if report["dest"] == farm and report["type"] == "attack":
                    for unit in report["extra"]["units_sent"]:
                        total_sent_count += report["extra"]["units_sent"][unit]
                    for unit in report["extra"]["units_losses"]:
                        total_loss_count += report["extra"]["units_losses"][unit]
                    try:
                        res = report["extra"]["loot"]
                        for r in res:
                            loot[r] = loot[r] + int(res[r])
                            t[r] = t[r] + int(res[r])
                        num_attack.append(report)
                    except KeyError:
                        pass
            percentage_lost = 0

            if total_sent_count > 0:
                percentage_lost = total_loss_count / total_sent_count * 100

            perf = ""
            if data["high_profile"]:
                perf = "High Profile "
            if "low_profile" in data and data["low_profile"]:
                perf = "Low Profile "
            if verbose:
                logger.info(
                    "%sFarm village %s attacked %d times - Total loot: %s - Total units lost: %d (%.2f)",
                    perf,
                    farm,
                    len(num_attack),
                    str(loot),
                    total_loss_count,
                    percentage_lost,
                )
            if len(num_attack):
                total = 0
                for k in loot:
                    total += loot[k]
                if len(num_attack) > 3:
                    if total / len(num_attack) < 100 and (
                        "low_profile" not in data or not data["low_profile"]
                    ):
                        if verbose:
                            logger.info(
                                "Farm %s has very low resources (%d avg total), extending farm time",
                                farm,
                                total / len(num_attack),
                            )
                        data["low_profile"] = True
                        AttackCache.set_cache(farm, data)
                    elif total / len(num_attack) > 500 and (
                        "high_profile" not in data or not data["high_profile"]
                    ):
                        if verbose:
                            logger.info(
                                "Farm %s has very high resources (%d avg total), setting to high profile",
                                farm,
                                total / len(num_attack),
                            )
                        data["high_profile"] = True
                        AttackCache.set_cache(farm, data)

            if percentage_lost > 20 and not data["low_profile"]:
                logger.warning(
                    f"Dangerous {percentage_lost} percentage lost units! Extending farm time"
                )
                data["low_profile"] = True
                data["high_profile"] = False
                AttackCache.set_cache(farm, data)
            if percentage_lost > 50 and len(num_attack) > 10:
                logger.critical(
                    "Farm seems too dangerous/ unprofitable to farm. Setting safe to false!"
                )
                data["safe"] = False
                AttackCache.set_cache(farm, data)

        if verbose:
            logger.info(f"Total loot: {t}")

        if clean_reports:
            list_of_files = sorted(
                ["./cache/reports/" + f for f in os.listdir("./cache/reports/")],
                key=os.path.getctime,
            )

            logger.info(f"Found {len(list_of_files)} files")

            while len(list_of_files) > clean_reports:
                oldest_file = list_of_files.pop(0)
                logger.info(f"Delete old report ({oldest_file})")
                os.remove(os.path.abspath(oldest_file))


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout)
    VillageManager.farm_manager(verbose=True)
