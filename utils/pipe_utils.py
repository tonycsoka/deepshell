import asyncio
import sys
import shutil
import textwrap
from utils.command_processor import CommandProcessor

class PipeUtils:
    def __init__(self, chat_manager):
        self.chat_manager = chat_manager

    async def read_pipe(self):
        """Read piped input asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sys.stdin.read)

    async def handle_pipe(self, ollama_client, user_input=None):
        """Handles pipe input, formats the user input, and runs the task manager."""
        pipe_input = await self.read_pipe()

        if pipe_input:
            if user_input:
                processor = CommandProcessor(ollama_client)
                user_input = processor.format_input(user_input, pipe_input)
            else:
                user_input = pipe_input

        task_manager_task = asyncio.create_task(self.chat_manager.task_manager(user_input))
        print_task = asyncio.create_task(self.print_from_buffer(task_manager_task))

        await asyncio.gather(task_manager_task, print_task)

    async def print_from_buffer(self, task_manager_task):
        """Prints messages from the output buffer with typewriter effect and ensures proper termination."""
        terminal_width = shutil.get_terminal_size().columns
        accumulated_text = ""

        while True:
            if task_manager_task.done() and self.chat_manager.output_buffer.empty():
                break

            try:
                message = await asyncio.wait_for(self.chat_manager.output_buffer.get(), timeout=1)
            except asyncio.TimeoutError:
                continue

            if message is None:
                break

            accumulated_text += message

            if accumulated_text.endswith(('.', '!', '?')):
                wrapped_lines = textwrap.wrap(accumulated_text, width=terminal_width)
                for line in wrapped_lines:
                    await self.typewriter_print(line)

                accumulated_text = ""

        print("\n")

    async def typewriter_print(self, text, delay=0.01):
        """Simulates a typewriter effect by printing text one character at a time."""
        for char in text:
            print(char, end='', flush=True)
            await asyncio.sleep(delay)
        print() 

    async def run(self, ollama_client, user_input):
        """Runs the full pipe handling process."""
        await self.handle_pipe(ollama_client, user_input)

