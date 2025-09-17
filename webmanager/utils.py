import collections
import json
import os
import subprocess

import psutil


class DataReader:
    """Provides methods for reading data from the cache and configuration files."""
    @staticmethod
    def cache_grab(cache_location):
        """Grabs all cache entries from a specific location.

        Args:
            cache_location (str): The name of the cache directory.

        Returns:
            dict: A dictionary of all cache entries.
        """
        output = {}
        c_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "cache",
            cache_location
        )
        for existing in os.listdir(c_path):
            existing = str(existing)
            if not existing.endswith(".json"):
                continue
            t_path = os.path.join(os.path.dirname(__file__), "..", "cache", cache_location, existing)
            with open(t_path, 'r') as f:
                try:
                    output[existing.replace('.json', '')] = json.load(f)
                except Exception as e:
                    print("Cache read error for %s: %s. Removing broken entry" % (t_path, str(e)))
                    f.close()
                    os.remove(t_path)

        return output

    @staticmethod
    def template_grab(template_location):
        """Grabs all template files from a specific location.

        Args:
            template_location (str): The path to the templates directory.

        Returns:
            list: A list of all template names.
        """
        output = []
        template_location = template_location.replace('.', '/')
        c_path = os.path.join(os.path.dirname(__file__), "..", template_location)
        for existing in os.listdir(c_path):
            existing = str(existing)
            if not existing.endswith(".txt"):
                continue
            output.append(existing.split('.')[0])
        return output

    @staticmethod
    def config_grab():
        """Grabs the main configuration file.

        Returns:
            dict: The configuration data.
        """
        with open(os.path.join(os.path.dirname(__file__), "..", "config.json"), 'r') as f:
            return json.load(f)

    @staticmethod
    def config_set(parameter, value):
        """Sets a configuration value in the main config file.

        Args:
            parameter (str): The configuration parameter to set.
            value (any): The value to set.

        Returns:
            bool: True if the configuration was set successfully, False otherwise.
        """
        try:
            value = json.loads(value)
        except:
            pass
        config_file_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        with open(config_file_path, 'r') as config_file:
            template = json.load(config_file, object_pairs_hook=collections.OrderedDict)
            if "." in parameter:
                section, param = parameter.split('.')
                template[section][param] = value
            else:
                template[parameter] = value
            with open(config_file_path, 'w') as newcf:
                json.dump(template, newcf, indent=2, sort_keys=False)
                print("Deployed new configuration file")
                return True

    @staticmethod
    def village_config_set(village_id, parameter, value):
        """Sets a configuration value for a specific village.

        Args:
            village_id (int): The ID of the village.
            parameter (str): The configuration parameter to set.
            value (any): The value to set.

        Returns:
            bool: True if the configuration was set successfully, False otherwise.
        """
        config_file_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        with open(config_file_path, 'r') as config_file:
            template = json.load(config_file, object_pairs_hook=collections.OrderedDict)
            if village_id not in template['villages']:
                return False
            try:
                template['villages'][str(village_id)][parameter] = json.loads(value)
            except json.decoder.JSONDecodeError:
                template['villages'][str(village_id)][parameter] = value
            with open(config_file_path, 'w') as newcf:
                json.dump(template, newcf, indent=2, sort_keys=False)
                print("Deployed new configuration file")
                return True

    @staticmethod
    def get_session():
        """Gets the current session data.

        Returns:
            dict: The session data.
        """
        c_path = os.path.join(os.path.dirname(__file__), "..", "cache", "session.json")
        if not os.path.exists(c_path):
            return {"raw": "", "endpoint": "None", "server": "None", "world": "None"}
        with open(c_path, 'r') as session_file:
            session_data = json.load(session_file)
            cookies = []
            for c in session_data['cookies']:
                cookies.append("%s=%s" % (c, session_data['cookies'][c]))
            session_data['raw'] = ';'.join(cookies)
            return session_data


class BuildingTemplateManager:
    """Manages building templates."""
    @staticmethod
    def template_cache_list():
        """Gets a list of all building templates.

        Returns:
            dict: A dictionary of all building templates.
        """
        c_path = os.path.join(os.path.dirname(__file__), "..", "templates", "builder")
        output = {}
        for existing in os.listdir(c_path):
            if not existing.endswith(".txt"):
                continue
            with open(os.path.join(os.path.dirname(__file__), "..", "templates", "builder", existing),
                      'r') as template_file:
                output[existing] = BuildingTemplateManager.template_to_dict(
                    [x.strip() for x in template_file.readlines()])
        return output

    @staticmethod
    def template_to_dict(t_list):
        """Converts a building template list to a dictionary.

        Args:
            t_list (list): A list of strings from a building template file.

        Returns:
            dict: A dictionary representation of the building template.
        """
        out_data = {}
        rows = []

        for entry in t_list:
            if entry.startswith('#') or ':' not in entry:
                continue
            building, next_level = entry.split(':')
            next_level = int(next_level)
            old = 0
            if building in out_data:
                old = out_data[building]
            rows.append({'building': building, 'from': old, 'to': next_level})
            out_data[building] = next_level

        return rows


class MapBuilder:
    """Builds the map data for display in the web interface."""
    @staticmethod
    def build(villages, current_village=None, size=None):
        """Builds the map data.

        Args:
            villages (dict): A dictionary of all villages.
            current_village (int, optional): The ID of the current village.
                Defaults to None.
            size (int, optional): The size of the map to build. Defaults to None.

        Returns:
            dict: A dictionary of the map data.
        """
        out_map = {}
        min_x = 999
        max_x = 0
        min_y = 999
        max_y = 0

        current_location = None
        grid_vils = {}
        extra_data = {}

        for v in villages:
            vdata = villages[v]
            x, y = vdata['location']
            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x

            if y < min_y:
                min_y = y
            if y > max_y:
                max_y = y
            if current_village and vdata['id'] == current_village:
                current_location = vdata['location']
                extra_data['owner'] = vdata['owner']
                extra_data['tribe'] = vdata['tribe']
            grid_vils["%d:%d" % (x, y)] = vdata

        if current_location and size:
            min_x = current_location[0] - size
            min_y = current_location[1] - size
            max_x = current_location[0] + size
            max_y = current_location[1] + size

        for location_x in range(min_x, max_x):
            if location_x not in out_map:
                out_map[location_x - min_x] = {}
            ylocs = {}
            for location_y in range(min_y, max_y):
                location = "%d:%d" % (location_x, location_y)
                if location in grid_vils:
                    ylocs[location_y - min_y] = grid_vils[location]
                else:
                    ylocs[location_y - min_y] = None
            out_map[location_x - min_x] = ylocs

        return {"grid": out_map, "extra": extra_data}


class BotManager:
    """Provides methods for starting and stopping the bot."""
    pid = None

    def is_running(self):
        """Checks if the bot is running.

        Returns:
            bool: True if the bot is running, False otherwise.
        """
        if not self.pid:
            return False
        if psutil.pid_exists(self.pid):
            return True
        self.pid = False
        return False

    def start(self):
        """Starts the bot."""
        wd = os.path.join(os.path.dirname(__file__), "..")
        proc = subprocess.Popen("python twb.py", cwd=wd, shell=True)
        self.pid = proc.pid
        print("Bot started successfully")

    def stop(self):
        """Stops the bot."""
        if self.is_running():
            os.kill(self.pid, sig=0)
            print("Bot stopped successfully")
