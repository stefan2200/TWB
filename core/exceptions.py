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
    The selected unit template for the village is either missing or corrupted
    """


class InvalidJSONException(Exception):
    """
    The JSON file I'm trying to read is corrupted and cannot be parsed
    """


class FileNotFoundException(Exception):
    """
    The file I'm trying to read does not exist and is expected to be there
    """


class UnsupportedPythonVersion(Exception):
    """
    You are trying run the bot with an outdated python version
    Updating to Python3 fixes this issue
    """
