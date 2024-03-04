import json
import os


class FileManager:
    @staticmethod
    def get_root():
        """Returns the root directory of the project."""
        return os.path.join(os.path.dirname(__file__), "../../")

    @staticmethod
    def path_exists(path):
        """Returns True if the path exists, False otherwise."""
        full_path = os.path.join(FileManager.get_root(), path)
        return os.path.exists(full_path)

    @staticmethod
    def read_json_file(path):
        """Reads the contents of a JSON file and returns the data. Returns None if the file does not exist."""
        full_path = os.path.join(FileManager.get_root(), path)

        if not FileManager.path_exists(full_path):
            return None

        with open(full_path, "r") as file:
            return json.load(file)

    @staticmethod
    def write_json_file(path, data):
        """Writes the data to a JSON file."""
        full_path = os.path.join(FileManager.get_root(), path)

        with open(full_path, "w") as file:
            json.dump(data, file, indent=2, sort_keys=False)
