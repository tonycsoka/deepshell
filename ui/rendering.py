import re
import asyncio
from utils.logger import Logger
from config.settings import RENDER_DELAY

logger = Logger.get_logger()

class Rendering:
    def __init__(self, chat_app):
        self.chat_app = chat_app
        self.cleaner = re.compile(r'(#{3,4}|\*\*)')
        self.delay = RENDER_DELAY
        self._lock = asyncio.Lock()

    async def render_output(self, line):
        """Rendering lines while stripping away some of the markdown tags"""
        async with self._lock:
            cleaned_line = self.cleaner.sub('', line.strip()) 
            self.chat_app.rich_log_widget.write(cleaned_line, animate=True)
            self.chat_app.rich_log_widget.scroll_end()

    async def fancy_print(self, content):
        """Render string line by line, preserving newlines and other whitespace."""
        self.chat_app.input_widget.disabled = True
        lines = content.split('\n')
        
        for line in lines:
            await self.render_output(line) 
            await asyncio.sleep(self.delay)
        
        self.chat_app.input_widget.disabled = False
        self.chat_app.input_widget.focus()
   
    async def transfer_buffer(self, content):
        """
        Continuously transfer data from the source_buffer (e.g., filtering's buffer)
        into the UI's rendering buffer.
        Accumulates lines before transferring them.
        Skips lines that consist solely of newlines or spaces.
        """
        self.chat_app.input_widget.disabled = True
        accumulated_line = ""
        first_chunk = True

        try:
            if isinstance(content, asyncio.Queue):
                while True:
                    chunk = await content.get()
                    if chunk is None:
                        if accumulated_line and accumulated_line.strip():
                            await self.render_output(accumulated_line)
                        accumulated_line = ""
                        self.chat_app.input_widget.disabled = False
                        self.chat_app.input_widget.focus()
                        break
                    if first_chunk:
                        chunk = "[green]AI: [/]" + chunk.lstrip("\n")
                        first_chunk = False
                    accumulated_line += chunk

                    if "\n" in accumulated_line:
                        if accumulated_line.strip():
                            await self.render_output(accumulated_line)
                        accumulated_line = ""  

            elif hasattr(content, "__aiter__"):
                async for chunk in content:
                    if first_chunk:
                        chunk = "[green]AI: [/]" + chunk.lstrip("\n")
                        first_chunk = False
                    accumulated_line += chunk

                    if "\n" in accumulated_line:
                        if accumulated_line.strip():
                            await self.render_output(accumulated_line)
                        await asyncio.sleep(self.delay)
                        accumulated_line = ""

            else:
                if first_chunk:
                    content = "[green]AI: [/]" + content.lstrip("\n")
                    first_chunk = False
                accumulated_line += content
                if "\n" in accumulated_line:
                    if accumulated_line.strip():
                        await self.render_output(accumulated_line)
                    await asyncio.sleep(self.delay)
                    accumulated_line = ""

        except Exception as e:
            self.chat_app.input_widget.disabled = False
            self.chat_app.input_widget.focus()
            raise e

        if accumulated_line:
            if accumulated_line.strip():
                await self.render_output(accumulated_line)
            await asyncio.sleep(self.delay)

        self.chat_app.input_widget.disabled = False
        self.chat_app.input_widget.focus()

