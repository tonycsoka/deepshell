import asyncio
from utils.command_processor import CommandProcessor
from pipeline.pipe_filter import PipeFilter
from config.system_prompts import *
from config.settings import Mode 
from ollama_client.client_deployer import ClientDeployer
from ui.ui import ChatMode

class ChatManager:
    """
    Manages the chatbot's operations, including initializing the client, handling user commands,
    managing tasks, and rendering outputs. It operates in different modes (SHELL, CODE, or default) 
    and interacts with the client to process and execute user inputs and display the results.

    Attributes:
        client_deployer (ClientDeployer): Responsible for deploying the chatbot client.
        client (Client): The chatbot client, which processes commands and communicates with the server.
        ui (ChatMode or None): User interface for interacting with the chatbot, if available.
        filtering (PipeFilter): Handles the extraction and filtering of code and other content.
        output_buffer (asyncio.Queue): A buffer that stores output data for rendering.
        command_processor (CommandProcessor): Processes user commands and prepares them for execution.
        file_utils (FileUtils): Handles file-related operations during command execution.
        executor (Executor): Executes commands or scripts within the chatbot environment.
        tasks (list): A list of tasks that are being executed concurrently.
    """

    def __init__(self):
        self.client_deployer = ClientDeployer()
        self.client = self.client_deployer.deploy()
        
        if self.client.render_output:
            self.ui = ChatMode(self)
        else:
            self.ui = None
        
        self.filtering = PipeFilter(self.client) 
        self.output_buffer = self.filtering.buffer

        self.command_processor = CommandProcessor(self.ui)
        self.file_utils = self.command_processor.file_utils 
        self.executor = self.command_processor.executor
        self.tasks = []
       

    def deploy_listener(self,mode):
        deployer = ClientDeployer()
        listener = deployer.deploy()
        listener.switch_mode(mode)
        filter = PipeFilter(listener)
        return listener,filter
        

    async def client_init(self, mode=None):
        """
        Initializes the chatbot in the specified mode (SHELL, CODE, or SYSTEM). 

        In SHELL mode:
        - Deploys two clients:
            1. **Command Generator**: Generates commands (SHELL mode).
            2. **Output Analyzer**: Analyzes output (SYSTEM mode).
        - This is needed because DeepSeek ignores the system prompt, so it must be passed as a user prompt.
        
        In default mode, only the respective task is launched without a prompt.

        Parameters:
        - mode (optional): The mode for the client. Defaults to the current mode if not provided.
        """
        if not mode:
            mode = self.client.mode
        self.client.init = True
        if self.ui:
            await self.ui.fancy_print("\n[yellow]Initializing chatbot.\nPlease wait...[/yellow]\n")
            
        if mode == Mode.SHELL:
            self.listener, self.listener_filter = self.deploy_listener(Mode.SYSTEM)
            self.listener.init = True
            analyzer = asyncio.create_task(self.listener._chat_stream(SYSTEM))
            await asyncio.sleep(1)
            generator = asyncio.create_task(self.client._chat_stream(SHELL))
            await asyncio.gather(analyzer,generator)
            self.listener.init = False

        elif mode == Mode.CODE:
            await self.client._chat_stream(CODE)
        elif mode == Mode.SYSTEM:
            await self.client._chat_stream(SYSTEM)
        self.client.init = False
        if self.ui: 
            await self.ui.fancy_print("\n[cyan]Chatbot initialized[/cyan]\n\n")

    async def deploy_task(self, user_input=None, file_name=None, file_content=None):
        """
        Deploys a task based on user input and file content. If a file is provided, its content is processed.
        Otherwise, the input is handled as a command.
        """
        if file_name and not file_content:
            file_content = await self.file_utils.process_file_or_folder(file_name)
        if file_content:
            user_input = self.command_processor.format_input(user_input, file_content)
        else:
            user_input = await self.command_processor.handle_command(user_input)
        if isinstance(user_input, tuple):
            user_input, bypass_flag = user_input
        else:
            user_input, bypass_flag = user_input, False

        return await self.task_manager(user_input, bypass_flag)

    async def task_manager(self, user_input, bypass=False):
        """
        Manages tasks based on the client's mode (SHELL, CODE, or default). Calls the appropriate handler
        based on the current mode and returns the chatbot's last response.
        """
        if self.client.mode == Mode.SHELL or bypass:
            await self._handle_shell_mode(user_input, bypass)
        elif self.client.mode == Mode.CODE:
            await self._handle_code_mode(user_input)
        else:
            await self._handle_default_mode(user_input)
        return self.client.last_response

    async def _handle_shell_mode(self, input, bypass=False):
        """
        Handles tasks when the client is in SHELL mode. This includes:
        1. Parsing the user input to the chatbot for processing.
        2. Executing the command.
        3. Parsing the output back to the chatbot for analysis.

        Args:
            input (str): The input command to execute.
            bypass (bool, optional): Whether to bypass the default shell behavior.
        """
        if not bypass:
            input = await self._handle_code_mode(input,no_render=True)
            
            output = await self.executor.start(input)
            
            if output:
                if self.ui and await self.ui.yes_no_prompt("\nDo you want to see the output?\n (Y)es or (No)\n"):
                    await self.ui.buffer.put(output)
                await self._handle_listener(output)
            else:
                if self.ui:
                    await self.ui.fancy_print("\nNo output detected...\n")

        else:
            output = await self.executor.execute_command(input)

            if output:
                if self.ui and await self.ui.yes_no_prompt("\nDo you want to see the output?\n (Y)es or (No)\n"):
                    await self.ui.buffer.put(output)
                if self.client.mode == Mode.DEFAULT:    
                    await self._handle_default_mode(output)
                else:
                    await self._handle_listener(output)
            else:
                if self.ui:
                    await self.ui.fancy_print("\nNo output detected...\n")

        self.client.last_response = ""
        self.filtering.extracted_code = ""

    async def _handle_code_mode(self, input,no_render = False):
        """
        Handles tasks when the client is in CODE mode. It streams the input to the client,
        processes the text, and returns any extracted code.
        """
        get_stream = asyncio.create_task(self.client._chat_stream(input))
        process_text = asyncio.create_task(self.filtering.process_stream(True))
        self.tasks = [get_stream, process_text]
        await asyncio.gather(*self.tasks)

        code = self.filtering.extracted_code
      
        if self.ui and not no_render:
            await self.ui.fancy_print(code)
        self.tasks = []
        return code

    async def _handle_default_mode(self, input,no_render = False):
        """
        Handles tasks when the client is in the default mode. It streams the input to the client,
        processes the text, and handles rendering the output in the UI.
        """
        get_stream = asyncio.create_task(self.client._chat_stream(input))
        process_text = asyncio.create_task(self.filtering.process_stream(False))
        self.tasks = [get_stream, process_text]
        if self.ui and not no_render:
            rendering_task = asyncio.create_task(self.ui.transfer_buffer(self.output_buffer))
            self.tasks.append(rendering_task)

        await asyncio.gather(*self.tasks)
        self.tasks = []
        return self.client.last_response

    async def _handle_listener(self, input, no_render = False):
        """
        Handles tasks when the client is listener mode. It streams the input to the client,
        processes the text, and handles rendering the output in the UI.
        """
        if self.listener:
            get_stream = asyncio.create_task(self.listener._chat_stream(input))
            process_text = asyncio.create_task(self.listener_filter.process_stream(False))
            self.tasks = [get_stream, process_text]
            if self.ui and not no_render:
                rendering_task = asyncio.create_task(self.ui.transfer_buffer(self.listener_filter.buffer))
                self.tasks.append(rendering_task)

            await asyncio.gather(*self.tasks)
            self.tasks = []
            self.listener.history.pop() #keeoing listneer's history clean to avoid confusion between outputs
            self.listener.history.pop()
            return self.listener.last_response
