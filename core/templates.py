"""
Manages template files
"""
from core.filemanager import FileManager


class TemplateManager:
    """Manages loading templates from the filesystem.

    This class provides a static method to read template files, which can be
    either plain text or JSON.
    """
    @staticmethod
    def get_template(category, template="basic", output_json=False):
        """Reads a specific template file.

        Args:
            category (str): The category of the template (e.g., 'builder', 'offensive').
            template (str, optional): The name of the template. Defaults to "basic".
            output_json (bool, optional): Whether to load the template as JSON.
                Defaults to False.

        Returns:
            list or dict: The content of the template file as a list of strings,
                or as a dictionary if output_json is True.
        """
        path = f"templates/{category}/{template}.txt"
        if output_json:
            return FileManager.load_json_file(path)
        lines = FileManager.read_file(path)
        if lines:
            return lines.strip().split()
        return []
