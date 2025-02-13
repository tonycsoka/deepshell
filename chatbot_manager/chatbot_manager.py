import asyncio
from utils.command_processor import CommandProcessor
from utils.shell_utils import CommandExecutor
from pipeline.pipe_filter import PipeFilter
from config.settings import DEFAULT_MODEL
from utils.file_utils import FileUtils


class ChatManager:
    def __init__(self, client, ui=None):
        self.client = client
        self.ui = ui
        self.filtering = PipeFilter(client)
        self.output_buffer = self.filtering.buffer
        self.file_utils = FileUtils(ui)
        self.command_processor = CommandProcessor(client,ui)
        self.executor = CommandExecutor(ui)
        self.tasks = []

    async def deploy_task(self, user_input=None,file=None):
        file_content = None
        if file:
            file_content = await self.file_utils.process_file_or_folder(file)
            user_input = self.command_processor.format_input(user_input, file_content)
            
        user_input = await self.command_processor.handle_command(user_input)

        

        await self.task_manager(user_input)
    
    async def task_manager(self, input):
     
        # Start fetching the response from the API and process the text concurrently
        get_stream = asyncio.create_task(self.client._chat_stream(input))
        process_text = asyncio.create_task(self.filtering.process_stream())  # Process & clean text
        self.tasks = [get_stream, process_text]

        if self.client.config_name == "shell":
       
            await self._handle_shell_mode()
        elif self.client.config_name == "code":
            await self._handle_code_mode()

        await asyncio.gather(*self.tasks)
        self.task = []    

    async def _handle_shell_mode(self):
        await asyncio.gather(*self.tasks)
        command = await self.filtering.extract_code(keep_formatting=self.client.render_output, shell = True)
        output = await self.executor.start(command)
        if output:
            self.client.model = DEFAULT_MODEL
            self.client.config_name = "default"
            await self.output_buffer.put(output)
            process = asyncio.create_task(self.deploy_task(output))
            self.tasks.append(process)
    
    async def _handle_code_mode(self):
        await asyncio.gather(*self.tasks)
        code = await self.filtering.extract_code(keep_formatting=self.client.render_output,shell  = False)
        self.tasks = []

        print(code) 

