import json
import os

from core.exceptions import InvalidJSONException, FileNotFoundException


class FileManager:
    """Provides methods for file and directory management."""

    @staticmethod
    def get_root():
        """Returns the root directory of the project."""
        return os.path.join(os.path.dirname(__file__), "..")

    @staticmethod
    def get_path(path):
        """Returns the full path of a file or directory in the project."""
        return os.path.join(FileManager.get_root(), path)

    @staticmethod
    def path_exists(path):
        """Returns True if the path exists, False otherwise."""
        return os.path.exists(path)

    @staticmethod
    def create_directory(directory):
        """Creates a directory if it does not exist."""
        if not os.path.exists(directory):
            os.makedirs(directory)

    @staticmethod
    def create_directories(directories):
        """Creates a list of directories in the root directory if they do not exist."""
        root_directory = FileManager.get_root()
        for directory in directories:
            directory = os.path.join(root_directory, directory)
            FileManager.create_directory(directory)

    @staticmethod
    def list_directory(directory, ends_with=None):
        """Returns a list of files in a directory. If ends_with is specified, only files ending with the specified
        string will be returned."""
        full_path = os.path.join(FileManager.get_root(), directory)
        files = os.listdir(full_path)
        if ends_with:
            files = [f for f in files if f.endswith(ends_with)]
        return files

    @staticmethod
    def __open_file(path, mode="r"):
        """Opens a file in the specified mode. Private do NOT use outside filemanager."""
        full_path = os.path.join(FileManager.get_root(), path)
        try:
            return open(full_path, mode)
        except:
            raise FileNotFoundException

    @staticmethod
    def read_file(path):
        """Reads the contents of a file and returns the data. Returns None if the file does not exist."""
        full_path = os.path.join(FileManager.get_root(), path)

        if not FileManager.path_exists(full_path):
            return None

        with FileManager.__open_file(full_path) as file:
            return file.read()

    @staticmethod
    def read_lines(path):
        """Reads the contents of a file and returns the lines. Returns None if the file does not exist."""
        full_path = os.path.join(FileManager.get_root(), path)

        if not FileManager.path_exists(full_path):
            return None

        with FileManager.__open_file(full_path) as file:
            return file.readlines()

    @staticmethod
    def remove_file(path):
        """Removes a file if it exists."""
        full_path = os.path.join(FileManager.get_root(), path)

        if FileManager.path_exists(full_path):
            os.remove(full_path)

    @staticmethod
    def load_json_file(path, **kwargs):
        """Loads a JSON file and returns the data. Returns None if the file does not exist."""
        full_path = os.path.join(FileManager.get_root(), path)

        if not FileManager.path_exists(full_path):
            return None

        with FileManager.__open_file(full_path) as file:
            try:
                return json.load(file, **kwargs)
            except json.decoder.JSONDecodeError:
                raise InvalidJSONException

    @staticmethod
    def save_json_file(data, path, **kwargs):
        """Saves data to a JSON file. If the file does not exist, it will be created."""
        full_path = os.path.join(FileManager.get_root(), path)

        with FileManager.__open_file(full_path, mode="w") as file:
            json.dump(data, file, indent=2, sort_keys=False, **kwargs)

    @staticmethod
    def copy_file(src_path, dest_path):
        """Copies a file from the source path to the destination path."""
        full_src_path = os.path.join(FileManager.get_root(), src_path)
        full_dest_path = os.path.join(FileManager.get_root(), dest_path)

        if not FileManager.path_exists(full_src_path):
            return False

        with FileManager.__open_file(full_src_path) as src_file:
            with FileManager.__open_file(full_dest_path, mode="w") as dest_file:
                dest_file.write(src_file.read())
