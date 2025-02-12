import os
import asyncio
from prompt_toolkit.application import Application
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.document import Document



def get_terminal_width():
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80


class UIManager:
    _instance = None
    _initialized: bool = False  # Explicitly declared for IDE

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, refresh_rate=10):
        if self._initialized:
            return
        
        self.refresh_rate = refresh_rate
        self.displayed_text = ""
        self.buffer = asyncio.Queue()
        self.is_listening = False
        self.buffer_paused = False
        self.listener_task = None
        self.input_future = None

     
        # Input Field
        self.input_field = TextArea(
            height=1,
            prompt="You: ",
            multiline=False,
            accept_handler=self._handle_input,
            width=get_terminal_width(),
        )

        # Output Field (Scrollable & Selectable)
        self.output_field = TextArea(
            text="",
            read_only=True,  # Allows copying text
            scrollbar=True,  # Enables scrollbar
            focusable=True,  # Allows focus switching
            wrap_lines=True,
        )

        self.layout = HSplit([self.output_field, self.input_field])

        # Key Bindings
        self.kb = KeyBindings()

        @self.kb.add("c-c")
        def exit_(event):
            self.stop()
            event.app.exit()

        @self.kb.add("tab")  # Switch focus between input & output
        def switch_focus(event):
            if self.app.layout.has_focus(self.input_field):
                self.app.layout.focus(self.output_field)
            else:
                self.app.layout.focus(self.input_field)

        @self.kb.add("up")  # Scroll Up
        def scroll_up(event):
            if self.app.layout.has_focus(self.output_field):
                self.output_field.buffer.cursor_up()

        @self.kb.add("down")  # Scroll Down
        def scroll_down(event):
            if self.app.layout.has_focus(self.output_field):
                self.output_field.buffer.cursor_down()

        self.app = Application(
            layout=Layout(self.layout),
            key_bindings=self.kb,
            mouse_support=True,
        )
        self.app.layout.focus(self.input_field)


    async def listen(self):
        self.is_listening = True
        while self.is_listening:
            chunk = await self.buffer.get()
            if chunk is None:
                await asyncio.sleep(0.1)
                continue

            self.displayed_text += chunk
            self.update_output(self.displayed_text)
      

    def start_listener(self):
        if self.listener_task is None or self.listener_task.done():
            self.listener_task = asyncio.create_task(self.listen())
        elif not self.is_listening:
            self.is_listening = True

    def stop(self):
        self.is_listening = False
        if self.listener_task:
            self.listener_task.cancel()


    def update_output(self, text):
        self.output_field.buffer.set_document(Document(text), bypass_readonly=True)
        self.app.invalidate()


    def _handle_input(self, buff):
        if self.input_future and not self.input_future.done():
            self.input_future.set_result(buff.text)
           
        self.input_field.buffer.reset()
        return True

    async def run(self):
        self.start_listener()
        return await self.app.run_async()

    async def shutdown(self):
        self.stop()
        self.app.exit()


    async def get_user_input(self, prompt_text="",input_text = "" , is_password=False):
        # Set the initial prompt text
        await self.rich_print(prompt_text)
        self.input_field.text = input_text
        self.input_future = asyncio.get_event_loop().create_future()

        # If it's a password, avoid printing anything at all
        if is_password:
            # Use a custom accept handler for password input where we do not display anything
            self.input_field.accept_handler = self._password_accept_handler
        else:
            # Use the regular handler
            self.input_field.accept_handler = self._handle_input

        # Wait for the input to be provided and return it
        result = await self.input_future
       
        self.input_future = None
        return result

    def _password_accept_handler(self, _):
        # Password handling: don't display anything, just return the password
        input_text = self.input_field.text
        if self.input_future:
            self.input_future.set_result(input_text)  # Set the result of the password input
        return True

    async def rich_print(self, content):
        if hasattr(content, "__aiter__"):
            async for chunk in content:
                for line in chunk.splitlines(keepends=True):  # Preserve newlines
                    for char in line:
                        await self.buffer.put(char)
                        await asyncio.sleep(0.01)
        else:
            for line in content.splitlines(keepends=True):  # Keepends=True keeps "\n"
                for char in line:
                    await self.buffer.put(char)
                    await asyncio.sleep(0.01)
        self.start_listener()


    
    async def live_print(self, content):
        if hasattr(content, "__aiter__"):
            async for chunk in content:
                for line in chunk.splitlines(keepends=True):  # Preserve newlines
                    for char in line:
                        print(char)
                        await asyncio.sleep(0.01)
        else:
            for line in content.splitlines(keepends=True):  # Keepends=True keeps "\n"
                for char in line:
                    print(char)
                    await asyncio.sleep(0.01)
          
    async def print_buffer(self, buffer, buffer_size=10):
        temp_buffer = []  # Temporary buffer for accumulating characters

        async def flush_buffer():
            """Flush accumulated characters to stdout."""
            if temp_buffer:
                print("".join(temp_buffer), end="", flush=True)
                temp_buffer.clear()

        while True:
            chunk = await buffer.get()
            if chunk is None:
                break  # Stop when None is received

            for char in chunk:
                temp_buffer.append(char)
                if len(temp_buffer) >= buffer_size:
                    await flush_buffer()
                    await asyncio.sleep(0.01)

        await flush_buffer()  # Ensure any remaining characters are printed

 
    async def transfer_buffer(self, source_buffer):
        self.start_listener()
        while True:
            chunk = await source_buffer.get()
            if chunk is None:
                break
            while self.buffer_paused:
                await asyncio.sleep(0.05)
            await self.buffer.put(chunk)
        await self.buffer.put(None)

#shell

    async def confirm_execute_command(self, command):
        """Prompt the user to execute, modify, or cancel a command."""
        await self.rich_print(f"\nCommand to be executed: {command}")

        while True:
            choice = await self.get_user_input("\nChoose wisely (E)xecute / (M)odify / (C)ancel")

            choice = choice.strip().lower()

            if choice in ("execute", "e"):
                return command  # Execute the command as-is

            elif choice in ("modify", "m"):
                command = await self.get_user_input(prompt_text= "\nModify command",input_text=command)
                return command.strip()  # Return modified command

            elif choice in ("cancel", "c"):
                await self.rich_print("\nCommand execution canceled.")
                return None  # Cancel execution

            else:
                await self.rich_print("\nInvalid choice. Please select Execute (E), Modify (M), or Cancel (C).")

    async def yes_no_prompt(self, text):
        choice = await radiolist_dialog(
            title="Confirmation",
            text=text,
            values=[("yes", "Yes"), ("no", "No")]
        ).run_async()
        return choice == "yes"


