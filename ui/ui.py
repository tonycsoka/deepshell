import asyncio
from chatbot_manager.chatbot_manager import ChatManager
from textual.app import App, ComposeResult
from textual.widgets import Input, RichLog
from textual import events
from textual.containers import Vertical
from rich.markdown import Markdown as RichMarkdown

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
            self.buffer= asyncio.Queue()
            self.user_input = user_input
            self.file = file 
            self.system_message = (
            f"Chat with model: {self.client.model} in {self.client.mode.name} mode.\n\n"
            "Type 'exit' to quit.\n\n"
        )

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
       # asyncio.create_task(self.fancy_printer())
        asyncio.create_task(self.render_output())
        asyncio.create_task(self.buffer.put(self.system_message))
        if self.user_input or self.file:
            asyncio.create_task(self.manager.deploy_task(self.user_input,self.file))
            asyncio.create_task(self.buffer.put(f"\n\nYou: {self.user_input or self.file}\n\n"))
            asyncio.create_task(self.buffer.put("AI: "))


    async def on_key(self, event: events.Key) -> None:
        """Handles user input from the keyboard."""
        if event.key == "enter":
            text = self.input_widget.value or ""
            text = text.strip()
            
            # If there's a pending input future (from get_user_input), resolve it and return early.
            if hasattr(self, "input_future") and self.input_future and not self.input_future.done():
                self.input_future.set_result(text)
                self.input_widget.clear()
                self.input_widget.focus()
                return
            
            if text:
                if text.lower() == "exit":
                    self.exit()
                else:
                    asyncio.create_task(self.buffer.put(f"\n\n**You:** {text}\n\n"))
                    self.input_widget.clear()
                    self.input_widget.focus()
                    asyncio.create_task(self.buffer.put("\n\nAI: "))
                    asyncio.create_task(self.manager.deploy_task(text))


    def wait_for_input(self):
        """Helper method to wait for input asynchronously."""
        self.input_future = asyncio.Future()
        return self.input_future


    async def get_user_input(self, prompt_text: str = "Enter input:", input_text: str = "", is_password: bool = False):
        """Waits for user input asynchronously and returns the value.
        If is_password is True, masks the input like a password.
        """
        await self.buffer.put(f"\n\nSystem: {prompt_text}\n\n")
        
        self.input_widget.value = input_text  # Set initial text
        self.input_widget.placeholder = prompt_text

        if is_password:
            self.input_widget.password = True
            self.input_widget.placeholder = "●●●●●●●●"
        else:
            self.input_widget.password = False

        result = await self.wait_for_input()
        user_input = result.strip() if result else ""
        
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
                await self.buffer.put(chunk)
        else:
             await self.buffer.put(content)
                   
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
            await asyncio.sleep(0.01)
        
        if accumulated_text:
            self.rich_log_widget.clear()
            self.rich_log_widget.write(RichMarkdown(accumulated_text))
            self.rich_log_widget.scroll_end()


 
    async def transfer_buffer(self, source_buffer):
        """
        Continuously transfer data from the source_buffer (e.g. filtering's buffer)
        into the UI's rendering buffer, but only if the transfer is enabled.
        """
        while True:
            chunk = await source_buffer.get()
            if chunk is None:
                break
            await self.buffer.put(chunk)
        # Signal completion.
       # await self.buffer.put(None)


    async def yes_no_prompt(self,prompt_text):
        """Prompts the user to execute, modify, or cancel a command."""
        while True:
            choice = await self.get_user_input(prompt_text=prompt_text)
            if choice:
                choice = choice.strip().lower()

                if choice in ("yes", "y"):
                    return True  
       
                elif choice in ("no","n"):
                    return False

            else:
                await self.buffer.put("\n\nSystem: Invalid choice, it's a Yes or No question.\n\n")

