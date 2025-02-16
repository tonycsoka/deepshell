import asyncio
import secrets
from textual.app import App, ComposeResult
from textual.widgets import Input, RichLog
from textual import events
from textual.containers import Vertical
from ui.rendering import Rendering

class ChatMode(App):
    _instance = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        """Ensure that only one instance of the class exists (Singleton)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, manager):
            super().__init__() 
            if self._initialized:
                return
            self.pswd = None
            self.manager = manager
            self.client = manager.client
            self.buffer= asyncio.Queue()
            self.rendering = Rendering(self)
            self.system_message = (
            f"Chat with model: {self.client.model} in {self.client.mode.name} mode.\n\n"
            "Type 'exit' to quit.\n\n"
        )

    def compose(self) -> ComposeResult:
        """Create UI layout with a fixed bottom input and scrollable output."""
        yield Vertical(
            RichLog(highlight=True, markup=True ,id="rich_log"), 
            Input(placeholder="Type here and press Enter...", id="input_field")  
        )

    def on_ready(self) -> None:
        """Initialize queue and start background listeners."""
       
        self.rich_log_widget = self.query_one(RichLog)
        self.input_widget = self.query_one(Input)
        self.input_widget.focus()
        asyncio.create_task(self.rendering.render_output())
        asyncio.create_task(self.buffer.put(self.system_message))

        file = None
        user_input = None
        if self.manager.client_deployer.file:
            file = self.manager.client_deployer.file
            self.manager.client_deployer.file = None
        if self.manager.client_deployer.user_input:
            user_input = self.manager.client_deployer.user_input
            self.manager.client_deployer.user_input = None
        if file or user_input:
            asyncio.create_task(self.manager.deploy_task(user_input,file))
        
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
                    if self.pswd:
                        self.pswd = secrets.token_urlsafe(32)
                        self.pswd = None
                    self.exit()
                else:
                    asyncio.create_task(self.buffer.put(f"\n[bold green]You:[/bold green] {text}"))
                    self.input_widget.clear()
                    self.input_widget.focus()
                    asyncio.create_task(self.buffer.put("\n[bold blue]AI:[/bold blue] "))
                    asyncio.create_task(self.manager.deploy_task(text))


    def wait_for_input(self):
        """Helper method to wait for input asynchronously."""
        self.input_future = asyncio.Future()
        return self.input_future


    async def get_user_input(self, prompt_text: str = "Enter input:", input_text: str = "", is_password: bool = False):
        """Waits for user input asynchronously and returns the value.
        If is_password is True, masks the input like a password.
        """
        await self.buffer.put(f"\nSystem: {prompt_text}")
        
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
            self.input_widget.placeholder = "Type here and press Enter:..."
        
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
                await self.buffer.put("\nIt is a Yes or No question.")





