import sys
import asyncio
from utils.command_processor import CommandProcessor
from utils.shell_utils import CommandExecutor
from pipeline.pipe_filter import PipeFilter
from ui.ui_manager import UIManager
from config.settings import DEFAULT_MODEL
from utils.file_utils import FileUtils

class ChatManager:
    def __init__(self, ollama_client):
        self.ollama_client = ollama_client
        self.file_utils = FileUtils()
        self.filtering = PipeFilter(ollama_client)
        self.output_buffer = self.filtering.buffer
        self.command_processor = CommandProcessor(ollama_client)
        self.executor = CommandExecutor()
        self.ui_manager = UIManager()  # Single UI instance for the session
        self.tasks = []

    async def start_chat(self, user_input=None,file=None):
        system_message = f"""Chat with model: {self.ollama_client.model} in {self.ollama_client.config_name} mode.\n\nType 'exit' to quit.\n\n"""
        file_content = None

        if file:
            file_content = await self.file_utils.process_file_or_folder(file)

            if file_content:
                user_input = self.command_processor.format_input(user_input, file_content)

      
        if self.ollama_client.render_output:
            
            ui_task = asyncio.create_task(self.ui_manager.run())
            await self.ui_manager.rich_print(system_message)
        
            while True:
                if not user_input:
                    user_input = await self.ui_manager.get_user_input()

                if user_input.lower() == "exit":
                    await self.ui_manager.rich_print("Goodbye.")
                    await self.ui_manager.shutdown()
                    await ui_task
                    break
                else:
                    await self.ui_manager.rich_print(f"\n\nYou: {user_input}\n")
                    user_input = await self.command_processor.handle_command(user_input)
                    if not user_input:
                        continue

                await self.task_manager(user_input)
                user_input = None
        else:
            await self.task_manager(user_input)
            return


    async def task_manager(self, input):
     
        # Start fetching the response from the API and process the text concurrently
        get_stream = asyncio.create_task(self.ollama_client._chat_stream(input))
        process_text = asyncio.create_task(self.filtering.process_stream())  # Process & clean text
        self.tasks = [get_stream, process_text]

        if self.ollama_client.config_name == "shell":
       
            await self._handle_shell_mode()
        elif self.ollama_client.config_name == "code":
            await self._handle_code_mode()

        else: #Default mode 
             if self.ollama_client.render_output:

                render_output = asyncio.create_task(self.ui_manager.transfer_buffer(self.filtering.buffer))
                self.tasks.append(render_output)

             else:           
                print_task = asyncio.create_task(self.ui_manager.print_buffer(self.filtering.buffer))
                self.tasks.append(print_task)

        await asyncio.gather(*self.tasks)
        self.task = []    

    async def _handle_shell_mode(self):
        await asyncio.gather(*self.tasks)
        command = await self.filtering.extract_code(keep_formatting=self.ollama_client.render_output, shell = True)
       
 
        output = await self.executor.start(command)
        if output:
            self.ollama_client.model = DEFAULT_MODEL
            self.ollama_client.config_name = "default"
            if self.ollama_client.render_output:
                render_task = asyncio.create_task(self.ui_manager.buffer.put(output))
                self.tasks.append(render_task)
            process = asyncio.create_task(self.start_chat(output))
            self.tasks.append(process)
    
    async def _handle_code_mode(self):
        await asyncio.gather(*self.tasks)
        code = await self.filtering.extract_code(keep_formatting=self.ollama_client.render_output,shell  = False)
        self.tasks = []

        print(code) 

