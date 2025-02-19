import asyncio
from utils.command_processor import CommandProcessor
from config.system_prompts import shell_helper, analyzer_helper
from config.settings import Mode
from ui.ui import ChatMode
from chatbot.deployer import ChatBotDeployer

class ChatManager:
    """
    Manages the chatbot's operations, including initializing the client, handling user commands,
    managing tasks, and rendering outputs.
    """

    def __init__(self):
        self.deployer = ChatBotDeployer()  # Use ChatBotDeployer to handle deployments
        self.client, self.filtering = self.deployer.deploy_chatbot()
        self.ui = ChatMode(self) if self.client.render_output else None
        self.deployer.ui = self.ui or None 
        self.command_processor = CommandProcessor(self.ui)
        self.file_utils = self.command_processor.file_utils
        self.executor = self.command_processor.executor
        self.tasks = []
        self.listener, self.listener_filter = None, None

    async def client_init(self):
        """
        Initializes the chatbot in the specified mode.
        """
        chatbot_data = await self.deployer.chatbot_init()  
        self.client, self.filtering = chatbot_data[:2]  # Always extract client & filtering
        
        if len(chatbot_data) > 2:  # SHELL mode includes listener & filter
            self.listener, self.listener_filter = chatbot_data[2:]

    async def deploy_task(self, user_input=None, file_name=None, file_content=None):
        """
        Deploys a task based on user input and file content.
        """
        if file_name and not file_content:
            file_content = await self.file_utils.process_file_or_folder(file_name)
        if file_content:
            user_input = self.command_processor.format_input(user_input, file_content)
        else:
            user_input = await self.command_processor.handle_command(user_input)
        
        user_input, bypass_flag = (user_input if isinstance(user_input, tuple) else (user_input, False))

        return await self.task_manager(user_input, bypass_flag)

    async def task_manager(self, user_input, bypass=False):
        """
        Manages tasks based on the client's mode.
        """
        mode_handlers = {
            Mode.SHELL: lambda input: self._handle_shell_mode(input, bypass),
            Mode.CODE: self._handle_code_mode,
        }
        
        if bypass:
            return await self._handle_shell_mode(user_input, bypass)

        if self.client.mode in mode_handlers:
            return await mode_handlers[self.client.mode](user_input)
        else:
            return await self._handle_default_mode(user_input)

    async def _handle_shell_mode(self, input, bypass=False):
        """
        Handles tasks when the client is in SHELL mode.
        """
        if not bypass:
            input = await self._handle_code_mode(shell_helper(input), no_render=True)
            input, output = await self.executor.start(input)

            if output:
                if self.ui and await self.ui.yes_no_prompt("\nDo you want to see the output?\n(Y)es or (No)\n"):
                    await self.ui.buffer.put(output)
                output = analyzer_helper(input,output)
                await self._handle_default_mode(output, client=self.listener,filtering=self.listener_filter)            
            else:
                if self.ui:
                    await self.ui.fancy_print("\nNo output detected...\n")
        else:
            output = await self.executor.execute_command(input)

            if output:
                if self.ui and await self.ui.yes_no_prompt("\nDo you want to see the output?\n (Y)es or (No)\n"):
                    await self.ui.buffer.put(output)
                output = analyzer_helper(input,output)
                await self._handle_default_mode(output, client=self.listener,filtering=self.listener_filter) if self.client.mode != Mode.DEFAULT else await self._handle_default_mode(output)
            else:
                if self.ui:
                    await self.ui.fancy_print("\nNo output detected...\n")

        self.client.last_response = ""
        self.filtering.extracted_code = ""

    async def _handle_code_mode(self, input, no_render=False):
        """
        Handles tasks when the client is in CODE mode.
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

    async def _handle_default_mode(self, input, no_render=False, client = None, filtering = None):
        """
        Handles tasks when the client is in the default mode.
        """
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
        return client.last_response

    # async def _handle_listener(self, input, no_render=False):
    #     """
    #     Handles tasks when the client is in listener mode.
    #     """
    #     if self.listener and self.listener_filter:
    #         get_stream = asyncio.create_task(self.listener._chat_stream(input))
    #         process_text = asyncio.create_task(self.listener_filter.process_stream(False))
    #         self.tasks = [get_stream, process_text]
    #
    #         if self.ui and not no_render:
    #             rendering_task = asyncio.create_task(self.ui.transfer_buffer(self.listener_filter.buffer))
    #             self.tasks.append(rendering_task)
    #
    #         await asyncio.gather(*self.tasks)
    #         self.tasks = []
    #         return self.listener.last_response
