import math
import os
import json


# Tribalwars simulator class, based on real math stuff I guess
class Simulator:

    pool = {
        "spear": {
            "name": "spear",
            "building": "barracks",
            "required_level": 1,
            "wood": 50,
            "clay": 30,
            "iron": 20,
            "food": 1,
            "build_time": 840,
            "attack": 10,
            "def_inf": 15,
            "def_kav": 45,
            "def_arc": 20,
            "speed": 14,
            "load": 25,
            "type": 1,
            "points_att": 1,
            "points_def": 4,
        },
        "sword": {
            "name": "sword",
            "building": "barracks",
            "required_level": 3,
            "wood": 30,
            "clay": 30,
            "iron": 70,
            "food": 1,
            "build_time": 1200,
            "attack": 25,
            "def_inf": 50,
            "def_kav": 15,
            "def_arc": 40,
            "speed": 18,
            "load": 15,
            "type": 1,
            "points_att": 2,
            "points_def": 5,
        },
        "axe": {
            "name": "axe",
            "building": "barracks",
            "required_level": 5,
            "wood": 60,
            "clay": 30,
            "iron": 40,
            "food": 1,
            "build_time": 1320,
            "attack": 40,
            "def_inf": 10,
            "def_kav": 5,
            "def_arc": 10,
            "speed": 14,
            "load": 10,
            "type": 1,
            "points_att": 4,
            "points_def": 1,
        },
        "archer": {
            "name": "archer",
            "building": "barracks",
            "required_level": 9,
            "wood": 80,
            "clay": 30,
            "iron": 60,
            "food": 1,
            "build_time": 1500,
            "attack": 15,
            "def_inf": 50,
            "def_kav": 40,
            "def_arc": 5,
            "speed": 14,
            "load": 10,
            "type": 3,
            "points_att": 2,
            "points_def": 5,
        },
        "light": {
            "name": "light_cavalry",
            "building": "barracks",
            "required_level": 11,
            "wood": 125,
            "clay": 100,
            "iron": 250,
            "food": 4,
            "build_time": 1800,
            "attack": 130,
            "def_inf": 30,
            "def_kav": 40,
            "def_arc": 30,
            "speed": 8,
            "load": 80,
            "type": 2,
            "points_att": 13,
            "points_def": 5,
        },
        "marcher": {
            "name": "mounted_archer",
            "building": "barracks",
            "required_level": 13,
            "wood": 250,
            "clay": 100,
            "iron": 150,
            "food": 5,
            "build_time": 2200,
            "attack": 150,
            "def_inf": 40,
            "def_kav": 30,
            "def_arc": 50,
            "speed": 8,
            "load": 50,
            "type": 3,
            "points_att": 12,
            "points_def": 6,
        },
        "heavy": {
            "name": "heavy_cavalry",
            "building": "barracks",
            "required_level": 21,
            "wood": 200,
            "clay": 150,
            "iron": 600,
            "food": 6,
            "build_time": 3200,
            "attack": 150,
            "def_inf": 200,
            "def_kav": 80,
            "def_arc": 180,
            "speed": 9,
            "load": 50,
            "type": 2,
            "points_att": 15,
            "points_def": 23,
        },
        "ram": {
            "name": "ram",
            "building": "barracks",
            "required_level": 15,
            "wood": 300,
            "clay": 200,
            "iron": 200,
            "food": 5,
            "build_time": 4800,
            "attack": 2,
            "def_inf": 20,
            "def_kav": 50,
            "def_arc": 20,
            "speed": 24,
            "load": 0,
            "type": 1,
            "points_att": 8,
            "points_def": 4,
        },
        "catapult": {
            "name": "catapult",
            "building": "barracks",
            "required_level": 17,
            "wood": 320,
            "clay": 400,
            "iron": 100,
            "food": 8,
            "build_time": 7200,
            "attack": 100,
            "def_inf": 100,
            "def_kav": 50,
            "def_arc": 100,
            "speed": 24,
            "load": 0,
            "type": 1,
            "points_att": 10,
            "points_def": 12,
        },
        "knight": {
            "name": "knight",
            "building": "statue",
            "required_level": 1,
            "wood": 0,
            "clay": 0,
            "iron": 0,
            "food": 1,
            "build_time": 21600,
            "attack": 150,
            "def_inf": 250,
            "def_kav": 400,
            "def_arc": 150,
            "speed": 8,
            "load": 100,
            "type": 2,
            "points_att": 20,
            "points_def": 40,
        },
        "snob": {
            "name": "snob",
            "building": "academy",
            "required_level": 1,
            "wood": 40000,
            "clay": 50000,
            "iron": 50000,
            "food": 100,
            "build_time": 10800,
            "attack": 30,
            "def_inf": 100,
            "def_kav": 50,
            "def_arc": 100,
            "points_att": 200,
            "points_def": 200,
            "speed": 35,
            "load": 0,
            "type": 1,
            "special": 1,
        },
    }
    attack_pool = {
        "spear": "attack",
        "sword": "attack",
        "axe": "attack",
        "ram": "attack",
        "catapult": "attack",
        "snob": "attack",
        "light": "attack_cavalry",
        "heavy": "attack_cavalry",
        "knight": "attack_cavalry",
        "archer": "attack_archer",
        "marcher": "attack_archer",
    }

    attack_units = {
        "attack": ["spear", "sword", "axe", "ram", "catapult", "snob"],
        "attack_cavalry": ["light", "heavy", "knight"],
        "attack_archer": ["archer", "marcher"],
    }

    def attack_sum(self, units):
        total = {"attack": 0, "attack_cavalry": 0, "attack_archer": 0}
        for unit in units:
            total[self.attack_pool[unit]] += self.pool[unit]["attack"] * units[unit]
        return total

    def update_with_real_levels(self, levels):
        if not levels:
            return
        for unit in levels:
            if unit in self.pool:
                for item in levels[unit]:
                    self.pool[unit][item] = levels[unit][item]

    def attack_sum_food(self, units):
        total = {"attack": 0, "attack_cavalry": 0, "attack_archer": 0}
        for unit in units:
            total[self.attack_pool[unit]] += self.pool[unit]["food"] * units[unit]
        return total

    def defense_sum(self, units):
        total = {"defense": 0, "defense_cavalry": 0, "defense_archer": 0}
        for unit in units:
            total["defense"] += self.pool[unit]["def_inf"] * units[unit]
            total["defense_cavalry"] += self.pool[unit]["def_kav"] * units[unit]
            total["defense_archer"] += self.pool[unit]["def_arc"] * units[unit]
        return total

    def get_sum(self, obj):
        res = 0
        for k in obj:
            res += round(obj[k])
        return res

    def pre_wall(self, num_rams=None, wall=None):
        if not num_rams:
            num_rams = 0
        if not wall:
            wall = 0
        result = wall - round(num_rams / (4 * math.pow(1.09, wall)))
        return result if result >= 0 else 0

    def post_wall(
        self,
        attacker,
        defender,
        wall,
    ):
        rams = attacker["quantity"]["ram"]
        wall = wall if wall else 0

        if rams == 0 or wall == 0:
            return wall
        def_sum = self.get_sum(defender["quantity"])
        lose_def = 1
        if def_sum != 0:
            lose_def = self.get_sum(defender["losses"]) / def_sum
        if lose_def == 1:
            lose_att = self.get_sum(attacker["losses"]) / self.get_sum(
                attacker["quantity"]
            )
            dmg = (rams * self.pool["ram"]["attack"]) / (4 * math.pow(1.09, wall))
            resulting = wall - round(dmg - 0.5 * dmg * lose_att)
        else:
            resulting = wall - round(
                rams
                * self.pool["ram"]["attack"]
                * lose_def
                / (8 * math.pow(1.09, wall))
            )
        return max(0, resulting)

    def simulate(self, attackerUnits, defenderUnits, wall, nightbonus, moral, luck):
        wall = wall if wall else 0
        moral = moral if moral else 100
        moral /= 100
        luck = luck if luck else 0
        luck = 1 + luck / 100
        nightbonus = 2 if nightbonus else 1

        for item in self.pool:
            if item not in attackerUnits:
                attackerUnits[item] = 0
            if item not in defenderUnits:
                defenderUnits[item] = 0

        attacker = {
            "quantity": {},
            "losses": {},
        }
        defender = {
            "quantity": {},
            "losses": {},
        }

        for unit in self.pool:
            attacker["quantity"][unit] = (
                attackerUnits[unit] if unit in attackerUnits else 0
            )
            defender["quantity"][unit] = (
                defenderUnits[unit] if unit in defenderUnits else 0
            )

        resultingWall = self.pre_wall(wall=wall, num_rams=attackerUnits["ram"])
        wallBonus = 1 + resultingWall * 0.05
        wallDefense = 0
        if resultingWall != 0:
            wallDefense = round(math.pow(1.25, resultingWall) * 20)
        while self.get_sum(attackerUnits) >= 1 and self.get_sum(defenderUnits) >= 1:
            attack_strength = self.attack_sum(attackerUnits)
            def_strength = self.defense_sum(defenderUnits)
            attack_sum = self.get_sum(attackerUnits)

            attackFood = self.attack_sum_food(attackerUnits)
            attackFoodSum = self.get_sum(attackFood)
            print(attackFood, attackFoodSum)
            defenderUnitsCopy = dict()

            for unit in defenderUnits:
                defenderUnitsCopy[unit] = defenderUnits[unit]

            for attackType in attack_strength:
                if attack_strength[attackType] == 0:
                    continue

                ratio = attackFood[attackType] / attackFoodSum
                defense = (
                    def_strength[attackType.replace("attack", "defense")]
                    * ratio
                    * wallBonus
                    * nightbonus
                    + wallDefense * ratio
                )
                a = attack_strength[attackType] * moral * luck / defense
                if a < 1:
                    c = math.sqrt(a) * a
                    for unit in defenderUnits:
                        defenderUnits[unit] -= defenderUnitsCopy[unit] * c * ratio
                    for i in self.attack_units[attackType]:
                        unit = self.attack_units[attackType][i]
                        attackerUnits[unit] = 0
                else:
                    c = math.sqrt(1 / a) / a
                    for unit in defenderUnits:
                        defenderUnits[unit] -= ratio * defenderUnitsCopy[unit]
                    for i in self.attack_units[attackType]:
                        unit = i
                        attackerUnits[unit] -= c * attackerUnits[unit]

        for unit in self.pool:
            attacker["losses"][unit] = attacker["quantity"][unit] - round(
                (attackerUnits[unit])
            )
            defender["losses"][unit] = defender["quantity"][unit] - round(
                (defenderUnits[unit])
            )

        return {
            "attacker": attacker,
            "defender": defender,
            "wall_before": wall,
            "wall_during": resultingWall,
            "wall_after": self.post_wall(attacker, defender, wall),
        }


class SimCache:
    @staticmethod
    def get_cache(world):
        t_path = os.path.join("cache", "stats_%s.json" % world)
        if os.path.exists(t_path):
            with open(t_path, "r") as f:
                return json.load(f)
        return None

    @staticmethod
    def set_cache(world, entry):
        t_path = os.path.join("cache", "stats_%s.json" % world)
        with open(t_path, "w") as f:
            return json.dump(entry, f)

    @staticmethod
    def grab_cache(world, session, village_id):
        current = SimCache.get_cache(world)
        if current:
            return current
        result = session.get_action(village_id=village_id, action="unit_info&ajax=data")
        if result:
            SimCache.set_cache(world=world, entry=result.json())

    @staticmethod
    def cache_customize(entry):
        if not entry:
            return {}

        for unit in entry["response"]["unit_data"]:
            return
