import re
import asyncio
from config.settings import RENDER_DELAY

class Rendering:
    _chat_app_instance = None
    def __init__(self, chat_app):
        self.chat_app = chat_app
        Rendering._chat_app_instance = chat_app
        self.cleaner = re.compile(r'(#{3,4}|\*\*)')
        self.delay = RENDER_DELAY
        self._lock = asyncio.Lock()


    async def render_output(self, line):
        """Rendering lines while stripping away some of the markdown tags"""
        async with self._lock:
            cleaned_line = self.cleaner.sub('', line.rstrip())
            self.chat_app.rich_log_widget.write(cleaned_line)
           
    async def fancy_print(self, content):
        """Render string line by line, preserving newlines and other whitespace."""
        lines = content.split('\n')
        if len(lines) > 1:
            self.chat_app.lock_input()
        
        for line in lines:
            await self.render_output(line) 
            await asyncio.sleep(self.delay)
        
        self.chat_app.unlock_input()


    @staticmethod
    async def _fancy_print(content):
        """Render string line by line, preserving newlines and other whitespace."""
        if not Rendering._chat_app_instance:
            raise ValueError("ChatApp instance not set in Rendering")

        chat_app = Rendering._chat_app_instance
        lines = content.split('\n')
        if len(lines) > 1:
            chat_app.lock_input()

        for line in lines:
            await chat_app.rendering.render_output(line)
            await asyncio.sleep(chat_app.rendering.delay)

        chat_app.unlock_input()
   
