import json
import os

from core.exceptions import InvalidJSONException, FileNotFoundException


class FileManager:
    """Provides methods for file and directory management.

    This class contains static methods for performing common file operations
    such as creating, reading, and writing files, as well as managing
    directories. All paths are relative to the project's root directory.
    """

    @staticmethod
    def get_root():
        """Gets the root directory of the project.

        Returns:
            str: The absolute path to the project's root directory.
        """
        return os.path.join(os.path.dirname(__file__), "..")

    @staticmethod
    def get_path(path):
        """Constructs the full path for a file or directory in the project.

        Args:
            path (str): The relative path from the project root.

        Returns:
            str: The absolute path of the file or directory.
        """
        return os.path.join(FileManager.get_root(), path)

    @staticmethod
    def path_exists(path):
        """Checks if a path exists.

        Args:
            path (str): The path to check.

        Returns:
            bool: True if the path exists, False otherwise.
        """
        return os.path.exists(path)

    @staticmethod
    def create_directory(directory):
        """Creates a directory if it does not already exist.

        Args:
            directory (str): The path of the directory to create.
        """
        if not os.path.exists(directory):
            os.makedirs(directory)

    @staticmethod
    def create_directories(directories):
        """Creates a list of directories in the project's root directory.

        Args:
            directories (list): A list of directory paths to create.
        """
        root_directory = FileManager.get_root()
        for directory in directories:
            directory = os.path.join(root_directory, directory)
            FileManager.create_directory(directory)

    @staticmethod
    def list_directory(directory, ends_with=None):
        """Lists the files in a directory.

        Args:
            directory (str): The directory to list.
            ends_with (str, optional): If specified, only files ending with
                this string will be returned. Defaults to None.

        Returns:
            list: A list of filenames in the directory.
        """
        full_path = os.path.join(FileManager.get_root(), directory)
        files = os.listdir(full_path)
        if ends_with:
            files = [f for f in files if f.endswith(ends_with)]
        return files

    @staticmethod
    def __open_file(path, mode="r"):
        """Opens a file in the specified mode.

        Note:
            This is a private method and should not be used outside of this class.

        Args:
            path (str): The path to the file.
            mode (str, optional): The mode to open the file in. Defaults to 'r'.

        Returns:
            _io.TextIOWrapper: The file object.

        Raises:
            FileNotFoundException: If the file does not exist.
        """
        full_path = os.path.join(FileManager.get_root(), path)
        try:
            return open(full_path, mode)
        except:
            raise FileNotFoundException

    @staticmethod
    def read_file(path):
        """Reads the entire contents of a file.

        Args:
            path (str): The path to the file.

        Returns:
            str: The contents of the file, or None if the file does not exist.
        """
        full_path = os.path.join(FileManager.get_root(), path)

        if not FileManager.path_exists(full_path):
            return None

        with FileManager.__open_file(full_path) as file:
            return file.read()

    @staticmethod
    def read_lines(path):
        """Reads the lines of a file.

        Args:
            path (str): The path to the file.

        Returns:
            list: A list of lines from the file, or None if the file does not exist.
        """
        full_path = os.path.join(FileManager.get_root(), path)

        if not FileManager.path_exists(full_path):
            return None

        with FileManager.__open_file(full_path) as file:
            return file.readlines()

    @staticmethod
    def remove_file(path):
        """Removes a file if it exists.

        Args:
            path (str): The path to the file to remove.
        """
        full_path = os.path.join(FileManager.get_root(), path)

        if FileManager.path_exists(full_path):
            os.remove(full_path)

    @staticmethod
    def load_json_file(path, **kwargs):
        """Loads a JSON file.

        Args:
            path (str): The path to the JSON file.
            **kwargs: Additional arguments to pass to json.load().

        Returns:
            dict: The loaded JSON data, or None if the file does not exist.

        Raises:
            InvalidJSONException: If the JSON file is corrupted.
        """
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
        """Saves data to a JSON file.

        Args:
            data (dict): The data to save.
            path (str): The path to the JSON file.
            **kwargs: Additional arguments to pass to json.dump().
        """
        full_path = os.path.join(FileManager.get_root(), path)

        with FileManager.__open_file(full_path, mode="w") as file:
            json.dump(data, file, indent=2, sort_keys=False, **kwargs)

    @staticmethod
    def copy_file(src_path, dest_path):
        """Copies a file.

        Args:
            src_path (str): The path to the source file.
            dest_path (str): The path to the destination file.

        Returns:
            bool: True if the file was copied successfully, False otherwise.
        """
        full_src_path = os.path.join(FileManager.get_root(), src_path)
        full_dest_path = os.path.join(FileManager.get_root(), dest_path)

        if not FileManager.path_exists(full_src_path):
            return False

        with FileManager.__open_file(full_src_path) as src_file:
            with FileManager.__open_file(full_dest_path, mode="w") as dest_file:
                dest_file.write(src_file.read())
