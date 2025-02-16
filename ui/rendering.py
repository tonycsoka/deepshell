import asyncio

class Rendering:
    def __init__(self, chat_app):
        self.chat_app = chat_app

    async def render_output(self):
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



