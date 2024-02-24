import dataclasses
import re
from typing import Dict, Optional, Tuple

from bs4 import BeautifulSoup
from requests import Response

from core.request import WebWrapper


class Point:
    """Represents a point with x and y coordinates."""

    def __init__(self, x: int, y: int):
        if not isinstance(x, int):
            raise TypeError("x must be an integer")
        if not isinstance(y, int):
            raise TypeError("y must be an integer")
        self.x = x
        self.y = y

    def __repr__(self):
        return f"({self.x}|{self.y})"

    def __eq__(self, other: "Point") -> bool:
        """Check if two Point instances have the same coordinates."""
        if isinstance(other, Point):
            return self.x == other.x and self.y == other.y
        return False

    def distance_to(self, other: "Point") -> float:
        """Calculate the square of the distance between this point and another point."""
        return (self.x - other.x) ** 2 + (self.y - other.y) ** 2

    def __str__(self):
        return f"({self.x}|{self.y})"


class Farm:
    """Represents farm population."""

    def __init__(self, population: str):
        """
        Initializes a Farm object.

        Args:
            population (str): The string representation of population.
                Format: 'current/maximum'.

        Raises:
            ValueError: If the population string format is invalid.
        """
        if not re.match(r"\d+/\d+", population):
            raise ValueError("Invalid population string format")
        current, maximum = map(int, population.split("/"))
        self.current = current
        self.maximum = maximum

    def is_full(self) -> bool:
        """
        Check if the farm is full.

        Returns:
            bool: True if the farm is full, False otherwise.
        """
        return self.current == self.maximum

    def calculate_remaining_capacity(self) -> int:
        """
        Calculate the remaining capacity of the farm.

        Returns:
            int: The remaining capacity.
        """
        return self.maximum - self.current


class Storage:
    """Represents storage resources (wood, stone, iron)."""

    def __init__(self, resources: str, capacity: str):
        """
        Initializes a Storage object.

        Args:
            resources (str): The string representation of resources.
                Format: 'wood,stone,iron'.
            capacity (str): The string representation of capacity.
                Format: 'capacity'.

        Raises:
            ValueError: If the resources string format is invalid.
            ValueError: If the capacity string format is invalid.
        """
        resource_values = resources.replace(".", "").split(" ")
        if len(resource_values) != 3:
            print("Invalid resources string format")
        try:
            self.wood = int(resource_values[0])
            self.stone = int(resource_values[1])
            self.iron = int(resource_values[2])
        except ValueError:
            raise ValueError("Invalid resources string format")
        try:
            self.capacity = int(capacity)
        except ValueError:
            raise ValueError("Invalid capacity string format")


class Village:
    """Represents a village with its name, coordinates, and continent."""

    def __init__(
        self,
        village_id: str,
        village_name: str,
        coordinates: Point,
        continent: str,
        points: str,
        storage: Storage,
        farm: Farm,
    ):
        """
        Initializes a Village object.

        Args:
            village_id (str): The ID of the village.
            village_name (str): The name of the village.
            coordinates (Point): The coordinates of the village.
            continent (str): The continent of the village.
            points (str): The points of the village.
            storage (Storage): The storage of the village.
            farm (Farm): The farm of the village.

        Raises:
            ValueError: If the village string format is invalid.
        """
        self._village_id = village_id
        self._village_name = village_name
        self._coordinates = coordinates
        self._continent = continent
        self._points = int(points.replace(".", ""))
        self._storage = storage
        self._farm = farm

    def __str__(self) -> str:
        """Return a human-readable representation of the Village object."""
        return f"Village: {self._village_name}, Coordinates: {self._coordinates}, Continent: {self._continent}"

    def __repr__(self):
        return f"Village(village_id={self._village_id}, village_name={self._village_name}, coordinates={self._coordinates}, continent={self._continent}, points={self._points}, storage={self._storage}, farm={self._farm})"

    @staticmethod
    def parse_coordinates(cords: str) -> "Point":
        """
        Parse the coordinates string and return a Point object.

        Args:
            cords (str): The string representation of coordinates.

        Returns:
            Point: The Point object with parsed coordinates.
        """
        x, y = map(int, cords.strip("()").split("|"))
        return Point(x, y)

    @property
    def village_id(self) -> str:
        return self._village_id

    @property
    def village_name(self) -> str:
        return self._village_name

    @property
    def coordinates(self) -> Point:
        return self._coordinates

    @property
    def continent(self) -> str:
        return self._continent

    @property
    def points(self) -> int:
        return self._points

    @property
    def storage(self) -> Storage:
        return self._storage

    @property
    def farm(self) -> Farm:
        return self._farm


@dataclasses.dataclass
class WorldSettings:
    """Represents the world settings."""

    flags: bool = Optional[bool]
    knight: bool = Optional[bool]
    boosters: bool = Optional[bool]
    quests: bool = Optional[bool]


class OverviewPage:
    """Represents the overview page with village data and world options."""

    def __init__(self, wrapper):
        """
        Initializes an OverviewPage object.

        Args:
            wrapper: The wrapper object for making HTTP requests.
        """
        self.wrapper: WebWrapper = wrapper
        self.world_settings: WorldSettings = WorldSettings()
        self.result_get: Response = self._get_overview_villages_data()
        self.soup = BeautifulSoup(self.result_get.text, "html.parser")
        self.header_info = self.soup.find("table", id="header_info")
        self.production_table = self.soup.find("table", id="production_table")
        self.villages_data: Dict[str, Village] = {}
        self.parse_production_table()
        self.parse_header_info()

    def _get_overview_villages_data(self):
        """Get the overview villages data using the wrapper object."""
        return self.wrapper.get_url("game.php?screen=overview_villages")

    def parse_production_table(self):
        """Parse the production table to extract village data."""
        if self.production_table:
            rows = self.production_table.find_all("tr")
            for row in rows:
                if row.find_all("td"):
                    cells = row.find_all("td")
                    village_id = cells[0].contents[1].attrs["data-id"]
                    name, coordinates, continent = self._extract_name_cords_continent(
                        cells[0].text.strip()
                    )
                    points = cells[1].text.strip()
                    resources = cells[2].text.strip()
                    storage_capacity = cells[3].text.strip()

                    storage = Storage(resources, storage_capacity)
                    farm = Farm(cells[4].text.strip())
                    village = Village(
                        village_id, name, coordinates, continent, points, storage, farm
                    )
                    self.villages_data[village_id] = village

    def parse_header_info(self) -> None:
        """Parse header information to get world options."""
        text = self.result_get.text

        self.world_settings.flags = "screen=flags" in text
        self.world_settings.knight = "screen=statue" in text
        self.world_settings.boosters = "screen=inventory" in text
        self.world_settings.quests = "Quests.setQuestData" in text

    @staticmethod
    def _extract_name_cords_continent(cell_value: str) -> Tuple[str, Point, str]:
        """Extract name, coordinates and continent from cell value."""
        match = re.match(r"(.+)\s\((\d+)\|(\d+)\)\s(.+)", cell_value)
        if match:
            name = match.group(1)
            coordinates = Point(int(match.group(2)), int(match.group(3)))
            continent = match.group(4)
            return name, coordinates, continent
        else:
            print("Invalid village string format. Skipping village...")
