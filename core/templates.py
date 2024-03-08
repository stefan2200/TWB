"""
Manages template files
"""
from core.filemanager import FileManager


class TemplateManager:
    """
    Template manager file
    """
    @staticmethod
    def get_template(category, template="basic", output_json=False):
        """
        Reads a specific text file with arguments
        TODO: switch to improved FileManager
        """
        path = f"templates/{category}/{template}.txt"
        if output_json:
            return FileManager.load_json_file(path)
        return FileManager.read_file(path).strip().split()
