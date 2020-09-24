

# How-to
Help file for explaining the bot workflow

### New player
The bot should work from the moment you first join a world.
It will automatically build the first buildings and complete the first quests (if enabled).
When the barracks is built the recruitment process should start. 
If the first spear units start rolling off the conveyor belt the farm process should also start to do its thing.

In some time the bot should also start to figure out which units to research / upgrade. 


### After some time
If your buildings have reached some higher levels the bot starts to create market trades.
This allows the building process to keep working at high efficiency.

Whenever the world has the "flags" system enabled the bot will also attempt to upgrade and set the highest "resource bonus" flag.
At this point farming tweak system (manager.py) should be able to detect which farms have the highest / lowest resource gain and automatically tweak the village parameters.

### After some more time
You will reach the point where other players can attack you. 
They might think your village is an easy target but with the right parameters set you will have a very good army.

Whenever an incoming attack is detected the bot will stop the farming process and automatically set the highest "defence bonus" flag.
Valuable (or crappy defensive) units will be evacuated whenever you have more then one village.

If the bot also has the "manage_defence" option enabled it will send defensive units as support.
This part can be configured per village

### Mid/Late game
Once you have reached the stage where the snob is built you can set the snob parameter on the village to 1.
This will start to create the necessary coins and will train a snob.

If you want stuff experimental you can set the current farm configuration to contain a snob. This will slowly start to take-over all surrounding farm villages :)

Once more villages are achieved you can set the bot to automatically copy the existing configuration to new ones. Preferably you set them manually since you probably want to tweak some stuff. 

I would also suggest you keep playing using the browser session once in a while, you might run into some captcha's which the bot will break on :)

Have fun!