import asyncio

import telegram

from core.filemanager import FileManager
from core.exceptions import InvalidJSONException


class _Notification:
    """Handles sending notifications via Telegram.

    This class reads Telegram bot configuration from the main config file,
    and provides a method to send messages to a specified channel.
    """
    bot = None
    enabled = False
    channel_id = None
    token = None

    def __init__(self):
        """Initializes the notification service."""
        self.get_config()

        if self.enabled:
            self.loop = asyncio.new_event_loop()
            self.bot = telegram.Bot(token=self.token)

    def get_config(self):
        """Loads notification settings from the config file."""
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
        """Sends a message to the configured Telegram channel.

        Args:
            message (str): The message to send.
        """
        if not self.enabled or not self.bot:
            return

        task = self.loop.create_task(self.send_async(message))
        self.loop.run_until_complete(task)

    async def send_async(self, message):
        """Asynchronously sends a message.

        Args:
            message (str): The message to send.
        """
        await self.bot.send_message(chat_id=self.channel_id, text=message)


Notification = _Notification()
