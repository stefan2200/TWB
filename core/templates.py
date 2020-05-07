import os
import json


class TemplateManager:

    @staticmethod
    def get_template(category, template="basic", output_json=False):
        t_path = os.path.join("templates", category, template + ".txt")
        if os.path.exists(t_path):
            with open(t_path, 'r') as f:
                if output_json:
                    return json.load(f)
                return f.read().strip().split()
        t_path = os.path.join("../", "templates", category, template + ".txt")
        if os.path.exists(t_path):
            with open(t_path, 'r') as f:
                if output_json:
                    return json.load(f)
                return f.read().strip().split()
        return None
