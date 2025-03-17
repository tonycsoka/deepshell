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
        self.client, self.filtering = ChatBotDeployer.deploy_chatbot() 
        self.ui = ChatMode(self) if self.client.render_output else None
        self.last_mode = None
                
        self.command_processor = CommandProcessor(self)
        self.file_utils = self.command_processor.file_utils
        self.executor = self.command_processor.executor

        self.history_manager = HistoryManager(self)
        self.add_to_history = self.history_manager.add_message
        self.add_terminal_output = self.history_manager.add_terminal_output
        self.generate_prompt = self.history_manager.generate_prompt

        self.file_utils.set_index_functions(self.history_manager.add_file,self.history_manager.add_folder_structure)

        self.tasks = []
        
    async def init_shell(self):
        """
        Helper functon to initialize shell session.
        """
        await self.executor.start_shell()

    async def stop_shell(self):
        """
        Helper functon to stop the shell session.
        """
        await self.executor.stop_shell()
       
    async def deploy_task(self, user_input=None, file_name=None, file_content=None):
        """
        Deploys a task based on user input and file content.
        """
        logger.info("Deploy task started.")
        response = None
        self.last_mode = self.client.mode
        
        if file_name:
            logger.info("Processing file: %s", file_name)
            await self.file_utils.process_file_or_folder(file_name)
            if not user_input:
                user_input = f"Analyze this content"
        
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
          
        logger.info("Executing task manager.")

        if bypass_flag or self.client.mode != Mode.DEFAULT:

            response = await self.task_manager(user_input = user_input,bypass = bypass_flag)
        
        if self.client.keep_history and self.client.mode != Mode.SHELL and not response:
            history = await self.generate_prompt(user_input)
            response = await self.task_manager(history=history)

        if self.client.keep_history and response:
            await self.add_to_history("assistant", response)

        if self.client.mode != self.last_mode:
            self.client.switch_mode(self.last_mode)

        logger.info("Deploy task completed.")
        return response


    async def task_manager(self, user_input = None, history = None, bypass = False):
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
            return await self._handle_default_mode(input= user_input, history = history)

    async def _handle_shell_mode(self, input, bypass=False, no_render = False):
        """
        Handles tasks when the client is in SHELL mode.
        """
        logger.info("Shell mode execution started. Bypass: %s", bypass)
        
        if not bypass:
            input = await self._handle_code_mode(PromptHelper.shell_helper(input), no_render=True)
            input, output = await self.executor.start(input)
        else:
            output = await self.executor.run_command(input)

        if output == "pass":
            if self.ui:
                await self.ui.fancy_print("[cyan]System:[/] command executed successfully")
            return "pass"
        
        if output and input:
            logger.info("Command executed, processing output.")
            if self.ui:        

                await self.ui.fancy_print(f"[cyan]System:[/] Executing [green]'{input}'[/]")
               
                if await self.ui.yes_no_prompt("Do you want to see the output?", default="No"):
                   render_task = asyncio.create_task(self.ui.fancy_print(f"[blue]Shell output[/]:\n{output}"))
                   self.tasks.append(render_task)
                await asyncio.sleep(0.1)
                if await self.ui.yes_no_prompt("Analyze the output?", default="Yes"):
                    if len(self.tasks) != 0:
        
                        asyncio.create_task(self.execute_tasks())
                    await self.ui.fancy_print("[cyan]System:[/] Output submitted to the chatbot for analysis...")

                    prompt = PromptHelper.analyzer_helper(input, output)
                    self.client.switch_mode(Mode.SYSTEM)
                    
                    get_summary = asyncio.create_task(self.client._chat_stream(prompt))
                    if not no_render:
                        render = True
                    else:
                        render = False
                    filter_summary = asyncio.create_task(self.filtering.process_stream(False,render != no_render))

                    self.tasks.append(get_summary)
                    self.tasks.append(filter_summary)
                    
                    await self.execute_tasks()
                   

                                                 
                    if self.client.keep_history and self.client.last_response:
                        await self.add_terminal_output(input,output,self.client.last_response)
                    self.client.switch_mode(Mode.SHELL)
                    return self.client.last_response

                else:
                    if len(self.tasks) != 0:
                        await self.execute_tasks()
                    if self.client.keep_history:
                        await self.add_terminal_output(input,output,"")
                    return output

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
       
        response = await self.client._fetch_response(input)
        code = await self.filtering.process_static(response,True)

        if code:
            if self.ui and not no_render:
                await self.ui.fancy_print(code)
            return code

    async def _handle_default_mode(self, input= None, history = None, no_render=False):
        """
        Handles tasks when the client is in the default mode.
        """
        logger.info("Default mode execution started.")

        client = self.client
        filtering = self.filtering
        if history and not input:
            get_stream = asyncio.create_task(client._chat_stream(history = history))
            logger.info("Passing the history to the chatbot")
        elif input and not history:
            get_stream = asyncio.create_task(client._chat_stream(input))
        else:
            logger.error("Invalid input")
            return

        if self.ui and not no_render:
            rendering = True
        else: 
            rendering = False

        process_text = asyncio.create_task(filtering.process_stream(False,rendering))
        self.tasks = [get_stream, process_text]
        
        # if self.ui and not no_render:
        #     rendering_task = asyncio.create_task(self.ui.transfer_buffer(filtering.buffer))
        #     self.tasks.append(rendering_task)
       
        await self.execute_tasks() 
        logger.info("Default mode execution completed.")

        return client.last_response

    async def execute_tasks(self):
        try:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error in default mode execution: {e}")

        self.tasks = []

