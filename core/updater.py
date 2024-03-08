"""
Update checking logic
"""

import json
import os.path
import time
import requests
import logging


def check_update():
    """
    If enabled, check whether the config template version matches the one on github
    Notify and 5 seconds sleep if update is available
    """
    get_local_config_template_version = os.path.join(
        os.path.dirname(__file__),
        "..",
        "config.example.json"
    )

    get_local_config_version = os.path.join(
        os.path.dirname(__file__),
        "..",
        "config.json"
    )
    if os.path.exists(get_local_config_version):
        with open(get_local_config_version, "r", encoding="utf-8") as running_cf:
            parsed = json.load(fp=running_cf)
            if not parsed["bot"].get("check_update", False):
                return
    with open(get_local_config_template_version, "r", encoding="utf-8") as local_cf:
        parsed = json.load(fp=local_cf)
        get_remote_version = requests.get(
            "https://raw.githubusercontent.com/stefan2200/TWB/master/config.example.json"
        ).json()
        if parsed["build"]["version"] != get_remote_version["build"]["version"]:
            logging.warning(
                "There is a new version of the bot available. \n"
                "Download the latest release from: \n"
                "https://github.com/stefan2200/TWB"
            )
            time.sleep(5)
        else:
            logging.info("The bot is up-to-date")
