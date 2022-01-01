import json
import os
from game.reports import ReportCache
from game.attack import AttackCache


class VillageManager:
    @staticmethod
    def farm_manager(verbose=False):
        with open("config.json", "r") as f:
            config = json.load(f)

        if verbose:
            print("[Farm Manager] Villages: %d" % len(config["villages"]))
        attacks = AttackCache.cache_grab()
        reports = ReportCache.cache_grab()

        if verbose:
            print("[Farm Manager] Reports: %d" % len(reports))
            print("[Farm Manager] Farms: %d" % len(attacks))
        t = {"wood": 0, "iron": 0, "stone": 0}
        for farm in attacks:
            data = attacks[farm]

            num_attack = []
            loot = {"wood": 0, "iron": 0, "stone": 0}
            total_loss_count = 0
            total_sent_count = 0
            for rep in reports:
                if reports[rep]["dest"] == farm and reports[rep]["type"] == "attack":
                    for unit in reports[rep]["extra"]["units_sent"]:
                        total_sent_count += reports[rep]["extra"]["units_sent"][unit]
                    for unit in reports[rep]["losses"]:
                        total_loss_count += reports[rep]["losses"][unit]
                    try:
                        res = reports[rep]["extra"]["loot"]
                        for r in res:
                            loot[r] = loot[r] + int(res[r])
                            t[r] = t[r] + int(res[r])
                        num_attack.append(reports[rep])
                    except:
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
                print(
                    "%sFarm village %s attacked %d times - Total loot: %s - Total units lost: %s (%s)"
                    % (perf, farm, len(num_attack), str(loot), str(total_loss_count), str(percentage_lost))
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
                            print(
                                "Farm %s has very low resources (%d avg total), extending farm time"
                                % (farm, total / len(num_attack))
                            )
                        data["low_profile"] = True
                        AttackCache.set_cache(farm, data)
                    elif total / len(num_attack) > 500 and (
                        "high_profile" not in data or not data["high_profile"]
                    ):
                        if verbose:
                            print(
                                "Farm %s has very high resources (%d avg total), setting to high profile"
                                % (farm, total / len(num_attack))
                            )
                        data["high_profile"] = True
                        AttackCache.set_cache(farm, data)

            if percentage_lost > 20 and not data["low_profile"]:
                print(f"[Farm Manager] Dangerous {percentage_lost} percentage lost units! Extending farm time")
                data["low_profile"] = True
                data["high_profile"] = False
                AttackCache.set_cache(farm, data)
            if percentage_lost > 50 and len(num_attack) > 10:
                print("[Farm Manager] Farm seems too dangerous/ unprofitable to farm. Setting safe to false!")
                data["safe"] = False
                AttackCache.set_cache(farm, data)

        for report in reports:
            r = reports[report]
            total_loss_count = 0
            if r["type"] == "scout" or r["type"] == "attack":
                if r["losses"] != {}:
                    for unit in r["losses"]:
                        total_loss_count += r["losses"][unit] * 2 if unit == "light" else r["losses"][unit]
                    if total_loss_count > 10 and verbose:
                        print(f"[Farm Manager] Dangerous: {r} -> {total_loss_count} total loss count, extending farm time")
                    if total_loss_count > 10:
                        data["low_profile"] = True
                        AttackCache.set_cache(farm, data)

        if verbose:
            print("[Farm Manager] Total loot: %s" % t)

        list_of_files = sorted([ "./cache/reports/"+f for f in os.listdir("./cache/reports/")], key=os.path.getctime)

        print(f"Found {len(list_of_files)} files")

        while len(list_of_files) > 350:
            oldest_file = list_of_files.pop(0)
            print(f"[Farm Manager] Delete old report ({oldest_file})")
            os.remove(os.path.abspath(oldest_file))


if __name__ == "__main__":
    VillageManager.farm_manager(verbose=True)
