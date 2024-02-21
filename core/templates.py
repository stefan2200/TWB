from core.filemanager import FileManager


class TemplateManager:
    @staticmethod
    def get_template(category, template="basic", output_json=False):
        path = f"templates/{category}/{template}.txt"
        if output_json:
            return FileManager.load_json_file(path)
        return FileManager.read_file(path).strip().split()
