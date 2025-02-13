import asyncio
from chatbot_manager.chatbot_manager import ChatManager
from textual.app import App, ComposeResult
from textual.widgets import Input, RichLog, Static
from textual import events
from textual.containers import Vertical
from rich.markdown import Markdown as RichMarkdown
from textual.widget import Widget

class ChatMode(App):
    _instance = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        """Ensure that only one instance of the class exists (Singleton)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, client,user_input = None, file = None):
            super().__init__() 
            if self._initialized:
                return
            self.client = client
            self.manager = ChatManager(client,self)
            self.buffer= self.manager.output_buffer
            self.user_input = user_input
            self.file = file 
            self.system_message = f"""
            Chat with model: {self.client.model} in {self.client.config_name} mode.\n\n
            Type 'exit' to quit.\n\n""" 

    def compose(self) -> ComposeResult:
        """Create UI layout with a fixed bottom input and scrollable output."""
        yield Vertical(
            RichLog(highlight=True, markup=True, id="rich_log"), 
            Input(placeholder="Type here and press Enter...", id="input_field")  
        )

    def on_ready(self) -> None:
        """Initialize queue and start background listeners."""
       
        self.rich_log_widget = self.query_one(RichLog)
        self.input_widget = self.query_one(Input)
        self.input_widget.focus()
        asyncio.create_task(self.render_output())
        asyncio.create_task(self.buffer.put(self.system_message))
        if self.user_input or self.file:
            asyncio.create_task(self.manager.deploy_task(self.user_input,self.file))
            asyncio.create_task(self.buffer.put(f"\n\n**You:** {self.user_input or self.file}\n\n"))
            asyncio.create_task(self.buffer.put("AI: "))


    def on_key(self, event: events.Key) -> None:
        """Handles user input from the keyboard."""
        if event.key == "enter":
            text = self.input_widget.value or ""  
            text = text.strip()

            if text:
                if text.lower() == "exit":
                    self.exit()
                else:
  
                    asyncio.create_task(self.buffer.put(f"\n\n**You:** {text}\n\n"))
                    self.input_widget.clear()
                    self.input_widget.focus()
                    asyncio.create_task(self.buffer.put("AI: "))
                    asyncio.create_task(self.manager.deploy_task(text))


    def wait_for_input(self):
        """Helper method to wait for input asynchronously."""
        self.input_future = asyncio.Future()
        return self.input_future


    async def get_user_input(self, prompt_text = "Enter input:", input_text = "", is_password = False):
            """Waits for user input asynchronously and returns the value.
            If is_password is True, masks the input like a password.
            """
      
            await self.buffer.put(f"\n**System:** {prompt_text}")
            
            self.input_widget.value = input_text
            self.input_widget.placeholder = prompt_text

            if is_password:
                self.input_widget.password = True
                self.input_widget.placeholder = "●●●●●●●●"
            else:
                self.input_widget.password = False

            await self.wait_for_input()

            user_input = self.input_widget.value
            if user_input is None:
                user_input = ""
            user_input = user_input.strip() 

            if is_password:
                self.input_widget.password = False
                self.input_widget.placeholder = "Type here and press Enter..."

            return user_input



    async def fancy_print(self, content):
        """Handles printing of both plain text and async streams with smooth character flow."""
        if isinstance(content, asyncio.Queue):
            while True:
                chunk = await content.get()
                if chunk is None:
                    break
                await self.buffer.put(chunk)
        elif hasattr(content, "__aiter__"):
            async for chunk in content:
                for line in chunk.splitlines(keepends=True):  # Preserve newlines
                    for char in line:
                        await self.buffer.put(char)
                        await asyncio.sleep(0.01)
        else:
            for line in content.splitlines(keepends=True):  # Preserve newlines
                for char in line:
                    await self.buffer.put(char)
                    await asyncio.sleep(0.01)

    async def render_output(self):
        accumulated_text = ""
        while True:
            chunk = await self.buffer.get()
            if chunk is None:
                break
            accumulated_text += chunk  
            self.rich_log_widget.clear()  
            self.rich_log_widget.write(RichMarkdown(accumulated_text))
            self.rich_log_widget.scroll_end()
        
        if accumulated_text:
            self.rich_log_widget.clear()
            self.rich_log_widget.write(RichMarkdown(accumulated_text))
            self.rich_log_widget.scroll_end()



