

class DefenceManager:
    wrapper = None
    village_id = None

    under_attack = False
    attacks = []

    dodge_clear = True

    defensive_units = [
        "spear",
        "sword",
        "archer",
        "marcher",
        "spy"
    ]

    hide_units = [
        "snob",
        "axe"
    ]

    def __init__(self, village_id=None, wrapper=None):
        self.village_id = village_id
        self.wrapper = wrapper

    def update(self, main):
        if "command/attack.png" in main:
            self.under_attack = True



