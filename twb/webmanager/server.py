import json
import os
import sys

sys.path.insert(0, "../")

from flask import Flask
from flask import jsonify
from flask import render_template
from flask import request
from flask import send_from_directory

try:
    from webmanager.helpfile import buildings
    from webmanager.helpfile import help_file
    from webmanager.utils import BotManager
    from webmanager.utils import BuildingTemplateManager
    from webmanager.utils import DataReader
    from webmanager.utils import MapBuilder
except ImportError:
    from helpfile import buildings
    from helpfile import help_file
    from utils import BotManager
    from utils import BuildingTemplateManager
    from utils import DataReader
    from utils import MapBuilder

bm = BotManager()

app = Flask(__name__)
app.config["DEBUG"] = True


def pre_process_bool(key, value, village_id=None):
    if village_id:
        if value:
            return f'<button class="btn btn-sm btn-block btn-success" data-village-id="{village_id}" data-type-option="{key}" data-type="toggle">Enabled</button>'
        else:
            return f'<button class="btn btn-sm btn-block btn-danger" data-village-id="{village_id}" data-type-option="{key}" data-type="toggle">Disabled</button>'
    if value:
        return f'<button class="btn btn-sm btn-block btn-success" data-type-option="{key}" data-type="toggle">Enabled</button>'
    else:
        return f'<button class="btn btn-sm btn-block btn-danger" data-type-option="{key}" data-type="toggle">Disabled</button>'


def preprocess_select(key, value, templates, village_id=None):
    output = (
        f'<select data-type-option="{key}" data-type="select" class="form-control">'
    )
    if village_id:
        output = f'<select data-type-option="{key}" data-village-id="{village_id}" data-type="select" class="form-control">'

    for template in DataReader.template_grab(templates):
        output += '<option value="{}" {}>{}</option>'.format(
            template,
            "selected" if template == value else "",
            template,
        )
    output += "</select>"
    return output


def pre_process_string(key, value, village_id=None):
    templates = {
        "units.default": "templates.troops",
        "village.units": "templates.troops",
        "building.default": "templates.builder",
        "village_template.units": "templates.troops",
        "village.building": "templates.builder",
        "village_template.building": "templates.builder",
    }
    if key in templates:
        return preprocess_select(key, value, templates[key], village_id)
    if village_id:
        return f'<input type="text" class="form-control" data-village-id="{village_id}" data-type="text" value="{value}" data-type-option="{key}" />'
    else:
        return f'<input type="text" class="form-control" data-type="text" value="{value}" data-type-option="{key}" />'


def pre_process_number(key, value, village_id=None):
    if village_id:
        return f'<input type="number" data-type="number" class="form-control" data-village-id="{village_id}" value="{value}" data-type-option="{key}" />'
    return f'<input type="number" data-type="number" class="form-control" value="{value}" data-type-option="{key}" />'


def pre_process_list(key, value, village_id=None):
    if village_id:
        return '<input type="text" data-type="list" class="form-control" data-village-id="{}" value="{}" data-type-option="{}" />'.format(
            village_id, ", ".join(value), key
        )
    return '<input type="number" data-type="list" class="form-control" value="{}" data-type-option="{}" />'.format(
        ", ".join(value), key
    )


def fancy(key):
    name = key
    if "." in name:
        name = name.split(".")[1]
    name = name[0].upper() + name[1:]
    out = f"<hr /><strong>{name}</strong>"
    help_txt = None
    help_key = key
    help_key = help_key.replace("village_template", "village")
    if help_key in help_file:
        help_txt = help_file[help_key]
    if help_txt:
        out += f"<br /><i>{help_txt}</i>"
    return out


def pre_process_config():
    # TODO get generic config
    config = sync()["config"]
    to_hide = ["build", "villages"]
    sections = {}
    for section in config:
        if section in to_hide:
            continue
        config_data = ""
        for parameter in config[section]:
            value = config[section][parameter]
            kvp = f"{section}.{parameter}"
            if isinstance(value, bool):
                config_data += f"{fancy(kvp)} {pre_process_bool(kvp, value)}"
            if isinstance(value, str):
                config_data += f"{fancy(kvp)} {pre_process_string(kvp, value)}"
            if isinstance(value, list):
                config_data += f"{fancy(kvp)} {pre_process_list(kvp, value)}"
            if isinstance(value, int) or isinstance(value, float):
                config_data += f"{fancy(kvp)} {pre_process_number(kvp, value)}"
        sections[section] = config_data

    return sections


def pre_process_village_config(village_id):
    config = sync()["config"]["villages"]
    if village_id in config:
        config = config[village_id]
    else:
        config = config[config.keys()[0]]
    config_data = ""
    for parameter in config:
        value = config[parameter]
        kvp = f"village.{parameter}"
        if isinstance(value, bool):
            config_data += f"{fancy(kvp)} {pre_process_bool(kvp, value, village_id)}"
        if isinstance(value, str):
            config_data += f"{fancy(kvp)} {pre_process_string(kvp, value, village_id)}"
        if isinstance(value, list):
            config_data += f"{fancy(kvp)} {pre_process_list(kvp, value, village_id)}"
        if isinstance(value, int) or isinstance(value, float):
            config_data += f"{fancy(kvp)} {pre_process_number(kvp, value, village_id)}"
    return config_data


def sync():
    reports = DataReader.cache_grab("reports")
    villages = DataReader.cache_grab("villages")
    attacks = DataReader.cache_grab("attacks")
    config = DataReader.config_grab()
    managed = DataReader.cache_grab("managed")
    bot_status = bm.is_running()

    sort_reports = {
        key: value
        for key, value in sorted(reports.items(), key=lambda item: int(item[0]))
    }
    n_items = {k: sort_reports[k] for k in list(sort_reports)[:100]}

    out_struct = {
        "attacks": attacks,
        "villages": villages,
        "config": config,
        "reports": n_items,
        "bot": managed,
        "status": bot_status,
    }
    return out_struct


@app.route("/api/get", methods=["GET"])
def get_vars():
    return jsonify(sync())


@app.route("/bot/start")
def start_bot():
    bm.start()
    return jsonify(bm.is_running())


@app.route("/bot/stop")
def stop_bot():
    bm.stop()
    return jsonify(not bm.is_running())


@app.route("/config", methods=["GET"])
def get_config():
    return render_template(
        "config.html", data=sync(), config=pre_process_config(), helpfile=help_file
    )


@app.route("/village", methods=["GET"])
def get_village_config():
    data = sync()
    vid = request.args.get("id", None)
    return render_template(
        "village.html",
        data=data,
        config=pre_process_village_config(village_id=vid),
        current_select=vid,
        helpfile=help_file,
    )


@app.route("/map", methods=["GET"])
def get_map():
    sync_data = sync()
    center_id = request.args.get("center", None)
    center = next(iter(sync_data["bot"])) if not center_id else center_id
    map_data = json.dumps(
        MapBuilder.build(sync_data["villages"], current_village=center, size=15)
    )
    return render_template("map.html", data=sync_data, map=map_data)


@app.route("/villages", methods=["GET"])
def get_village_overview():
    return render_template("villages.html", data=sync())


@app.route("/building_templates", methods=["GET", "POST"])
def get_building_templates():
    if request.form.get("new", None):
        plain = os.path.basename(request.form.get("new"))
        if not plain.endswith(".txt"):
            plain = f"{plain}.txt"
        tempfile = f"../templates/builder/{plain}"
        if not os.path.exists(tempfile):
            with open(tempfile, "w") as ouf:
                ouf.write("")
    selected = request.args.get("t", None)
    return render_template(
        "templates.html",
        templates=BuildingTemplateManager.template_cache_list(),
        selected=selected,
        buildings=buildings,
    )


@app.route("/", methods=["GET"])
def get_home():
    session = DataReader.get_session()
    return render_template("bot.html", data=sync(), session=session)


@app.route("/app/js", methods=["GET"])
def get_js():
    urlpath = os.path.join(os.path.dirname(__file__), "public")
    return send_from_directory(urlpath, "js.v2.js")


@app.route("/app/config/set", methods=["GET"])
def config_set():
    vid = request.args.get("village_id", None)
    if not vid:
        DataReader.config_set(
            parameter=request.args.get("parameter"),
            value=request.args.get("value", None),
        )
    else:
        param = request.args.get("parameter")
        if param.startswith("village."):
            param = param.replace("village.", "")
        DataReader.village_config_set(
            village_id=vid, parameter=param, value=request.args.get("value", None)
        )

    return jsonify(sync())


if len(sys.argv) > 1:
    app.run(host="localhost", port=sys.argv[1])
else:
    app.run()
