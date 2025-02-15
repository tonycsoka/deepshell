import asyncio
from utils.command_processor import CommandProcessor
from pipeline.pipe_filter import PipeFilter
from config.settings import Mode 

class ChatManager:
    def __init__(self, client, ui=None):
        self.client = client
        self.ui = ui
        self.filtering = PipeFilter(client) 
        self.output_buffer = self.filtering.buffer
        self.command_processor = CommandProcessor(client, ui)
        self.file_utils = self.command_processor.file_utils 
        self.executor = self.command_processor.executor
        self.tasks = []

    async def deploy_task(self, user_input=None, file=None):
        file_content = None
        if file:
            file_content = await self.file_utils.process_file_or_folder(file)
            user_input = self.command_processor.format_input(user_input, file_content)
            
        user_input = await self.command_processor.handle_command(user_input)
        if isinstance(user_input, tuple):
            user_input, bypass_flag = user_input
        else:
            user_input, bypass_flag = user_input, False
       
        await self.task_manager(user_input,bypass_flag)
    
    async def task_manager(self, user_input,bypass=False):
        if self.client.mode == Mode.SHELL or bypass:
            await self._handle_shell_mode(user_input,bypass)
        elif self.client.mode == Mode.CODE:
            await self._handle_code_mode(user_input)
        else: 
            await self._handle_default_mode(user_input)

        return self.client.last_response

       
    async def _handle_shell_mode(self,input,bypass=False):
        if not bypass:
            await self._handle_code_mode(input)
            input = self.filtering.extracted_code
            output = await self.executor.start(input)
        else:
            output = await self.executor.execute_command(input)

        if output:
            if self.ui and await self.ui.yes_no_prompt("\nDo you want to see the output?\n (Y)es or (No)"):
                await self.ui.buffer.put(output)
            await self._handle_default_mode(output)
        else:
            if self.ui:
                await self.ui.buffer.put("\nNo output detected...")

                
    async def _handle_code_mode(self,input):
        get_stream = asyncio.create_task(self.client._chat_stream(input))
        process_text = asyncio.create_task(self.filtering.process_stream(True))
        self.tasks = [get_stream, process_text]
        await asyncio.gather(*self.tasks)

        if self.ui:
            await self.ui.buffer.put(self.filtering.extracted_code)
        self.tasks = []
        return self.filtering.extracted_code

    async def _handle_default_mode(self,input): 
        get_stream = asyncio.create_task(self.client._chat_stream(input))
        process_text = asyncio.create_task(self.filtering.process_stream(False))
        self.tasks = [get_stream, process_text]
        if self.ui:
            rendering_task = asyncio.create_task(self.ui.transfer_buffer(self.output_buffer))
            self.tasks.append(rendering_task)

        await asyncio.gather(*self.tasks)
        self.tasks = []
        return self.client.last_response 


