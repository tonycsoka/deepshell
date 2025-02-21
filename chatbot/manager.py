import asyncio
from ui.ui import ChatMode
from utils.logger import Logger
from config.settings import Mode
from chatbot.helper import PromptHelper
from chatbot.history import HistoryManager
from chatbot.deployer import ChatBotDeployer
from utils.command_processor import CommandProcessor

logger = Logger.get_logger()

class ChatManager:
    """
    Manages the chatbot's operations, including initializing the client, handling user commands,
    managing tasks, and rendering outputs.
    """

    def __init__(self):
        self.deployer = ChatBotDeployer() 
        self.client, self.filtering = self.deployer.deploy_chatbot() 

        self.ui = ChatMode(self) if self.client.render_output else None
        self.deployer.ui = self.ui or None

        self.history_manager = HistoryManager()
        self.history = self.history_manager.history
        self.add_to_history = self.history_manager.add_message 
        self.generate_prompt = self.history_manager.generate_prompt
        self.add_file = self.history_manager.add_file
        self.add_folder = self.history_manager.add_folder_structure

        self.command_processor = CommandProcessor(self)
        self.file_utils = self.command_processor.file_utils
        self.executor = self.command_processor.executor

        self.tasks = []
       
    async def deploy_task(self, user_input=None, file_name=None, file_content=None):
        """
        Deploys a task based on user input and file content.
        """
        logger.info("Deploy task started.")
        
        if file_name:
            logger.info("Processing file: %s", file_name)
            await self.file_utils.process_file_or_folder(file_name)
            if not user_input:
                user_input = f"Analyze {file_name}"
        
        elif file_content:
            logger.info("Pipe input detected.")
            if not user_input:
                user_input = f"Analyze this: {file_content}"
            else:
                user_input = f"{user_input} Content: {file_content}"

        else:
            logger.info("No file content, processing user input.")
            user_input = await self.command_processor.handle_command(user_input)

        
        user_input, bypass_flag = (user_input if isinstance(user_input, tuple) else (user_input, False))
        
        if self.client.keep_history:
            await self.add_to_history("user", user_input)
            logger.info("User input added to history.")
            user_input = await self.generate_prompt(user_input)
        
        logger.info("Executing task manager.")
        response = await self.task_manager(user_input, bypass_flag)
        
        if self.client.keep_history:
            await self.add_to_history("assistant", response)
            logger.info("Assistant response added to history.")
        
        logger.info("Deploy task completed.")
        return response

    async def task_manager(self, user_input, bypass=False):
        """
        Manages tasks based on the client's mode.
        """
        logger.info("Task manager started in mode: %s", self.client.mode)

        
        
        mode_handlers = {
            Mode.SHELL: lambda input: self._handle_shell_mode(input, bypass),
            Mode.CODE: self._handle_code_mode,
        }
        
        if bypass:
            logger.info("Bypassing mode, executing shell mode.")
            return await self._handle_shell_mode(user_input, bypass)
        
        if self.client.mode in mode_handlers:
            logger.info("Handling task in mode: %s", self.client.mode)
            return await mode_handlers[self.client.mode](user_input)
        else:
            logger.info("Handling task in default mode.")
            return await self._handle_default_mode(user_input)

    async def _handle_shell_mode(self, input, bypass=False):
        """
        Handles tasks when the client is in SHELL mode.
        """
        logger.info("Shell mode execution started. Bypass: %s", bypass)
        
        if not bypass:
            input = await self._handle_code_mode(PromptHelper.shell_helper(input), no_render=True)
            input, output = await self.executor.start(input)
        else:
            output = await self.executor.execute_command(input)
        
        if output:
            logger.info("Command executed, processing output.")
            if self.ui and await self.ui.yes_no_prompt("Do you want to see the output?", default="No"):
                await self.ui.buffer.put(output)
            
            output = PromptHelper.analyzer_helper(input, output)
           
            await self._handle_default_mode(output)
        else:
            logger.warning("No output detected.")
            if self.ui:
                await self.ui.fancy_print("\nNo output detected...\n")
        
        self.client.last_response = ""
        self.filtering.extracted_code = ""
        logger.info("Shell mode execution completed.")

    async def _handle_code_mode(self, input, no_render=False):
        """
        Handles tasks when the client is in CODE mode.
        """
        logger.info("Code mode execution started.")
        
        get_stream = asyncio.create_task(self.client._chat_stream(input))
        process_text = asyncio.create_task(self.filtering.process_stream(True))
        self.tasks = [get_stream, process_text]
        await asyncio.gather(*self.tasks)
        
        code = self.filtering.extracted_code
        if self.ui and not no_render:
            await self.ui.fancy_print(code)
        
        self.tasks = []
        logger.info("Code mode execution completed.")
        return code

    async def _handle_default_mode(self, input, no_render=False, client=None, filtering=None):
        """
        Handles tasks when the client is in the default mode.
        """
        logger.info("Default mode execution started.")
        
        if not client or not filtering:
            client = self.client
            filtering = self.filtering
        
        get_stream = asyncio.create_task(client._chat_stream(input))
        process_text = asyncio.create_task(filtering.process_stream(False))
        self.tasks = [get_stream, process_text]
        
        if self.ui and not no_render:
            rendering_task = asyncio.create_task(self.ui.transfer_buffer(filtering.buffer))
            self.tasks.append(rendering_task)
        
        await asyncio.gather(*self.tasks)
        self.tasks = []
        
        logger.info("Default mode execution completed.")
        return client.last_response

