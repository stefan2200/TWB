

# Configuration manual
Help file for defining your custom configuration file.
## Server
**Username and password** 
As of v1.2 this is no longer required since login is protected by a captcha

**Endpoint & Server & World**
These are the first parts of the URL your TW game is located at. Endpoint should start with "https://" and end at "game.php". Server and world is the server you are currently playing at, in most cases (if not all) this is the first part of the endpoint URL after "https://".

**Has Recapcha**
This has nothing to do with the in-game bot protection, it just tells the script that the regular login procedure should be skipped and ask for a cookie string instead.

**Server on TWPlus**
If your game world is not (yet) available on [http://twplus.org/](http://twplus.org/) set to false. This will automatically fetch world-related data like the population required for certain buildings.

## Remote logging
The bot has a feature for remote logging using MySQL and files.
By default every start (running twb.py) creates a new log-file based on the current timestamp.
If you want the bot to log to MySQL it is required to supply a connection string like this:
`mysql://username:password@hostname:3306/database_name`
It should automatically create the required tables if they don't exist yet. 

## Bot
This will configure non game-related related features.

**Active Hours**
Hours that the bot should be active, it defaults to 6 in the morning to 23 at night. The current time will be set to your current timezone so if your TZ differs from the game's one make sure you include the difference in time!

**Active Delay, Inactive Delay and Inactive Still Active**
Active delay configures the minimal time the bot will wait until next run during active hours. Inactive delay will configure the same for inactive hours. If inactive_still_active is disabled the bot will completely shut down during inactive hours and will probably time-out your session so you have to manually restart the bot in the morning.

**Forced Peace Times**
An array of times that you cannot attack (christmas etc..). Should be in the form of:
```
[{"start:": "%d.%m.%y %H:%M:%S", "end":"%d.%m.%y %H:%M:%S"}, {"start:": "24.12.2001 17:00:00", "end":"27.12.2001 01:00:00"}]
```

## Building
The manage_building boolean can disable building globally so you wont have to re-configure all your villages manually.
**Default** 
will set the default building template, I personally like the purple_predator one but custom ones can be supplied in the builder templates folder.

**Max Look-ahead**
The max amount of buildings in the queue that get checked if the ones before fail (like not enough resources or requirements not met yet). I suggest you keep this number below 5 because otherwise it will most likely queue the cheapest buildings first.

**Max Queued Items**
The number of items that can be queued simultaneously, default: 2. Premium accounts can have more but I do not recommend it.

## Units
This section will configure how units should be trained. With the recruit option enabled the villages should automatically start producing units upon barracks completion. By default only a few units to start the farm procedure will be created until the barracks reaches a higher level.

Unit templates can be configured in the troops template folder. The units are configured from top to bottom and the lowest one with the building requirement met will be selected as the current unit template.

The current template also indicates how much and what farm units should be used by the farm section.

**Upgrading**
By default when "upgrade" is enabled the script will automatically research units listed in the current template. This part supports both of the upgrading systems and will automatically research everything (level 0-1, 0-3, 0-10) if given enough time and resources. Higher level upgrades might take a while since most resources will be spent by the builder and recruiter.

**Batch size**
The amount of units it will attempt to recruit in one time, when entering the late-game (barracks level 25+) I suggest you set this to something in the range of 500-1500. Keeping it low will allow for more variation which is useful when just starting in a world.
Note: the batch size will always be the max amount of units in one try, if insufficient resources the script will calculate the lowest amount of units possible.

## Farms

This section will configure the farming options for all villages, every village will automatically start attacking nearby barbarian villages. If spies are available the village will get scouted first, if it does not contain troops and the wall level is zero it will automatically be added to the farm list. 
If no scouts are available or they are not yet researched the script will send 1 farm run. If it returns without any losses it should also get added to the farm list.

By default the script will choose quantity over resources since other players could also be attacking this village. The "default_away_time" parameter sets the amount of seconds the bot will wait before attacking this village again. "full_loot_away_time" does the same but for high priority villages (full loot return).

## Market
The market feature automatically manages the resources in your village. This is especially nice whenever the builder is low on a certain resource and has plenty of others.
"max_trade_duration" configures the max amount of trade time in hours, this should be kept low.

**Trading frequency**
The trader will auto remove any items that are listed more than "max_trade_duration" in hours. When also doing custom trading with the village I would suggest you disable the "auto_remove" option.

**Trade multiplier**
If your world does not allow uneven trading you should disable the "trade_multiplier" option. By default it is enabled at factor 0.9 so it will trade 900 stone for 1000 wood if 1000 is the requested resource by the builder.
I would suggest you keep the factor multiplier below 1.0 because otherwise you are paying more than you should ;)

## World options
I think only the "quests_enabled" is currently working and it should automatically finish quests once all the requirements are met. When this is the case it should restart the current run for the village because there might be a resource award paired with the quest.

# Village configuration
This configures what and how villages are being managed. Both the building and units override the global template options. If you want the bot to (temporary) skip the village you can disable the "managed" option.

**Building priority**
Whenever the "prioritize_building" is enabled the recruiter will only create units whenever the building items queued equals the "max_queued_items" value set in the building configuration.

**Snob priority**
This will force the bot to reserve resources for snob creation, only the builder has a higher priority. It will also request resources from the market for coin crafting and snob creation.
The amount of snobs that can be created in a village can be configured with the "snobs" parameter.

**Custom farms**
Each village can have a list of custom farms in the "additional_farms" parameter, the village ID's should be added as strings. 
*Note: This option can be very dangerous! if the village gets captured by you or some other player the bot will still keep attacking until troops die or the entry gets disabled in the village cache file.*

**Gathering**
If troops are not used for farming and there is no incoming attack the village will automatically attempt to start a gather operation.
You can enable/disable this using the gather parameter and set the default gather operation using the "gather_selection" option.