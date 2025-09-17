import json
import os
import sys
sys.path.insert(0, "../")

from flask import Flask, jsonify, send_from_directory, request, render_template

try:
    from webmanager.helpfile import help_file, buildings
    from webmanager.utils import DataReader, BotManager, MapBuilder, BuildingTemplateManager
except ImportError:
    from helpfile import help_file, buildings
    from utils import DataReader, BotManager, MapBuilder, BuildingTemplateManager

bm = BotManager()

app = Flask(__name__)
app.config["DEBUG"] = True


def pre_process_bool(key, value, village_id=None):
    """Pre-processes a boolean value for display in the web interface.

    Args:
        key (str): The configuration key.
        value (bool): The boolean value.
        village_id (int, optional): The ID of the village. Defaults to None.

    Returns:
        str: The HTML for a toggle button.
    """
    if village_id:
        if value:
            return '<button class="btn btn-sm btn-block btn-success" data-village-id="%s" data-type-option="%s" data-type="toggle">Enabled</button>' % (
            village_id, key)
        else:
            return '<button class="btn btn-sm btn-block btn-danger" data-village-id="%s" data-type-option="%s" data-type="toggle">Disabled</button>' % (
            village_id, key)
    if value:
        return '<button class="btn btn-sm btn-block btn-success" data-type-option="%s" data-type="toggle">Enabled</button>' % key
    else:
        return '<button class="btn btn-sm btn-block btn-danger" data-type-option="%s" data-type="toggle">Disabled</button>' % key


def preprocess_select(key, value, templates, village_id=None):
    """Pre-processes a select input for display in the web interface.

    Args:
        key (str): The configuration key.
        value (str): The current value.
        templates (str): The path to the templates directory.
        village_id (int, optional): The ID of the village. Defaults to None.

    Returns:
        str: The HTML for a select input.
    """
    output = '<select data-type-option="%s" data-type="select" class="form-control">' % key
    if village_id:
        output = '<select data-type-option="%s" data-village-id="%s" data-type="select" class="form-control">' % (
        key, village_id)

    for template in DataReader.template_grab(templates):
        output += '<option value="%s" %s>%s</option>' % (template, 'selected' if template == value else '', template)
    output += '</select>'
    return output


def pre_process_string(key, value, village_id=None):
    """Pre-processes a string value for display in the web interface.

    Args:
        key (str): The configuration key.
        value (str): The string value.
        village_id (int, optional): The ID of the village. Defaults to None.

    Returns:
        str: The HTML for a text input or a select input.
    """
    templates = {
        'units.default': 'templates.troops',
        'village.units': 'templates.troops',
        'building.default': 'templates.builder',
        'village_template.units': 'templates.troops',
        'village.building': 'templates.builder',
        'village_template.building': 'templates.builder'
    }
    if key in templates:
        return preprocess_select(key, value, templates[key], village_id)
    if village_id:
        return '<input type="text" class="form-control" data-village-id="%s" data-type="text" value="%s" data-type-option="%s" />' % (
        village_id, value, key)
    else:
        return '<input type="text" class="form-control" data-type="text" value="%s" data-type-option="%s" />' % (
            value, key)


def pre_process_number(key, value, village_id=None):
    """Pre-processes a number value for display in the web interface.

    Args:
        key (str): The configuration key.
        value (number): The number value.
        village_id (int, optional): The ID of the village. Defaults to None.

    Returns:
        str: The HTML for a number input.
    """
    if village_id:
        return '<input type="number" data-type="number" class="form-control" data-village-id="%s" value="%s" data-type-option="%s" />' % (
        village_id, value, key)
    return '<input type="number" data-type="number" class="form-control" value="%s" data-type-option="%s" />' % (
    value, key)


def pre_process_list(key, value, village_id=None):
    """Pre-processes a list value for display in the web interface.

    Args:
        key (str): The configuration key.
        value (list): The list value.
        village_id (int, optional): The ID of the village. Defaults to None.

    Returns:
        str: The HTML for a text input.
    """
    if village_id:
        return '<input type="text" data-type="list" class="form-control" data-village-id="%s" value="%s" data-type-option="%s" />' % (
        village_id, ', '.join(value), key)
    return '<input type="number" data-type="list" class="form-control" value="%s" data-type-option="%s" />' % (
    ', '.join(value), key)


def fancy(key):
    """Makes a configuration key more human-readable.

    Args:
        key (str): The configuration key.

    Returns:
        str: The formatted key with a help text if available.
    """
    name = key
    if '.' in name:
        name = name.split('.')[1]
    name = name[0].upper() + name[1:]
    out = '<hr /><strong>%s</strong>' % name
    help_txt = None
    help_key = key
    help_key = help_key.replace('village_template', 'village')
    if help_key in help_file:
        help_txt = help_file[help_key]
    if help_txt:
        out += '<br /><i>%s</i>' % help_txt
    return out


def pre_process_config():
    """Pre-processes the main configuration for display in the web interface.

    Returns:
        dict: A dictionary of HTML strings for each configuration section.
    """
    # TODO get generic config
    config = sync()['config']
    to_hide = ["build", "villages"]
    sections = {}
    for section in config:
        if section in to_hide:
            continue
        config_data = ""
        for parameter in config[section]:
            value = config[section][parameter]
            kvp = "%s.%s" % (section, parameter)
            if type(value) == bool:
                config_data += '%s %s' % (fancy(kvp), pre_process_bool(kvp, value))
            if type(value) == str:
                config_data += '%s %s' % (fancy(kvp), pre_process_string(kvp, value))
            if type(value) == list:
                config_data += '%s %s' % (fancy(kvp), pre_process_list(kvp, value))
            if type(value) == int or type(value) == float:
                config_data += '%s %s' % (fancy(kvp), pre_process_number(kvp, value))
        sections[section] = config_data
    return sections


def pre_process_village_config(village_id):
    """Pre-processes the configuration for a specific village.

    Args:
        village_id (int): The ID of the village.

    Returns:
        str: The HTML for the village configuration.
    """
    config = sync()['config']['villages']
    if village_id in config:
        config = config[village_id]
    else:
        config = config[config.keys()[0]]
    config_data = ""
    for parameter in config:
        value = config[parameter]
        kvp = "village.%s" % parameter
        if type(value) == bool:
            config_data += '%s %s' % (fancy(kvp), pre_process_bool(kvp, value, village_id))
        if type(value) == str:
            config_data += '%s %s' % (fancy(kvp), pre_process_string(kvp, value, village_id))
        if type(value) == list:
            config_data += '%s %s' % (fancy(kvp), pre_process_list(kvp, value, village_id))
        if type(value) == int or type(value) == float:
            config_data += '%s %s' % (fancy(kvp), pre_process_number(kvp, value, village_id))
    return config_data


def sync():
    """Synchronizes the data from the bot's cache.

    Returns:
        dict: A dictionary of all the data from the cache.
    """
    reports = DataReader.cache_grab("reports")
    villages = DataReader.cache_grab("villages")
    attacks = DataReader.cache_grab("attacks")
    config = DataReader.config_grab()
    managed = DataReader.cache_grab("managed")
    bot_status = bm.is_running()

    sort_reports = {key: value for key, value in sorted(reports.items(), key=lambda item: int(item[0]))}
    n_items = {k: sort_reports[k] for k in list(sort_reports)[:100]}

    out_struct = {
        "attacks": attacks,
        "villages": villages,
        "config": config,
        "reports": n_items,
        "bot": managed,
        "status": bot_status
    }
    return out_struct


@app.route('/api/get', methods=['GET'])
def get_vars():
    """API endpoint to get all the data from the cache.

    Returns:
        JSON: A JSON object of all the data from the cache.
    """
    return jsonify(sync())


@app.route('/bot/start')
def start_bot():
    """API endpoint to start the bot.

    Returns:
        JSON: A JSON object with the status of the bot.
    """
    bm.start()
    return jsonify(bm.is_running())


@app.route('/bot/stop')
def stop_bot():
    """API endpoint to stop the bot.

    Returns:
        JSON: A JSON object with the status of the bot.
    """
    bm.stop()
    return jsonify(not bm.is_running())


@app.route('/config', methods=['GET'])
def get_config():
    """Renders the configuration page.

    Returns:
        HTML: The rendered configuration page.
    """
    return render_template('config.html', data=sync(), config=pre_process_config(), helpfile=help_file)


@app.route('/village', methods=['GET'])
def get_village_config():
    """Renders the village configuration page.

    Returns:
        HTML: The rendered village configuration page.
    """
    data = sync()
    vid = request.args.get("id", None)
    return render_template('village.html', data=data, config=pre_process_village_config(village_id=vid),
                           current_select=vid, helpfile=help_file)


@app.route('/map', methods=['GET'])
def get_map():
    """Renders the map page.

    Returns:
        HTML: The rendered map page.
    """
    sync_data = sync()
    center_id = request.args.get("center", None)
    center = next(iter(sync_data['bot'])) if not center_id else center_id
    map_data = json.dumps(MapBuilder.build(sync_data['villages'], current_village=center, size=15))
    return render_template('map.html', data=sync_data, map=map_data)


@app.route('/villages', methods=['GET'])
def get_village_overview():
    """Renders the village overview page.

    Returns:
        HTML: The rendered village overview page.
    """
    return render_template('villages.html', data=sync())


@app.route('/building_templates', methods=['GET', 'POST'])
def get_building_templates():
    """Renders the building templates page.

    Returns:
        HTML: The rendered building templates page.
    """
    if request.form.get('new', None):
        plain = os.path.basename(request.form.get('new'))
        if not plain.endswith('.txt'):
            plain = "%s.txt" % plain
        tempfile = '../templates/builder/%s' % plain
        if not os.path.exists(tempfile):
            with open(tempfile, 'w') as ouf:
                ouf.write("")
    selected = request.args.get('t', None)
    return render_template('templates.html',
                           templates=BuildingTemplateManager.template_cache_list(),
                           selected=selected,
                           buildings=buildings)


@app.route('/', methods=['GET'])
def get_home():
    """Renders the home page.

    Returns:
        HTML: The rendered home page.
    """
    session = DataReader.get_session()
    return render_template('bot.html', data=sync(), session=session)


@app.route('/app/js', methods=['GET'])
def get_js():
    """Serves the main JavaScript file.

    Returns:
        File: The JavaScript file.
    """
    urlpath = os.path.join(os.path.dirname(__file__), "public")
    return send_from_directory(urlpath, "js.v2.js")


@app.route('/app/config/set', methods=['GET'])
def config_set():
    """API endpoint to set a configuration value.

    Returns:
        JSON: A JSON object of all the data from the cache.
    """
    vid = request.args.get("village_id", None)
    if not vid:
        DataReader.config_set(parameter=request.args.get("parameter"), value=request.args.get("value", None))
    else:
        param = request.args.get("parameter")
        if param.startswith("village."):
            param = param.replace("village.", "")
        DataReader.village_config_set(village_id=vid, parameter=param, value=request.args.get("value", None))

    return jsonify(sync())


if len(sys.argv) > 1:
    app.run(host="localhost", port=sys.argv[1])
else:
    app.run()
