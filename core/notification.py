import asyncio

import telegram

from core.filemanager import FileManager
from core.exceptions import InvalidJSONException


class _Notification:
    bot = None
    enabled = False
    channel_id = None
    token = None

    def __init__(self):
        self.get_config()

        if self.enabled:
            self.loop = asyncio.new_event_loop()
            self.bot = telegram.Bot(token=self.token)

    def get_config(self):
        try:
            config = FileManager.load_json_file("config.json")
        except InvalidJSONException:
            config = None
            self.enabled = False
        if config:
            notification_config = config.get("notifications", {})
            self.enabled = notification_config.get("enabled", False)
            self.channel_id = notification_config.get("channel_id")
            self.token = notification_config.get("token")

    def send(self, message):
        if not self.enabled or not self.bot:
            return

        task = self.loop.create_task(self.send_async(message))
        self.loop.run_until_complete(task)

    async def send_async(self, message):
        await self.bot.send_message(chat_id=self.channel_id, text=message)


Notification = _Notification()
