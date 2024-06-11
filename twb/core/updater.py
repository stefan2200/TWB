"""
Update checking logic
"""

import json
import logging
import os.path
import time
from pathlib import Path

import requests


def check_update(config_path: str) -> None:
    """
    If enabled, check whether the config template version matches the one on github
    Notify and 5 seconds sleep if update is available
    """
    local_config_example = (
        Path(__file__).resolve().parent.parent / "templates" / "config.example.json"
    )

    # os.path.join(
    #     os.path.dirname(__file__),
    #     "..",
    #     "config.example.json"
    # )

    config = Path(config_path).resolve()
    # get_local_config_version = os.path.join(
    #     os.path.dirname(__file__),
    #     "..",
    #     "config.json"
    # )
    if os.path.exists(config):
        with open(config, encoding="utf-8") as running_cf:
            parsed = json.load(fp=running_cf)
            if not parsed["bot"].get("check_update", False):
                return
    with open(local_config_example, encoding="utf-8") as local_cf:
        parsed = json.load(fp=local_cf)
        get_remote_version = requests.get(
            "https://raw.githubusercontent.com/stefan2200/TWB/master/config.example.json",
            timeout=10,
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
