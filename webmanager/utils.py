import collections
import json
import os
import subprocess
from json import JSONDecodeError

import psutil

from core.filemanager import FileManager


class DataReader:
    @staticmethod
    def cache_grab(cache_location):
        output = {}
        for existing in FileManager.list_directory(f"cache/{cache_location}", ends_with=".json"):
            t_path = f"cache/{cache_location}/{existing}"
            data = FileManager.load_json_file(t_path)
            if not data:
                print("Cache read error for %s. Removing broken entry" % t_path)
                FileManager.remove_file(t_path)

            output[existing.replace('.json', '')] = data

        return output

    @staticmethod
    def template_grab(template_location):
        output = []
        template_location = template_location.replace('.', '/')
        for existing in FileManager.list_directory(template_location, ends_with=".txt"):
            output.append(existing.split('.')[0])
        return output

    @staticmethod
    def config_grab():
        return FileManager.load_json_file("config.json")

    @staticmethod
    def config_set(parameter, value):
        try:
            value = json.loads(value)
        except JSONDecodeError as e:
            print(f"Value is not a valid JSON string, message: {e.msg}")

        template = FileManager.load_json_file("config.json", object_pairs_hook=collections.OrderedDict)

        if "." in parameter:
            section, param = parameter.split('.')
            template[section][param] = value
        else:
            template[parameter] = value

        FileManager.save_json_file(template, "config.json")
        print("Deployed new configuration file")
        return True

    @staticmethod
    def village_config_set(village_id, parameter, value):
        template = FileManager.load_json_file("config.json", object_pairs_hook=collections.OrderedDict)

        if village_id not in template['villages']:
            return False

        template['villages'][str(village_id)][parameter] = json.loads(value)

        FileManager.save_json_file(template, "config.json")
        print("Deployed new configuration file")
        return True

    @staticmethod
    def get_session():
        if not FileManager.path_exists("cache/session.json"):
            return {"raw": "", "endpoint": "None", "server": "None", "world": "None"}

        session_data = FileManager.load_json_file("cache/session.json")
        cookies = []

        for c in session_data['cookies']:
            cookies.append("%s=%s" % (c, session_data['cookies'][c]))

        session_data['raw'] = ';'.join(cookies)
        return session_data


class BuildingTemplateManager:
    @staticmethod
    def template_cache_list():
        output = {}
        for existing in FileManager.list_directory("templates/builder", ends_with=".txt"):
            lines = FileManager.read_lines(f"templates/builder/{existing}")
            if not lines:
                continue

            output[existing] = BuildingTemplateManager.template_to_dict(
                [x.strip() for x in lines]
            )
        return output

    @staticmethod
    def template_to_dict(t_list):
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

    @staticmethod
    def build(villages, current_village=None, size=None):
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
    pid = None

    def is_running(self):
        if not self.pid:
            return False
        if psutil.pid_exists(self.pid):
            return True
        self.pid = False
        return False

    def start(self):
        wd = FileManager.get_root()
        proc = subprocess.Popen("python twb.py", cwd=wd, shell=True)
        self.pid = proc.pid
        print("Bot started successfully")

    def stop(self):
        if self.is_running():
            os.kill(self.pid, sig=0)
            print("Bot stopped successfully")
