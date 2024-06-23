import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from twb.core.exceptions import FileNotFoundException
from twb.core.exceptions import InvalidJSONException


class FileManager:
    """Provides methods for file and directory management."""

    @staticmethod
    def get_root() -> Path:
        """Returns the root directory of the project."""
        return Path.cwd()

    @staticmethod
    def get_path(path: Union[str, Path]) -> Path:
        """Returns the full path of a file or directory in the project."""
        return FileManager.get_root() / path

    @staticmethod
    def path_exists(path: Union[str, Path]) -> bool:
        """Returns True if the path exists, False otherwise."""
        return Path(path).exists()

    @staticmethod
    def create_directory(directory: Union[str, Path]) -> None:
        """Creates a directory if it does not exist."""
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def create_directories(directories: List[Union[str, Path]]) -> None:
        """Creates a list of directories in the root directory if they do not exist."""
        root_directory = FileManager.get_root()
        for directory in directories:
            FileManager.create_directory(root_directory / directory)

    @staticmethod
    def list_directory(
        directory: Union[str, Path], ends_with: Optional[str] = None
    ) -> List[str]:
        """Returns a list of files in a directory. If ends_with is specified, only files
        ending with the specified string will be returned."""
        full_path = FileManager.get_root() / directory
        files = [f.name for f in full_path.iterdir() if f.is_file()]
        if ends_with:
            files = [f for f in files if f.endswith(ends_with)]
        return files

    @staticmethod
    def __open_file(path: Union[str, Path], mode: str = "r"):
        """Opens a file in the specified mode. Private do NOT use outside filemanager."""
        full_path = FileManager.get_root() / path
        try:
            return full_path.open(mode, encoding="utf-8")
        except FileNotFoundError as err:
            raise FileNotFoundException from err

    @staticmethod
    def read_file(path: Union[str, Path]) -> Optional[str]:
        """Reads the contents of a file and returns the data. Returns None if the file does not exist."""
        full_path = FileManager.get_root() / path

        if not FileManager.path_exists(full_path):
            return None

        with FileManager.__open_file(full_path) as file:
            return file.read()

    @staticmethod
    def read_lines(path: Union[str, Path]) -> Optional[List[str]]:
        """Reads the contents of a file and returns the lines. Returns None if the file does not exist."""
        full_path = FileManager.get_root() / path

        if not FileManager.path_exists(full_path):
            return None

        with FileManager.__open_file(full_path) as file:
            return file.readlines()

    @staticmethod
    def remove_file(path: Union[str, Path]) -> None:
        """Removes a file if it exists."""
        full_path = FileManager.get_root() / path

        if FileManager.path_exists(full_path):
            full_path.unlink()

    @staticmethod
    def load_json_file(
        path: Union[Path, str], **kwargs
    ) -> Union[
        Dict[str, Union[str, Dict[str, str]]],
        Dict[
            str,
            Union[
                Dict[str, str],
                Dict[str, Union[str, bool]],
                Dict[str, Union[str, float, int, bool]],
                Dict[str, Union[bool, str, int]],
                Dict[str, Union[bool, int]],
                Dict[str, Union[bool, int, float]],
                Dict[str, bool],
                Dict[str, Dict[str, Union[str, float, int, bool]]],
            ],
        ],
        Dict[
            str,
            Union[
                Dict[str, str],
                Dict[str, Union[str, bool]],
                Dict[str, Optional[Union[str, float, int, bool]]],
                Dict[str, Union[bool, str, int]],
                Dict[str, Union[str, float, int, bool]],
                Dict[str, Union[bool, int]],
                Dict[str, Union[bool, int, float]],
                Dict[str, Optional[bool]],
            ],
        ],
        OrderedDict,
    ]:
        """Loads a JSON file and returns the data. Returns None if the file does not exist."""
        full_path = FileManager.get_root() / path

        if not FileManager.path_exists(full_path):
            return None

        with FileManager.__open_file(full_path) as file:
            try:
                return json.load(file, **kwargs)
            except json.decoder.JSONDecodeError as err:
                raise InvalidJSONException from err

    @staticmethod
    def save_json_file(
        data: Dict[str, Union[str, Dict[str, str]]], path: Union[str, Path], **kwargs
    ) -> None:
        """Saves data to a JSON file. If the file does not exist, it will be created."""
        full_path = FileManager.get_root() / path

        with FileManager.__open_file(full_path, mode="w") as file:
            json.dump(data, file, indent=2, sort_keys=False, **kwargs)

    @staticmethod
    def copy_file(src_path: Union[str, Path], dest_path: Union[str, Path]) -> bool:
        """Copies a file from the source path to the destination path."""
        full_src_path = FileManager.get_root() / src_path
        full_dest_path = FileManager.get_root() / dest_path

        if not FileManager.path_exists(full_src_path):
            return False

        full_dest_path.write_text(full_src_path.read_text(), encoding="utf-8")
        return True
