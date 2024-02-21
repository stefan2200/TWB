import json
import os


class FileManager:
    @staticmethod
    def get_root():
        return os.path.join(os.path.dirname(__file__), "..")

    @staticmethod
    def create_directory(directory):
        if not os.path.exists(directory):
            os.makedirs(directory)

    @staticmethod
    def create_directories(root_directory, directories):
        for directory in directories:
            directory = os.path.join(root_directory, directory)
            FileManager.create_directory(directory)

    @staticmethod
    def path_exists(path):
        return os.path.exists(path)

    @staticmethod
    def open_file(path, mode="r"):
        full_path = os.path.join(FileManager.get_root(), path)

        if mode == "r" and not FileManager.path_exists(full_path):
            return None

        return open(full_path, mode)

    @staticmethod
    def load_json_file(path, **kwargs):
        full_path = os.path.join(FileManager.get_root(), path)

        if not FileManager.path_exists(full_path):
            return None

        with FileManager.open_file(full_path) as file:
            return json.load(file, **kwargs)

    @staticmethod
    def save_json_file(data, path, **kwargs):
        full_path = os.path.join(FileManager.get_root(), path)

        with FileManager.open_file(full_path, mode="w") as file:
            json.dump(data, file, indent=2, sort_keys=False, **kwargs)

    @staticmethod
    def copy_file(src_path, dest_path):
        full_src_path = os.path.join(FileManager.get_root(), src_path)
        full_dest_path = os.path.join(FileManager.get_root(), dest_path)

        with FileManager.open_file(full_src_path) as src_file:
            with FileManager.open_file(full_dest_path, mode="w") as dest_file:
                dest_file.write(src_file.read())
