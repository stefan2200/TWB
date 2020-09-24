### New in v1.4.1
- Automatic upgrading of out-dated config files
- Removed selenium (inc. Web Driver)
- How-To readme
- Minor bug-fixes

### New in v1.4
- Reworked config methods so the bot works with all config versions (with warnings tho)
- Automatic requesting and sending support
- Attack / resource flag management
- Automatic evacuation of high-profile units (snob, axe)
- Found out why snob recruiting was not working (fix in progress)
- Minor bug-fixes

_When migrating from v1.1 please delete the cache/villages folder_

*Features:*

- Basic build queue
- Defence management
- Automatic troop management
- Automatic scouting (and attack if empty)
- Flag management
- Automatic farming (based on range) also very configurable
- Market management (also exchange leftovers for premium points)
- Research (both systems)
- Automatic snob creation
- Report management
- ReCaptcha bypass by using browser cookie string (bot works if browser session is valid)

*How To:*
- Install Python 3.x
- Install the requirements (pip install -r requirements.txt)
- Rename config.example.json to config.json and edit the following things:
	- add at least the endpoint and server
	- In the village config set the VillageID (from the village overview page)
	- Add additional villages in JSON dictionary format

- Start the bot by running python twb.py and supply the cookie string from your browser
- If login works you can adjust the config.json to your needs, it will automatically reload on change.
- Additional properties can be tweaked by running the manager.py script

More information about configuring the bot can be found in the readme directory!


