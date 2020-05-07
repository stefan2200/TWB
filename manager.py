import json
from game.reports import ReportCache
from game.attack import AttackCache


with open('config.json', 'r') as f:
    config = json.load(f)

print("Villages: %d" % len(config['villages']))
attacks = AttackCache.cache_grab()
reports = ReportCache.cache_grab()

print("Reports: %d" % len(reports))
print("Farms: %d" % len(attacks))
t = {'wood': 0, 'iron': 0, 'stone': 0}
for farm in attacks:
    data = attacks[farm]

    num_attack = []
    loot = {'wood': 0, 'iron': 0, 'stone': 0}
    for rep in reports:
        if reports[rep]['dest'] == farm and reports[rep]['type'] == "attack":
            try:
                res = reports[rep]['extra']['loot']
                for r in res:
                    loot[r] = loot[r] + int(res[r])
                    t[r] = t[r] + int(res[r])
                num_attack.append(reports[rep])
            except:
                pass
    perf = ""
    if data['high_profile']:
        perf = "High Profile "
    if 'low_profile' in data and data['low_profile']:
        perf = "Low Profile "
    print("%sFarm village %s attacked %d times - Total loot: %s" % (perf, farm, len(num_attack), str(loot)))
    if len(num_attack):
        total = 0
        for k in loot:
            total += loot[k]
        if len(num_attack) > 3:
            if total / len(num_attack) < 50 and ('low_profile' not in data or not data['low_profile']):
                print("Farm %s has very low resources (%d avg total), extending farm time" % (farm, total / len(num_attack)))
                data['low_profile'] = True
                AttackCache.set_cache(farm, data)
            elif total / len(num_attack) > 500 and ('high_profile' not in data or not data['high_profile']):
                print(
                    "Farm %s has very high resources (%d avg total), setting to high profile" % (farm, total / len(num_attack)))
                data['high_profile'] = True
                AttackCache.set_cache(farm, data)

for report in reports:
    r = reports[report]
    if r['type'] == "scout" or r['type'] == "attack":
        if r['losses'] != {}:
            print("Dangerous: %s" % r)

print("Total loot: %s" % t)