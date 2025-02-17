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
    CSS_PATH = "style.css"

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
            self.fancy_print = self.rendering.fancy_print
            self.transfer_buffer = self.rendering.transfer_buffer
            self.system_message = (
            f"\nChat with model: {self.client.model} in {self.client.mode.name} mode."
            "Type 'exit' to quit.\n"
        )

    def compose(self) -> ComposeResult:
        """Create UI layout with a fixed bottom input and scrollable output."""
        yield Vertical(
            RichLog(highlight=True, markup=True,wrap=True ,id="rich_log"), 
            Input(placeholder="Type here and press Enter...", id="input_field")  
        )

  
    async def on_ready(self) -> None:
        """Initialize queue and start background listeners."""
        
          # Initialize UI widgets and styles
        self.rich_log_widget = self.query_one(RichLog)
        self.input_widget = self.query_one(Input)
        self.rich_log_widget.styles.border = None
        self.input_widget.styles.border = None
        self.input_widget.focus()

        # Start rendering the output in the background
        asyncio.create_task(self.rendering.render_output())
        # Initializing client
        await self.manager.client_init()
        # Print the system message once the client is initialized
        asyncio.create_task(self.fancy_print(self.system_message))
        file = None
        user_input = None
        
        if self.manager.client_deployer.file:
            file = self.manager.client_deployer.file
            self.manager.client_deployer.file = None

        if self.manager.client_deployer.user_input:
            user_input = self.manager.client_deployer.user_input
            self.manager.client_deployer.user_input = None

        # Deploy the task with the file and user input if available
        if file or user_input:
            asyncio.create_task(self.manager.deploy_task(user_input, file))

        
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
                    asyncio.create_task(self.buffer.put(f"\n\n[bold red]You: [/bold red][white]{text}[/white]"))
                    self.input_widget.clear()
                    self.input_widget.focus()
                    asyncio.create_task(self.manager.deploy_task(text))


    def wait_for_input(self):
        """Helper method to wait for input asynchronously."""
        self.input_future = asyncio.Future()
        return self.input_future


    async def get_user_input(self, prompt_text: str = "Enter input:", input_text: str = "", is_password: bool = False):
        """Waits for user input asynchronously and returns the value.
        If is_password is True, masks the input like a password.
        """
        await self.fancy_print(f"\nSystem: {prompt_text}")
        
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





