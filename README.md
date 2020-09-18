# ~~Warning: this code works with the current version (07-05-2020) but will not be maintained by me any further!~~
# ok maybe just a few little updates :)

_When migrating from v1.1 please delete the cache/villages folder_

*Features:*

- Basic build queue
- Automatic troop management
- Automatic scouting (and attack if empty)
- Automatic farming (based on range) also very configurable
- Market management
- Research (both systems)
- Automatic snob creation
- Report management
- ReCaptcha bypass by using browser cookie string (bot works if browser session is valid)

There is a lot of unfinished code which somewhat works but is not yet implemented.

*How To:*
- Install Python 3.x
- Install the requirements (pip install -r requirements.txt)
- Rename config.example.json to config.json and edit the following things:
	- add at least the endpoint, world and server
	- In the village config set the VillageID (from the village overview page)
	- Add additional villages in JSON dictionary format

- Start the bot by running python twb.py and supply the cookie string from your browser
- If login works you can adjust the config.json to your needs, it will automatically reload on change.
- Additional properties can be tweaked by running the manager.py script

More information about configuring the bot can be found in the readme directory!


