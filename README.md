# Tribal Wars Bot (TWB)
## An open source bot for the Tribal Wars game

## Update 2.0.2 notice
Simplification of the project. Renamed to TWBot. Find more info and download from [PyPi]

[PyPi]: https://pypi.org/project/TWBot/

## A Simple Example

```python
# save this as app.py
from twb.bot import TWB


def main():
    TWB(config_path="config.json").run()


if __name__ == "__main__":
    main()
```

We also created a [Discord](https://discord.gg/8PuzHjttMy) server so you can seek help from other users.

*Features:*
- Cooperative mode (you can keep playing using the browser while the bot manages stuff in the background)
- Building management
- Defence management
- Troop management
- Flag management
- Automatically adds conquered villages
- Farm management
- Market management
- Premium market (free premium points :D)
- Research management (including level systems)
- Automatic snob creation
- Report management
- ReCaptcha "bypass" by using browser cookie string (bot works if browser session is valid)

*How To:*
- Install library
- Run using example above
- Default config will be created on startup
	- add at least the endpoint and server
	- change the village_template configuration section to your needs


- Start the bot by running python twb.py and supply the cookie string from your browser
- If login works you can adjust the config.json to your needs, it will automatically reload on change.
- Your villages will be added to the config automatically, disable the "managed" parameter to make the bot skip the village
- Additional properties can be tweaked by running the manager.py script
- You might want to set the bot user-agent in core/request.py to your own user agent. They probably wont notice but just in case :)

You can find the cookie string in the following location (Chrome):

![Screenshot](readme/network.JPG)

You need to use the cookie: header value

*optional: If everything is set-up correctly and the bot is running you can `cd` into the webmanager directory and start the bot interface by running `server.py`. You can access this dashboard by visiting http://127.0.0.1:5000/ in your browser.
A lot of new features will be added to the dashboard soon.*

More information about configuring the bot can be found in the readme directory!
