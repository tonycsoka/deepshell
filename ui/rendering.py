import re
import asyncio

class Rendering:
    def __init__(self, chat_app):
        self.chat_app = chat_app

    async def render_output(self):
        """Rendering the content from the buffer,word by word"""
        accumulated_text = ""
        while True:
            chunk = await self.chat_app.buffer.get()
            if chunk is None:
                break
            chunk = chunk.replace("###", "")
            chunk = chunk.replace("####", "")
            chunk = chunk.replace("**", "")

            accumulated_text += chunk
            self.chat_app.rich_log_widget.clear()
            self.chat_app.rich_log_widget.write(accumulated_text)
            self.chat_app.rich_log_widget.scroll_end()
        await asyncio.sleep(0.01)


    async def fancy_print(self, content, delay=0.03):
        """Render string word by word, preserving newlines and other whitespace."""
        # Split content into chunks, keeping spaces and newlines
        chunks = re.split(r'(\s+)', content)  # Split by any whitespace (spaces, tabs, newlines)
        
        for chunk in chunks:
            # Check if chunk is empty or whitespace and handle accordingly
            if chunk == '\n':  # Handle newline separately to ensure correct formatting
                await self.chat_app.buffer.put('\n')  # Send newline directly to the buffer
            elif chunk.isspace():  # Handle spaces and tabs
                await self.chat_app.buffer.put(chunk)  # Send space or tab directly to the buffer
            else:
                await self.chat_app.buffer.put(chunk)  # Send words to buffer
            await asyncio.sleep(delay) 
    

    async def transfer_buffer(self, content):
        """
        Continuously transfer data from the source_buffer (e.g. filtering's buffer)
        into the UI's rendering buffer, but only if the transfer is enabled.
        """
        if isinstance(content, asyncio.Queue):
            while True:
                chunk = await content.get()
                if chunk is None:
                    break
                await self.chat_app.buffer.put(chunk)
        elif hasattr(content, "__aiter__"):
            async for chunk in content:
                await self.chat_app.buffer.put(chunk)
        else:
             await self.chat_app.buffer.put(content)

