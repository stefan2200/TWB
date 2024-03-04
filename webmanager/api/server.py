import sys

import flask
from flask_cors import CORS

from filemanager import FileManager

app = flask.Flask(__name__)
app.config["DEBUG"] = True
CORS(app, resources={r"/api*": {"origins": "http://localhost:*"}})


@app.route('/api/config', methods=['GET'])
def get_config():
    config = FileManager.read_json_file("config.json")
    if not config:
        return flask.jsonify({"error": "config.json does not exist."}), 500

    return flask.jsonify(config)


@app.route('/api/config', methods=['PUT'])
def update_config():
    data = flask.request.json
    FileManager.write_json_file("config.json", data)
    return flask.jsonify({"message": "Config updated."}), 200


if __name__ == "__main__":
    if len(sys.argv) > 1:
        app.run(host="localhost", port=int(sys.argv[1]))
    else:
        app.run()
