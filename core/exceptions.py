class VillageInitException(Exception):
    """Raised when village initialization fails."""


class VillageNotExists(Exception):
    """Raised when a village is not found in the configuration file."""


class InvalidGameStateException(Exception):
    """Raised when there is an error reading the game state of a village."""


class InvalidUnitTemplateException(Exception):
    """Raised when the selected unit template for a village is missing or corrupted."""


class InvalidJSONException(Exception):
    """Raised when a JSON file is corrupted and cannot be parsed."""


class FileNotFoundException(Exception):
    """Raised when a required file is not found."""


class UnsupportedPythonVersion(Exception):
    """Raised when the bot is run with an unsupported Python version."""
