class VillageInitException(Exception):
    """
    Error when village init does not happen correctly
    """


class VillageNotExists(Exception):
    """
    A village is added to the bot that is not configured in the config file
    """


class InvalidGameStateException(Exception):
    """
    There was an error reading the game state of the village
    """


class InvalidUnitTemplateException(Exception):
    """
    There was an error reading the game state of the village
    """