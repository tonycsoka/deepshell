import re
import shlex
import string
import asyncio
import secrets
from utils.logger import Logger
from config.settings import SHELL_TYPE, MONITOR_INTERVAL, MAX_OUTPUT_LINES, FINALIZE_OUTPUT

logger = Logger.get_logger()

class CommandExecutor:
    """
    A class for executing shell commands asynchronously, handling sudo authentication,
    monitoring execution, and processing command outputs.
    """

    def __init__(self, ui=None):
        """
        Initializes the CommandExecutor.
        
        Args:
            ui: Optional user interface object for interactive input/output.
            monitor_interval (int): Interval (in seconds) to check for long-running commands.
            max_output_length (int): Maximum length of output before truncation.
        """
        self.history = []
        self.ui = ui
        self._should_stop = False
        self.sudo_password = None
        self.monitor_interval = MONITOR_INTERVAL
        self.max_output_lines = MAX_OUTPUT_LINES
        self.finalize_output = FINALIZE_OUTPUT
        self.shell_type = SHELL_TYPE
        self.process: asyncio.subprocess.Process | None = None
        if self.ui:
            self.sudo_password = self.ui.pswd


    async def start_shell(self):
        """Starts a persistent shell session if not already running."""
 
        if self.process is None or self.process.returncode is not None:
            self.process = await asyncio.create_subprocess_exec(
                self.shell_type,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            logger.info("Started persistent shell session.")

   
   
    
    async def run_command(self, command: str) -> str | None:
        if self.process is None or self.process.stdin is None or self.process.stdout is None:
            await self.start_shell()
            if self.process is None or self.process.stdin is None or self.process.stdout is None:
                logger.error("Failed to start shell process.")
                return "Error: Shell process could not be started."

        if "sudo" in shlex.split(command):
            await self._get_sudo_password()

        # Unique delimiter to detect command completion
        delimiter = "----END-OF-COMMAND----"
        full_command = f"stdbuf -oL {command} ; echo '{delimiter}' ; echo $?\n"

        logger.debug(f"Executing: {full_command}")
        self.process.stdin.write(full_command.encode())
        await self.process.stdin.drain()
        
        output_lines = []
        exit_code = None

        while True:
            line = await self.process.stdout.readline()
            if not line:
                break

            decoded_line = line.decode(errors="ignore").strip()

            if decoded_line == delimiter:
                # Read the exit code after delimiter
                exit_code_line = await self.process.stdout.readline()
                exit_code = int(exit_code_line.decode(errors="ignore").strip())
                break

            # Skip empty lines
            if decoded_line:
                output_lines.append(decoded_line)

        result = "\n".join(output_lines).strip()

        logger.info(f"Command produced {len(output_lines)} lines")
        logger.debug(f"Command result : {result}")

        if exit_code == 0 and not result:
            logger.info("Command executed successfully with no output")
            return "pass"

        
        if result and self.finalize_output:
            result = await self._finalize_command_output(output_lines)
            return result if result else f"Command failed with exit code {exit_code}"
        
    async def stop_shell(self):
        """Stops the persistent shell session."""
        if self.process and self.process.returncode is None:
            self.process.terminate()
            await self.process.wait()
            self.process = None
            logger.info("Shell session terminated.")
        else:
            logger.warning("Process already terminated or not started.")
 
   
    async def start(self, command=None):
        """
        Starts execution of the given command.
        
        Args:
            command (str, optional): The command to execute.
        
        Returns:
            tuple: (confirmed_command, command output or error message)
        """
        logger.info("Execution started.")
    
        confirmed_command = None
        output = "No command specified."

        if command:
            logger.info("Command received, confirming execution.")
            confirmed_command = await self.confirm_execute_command(command)
            if confirmed_command:
                logger.info("Command confirmed, executing.")
                output = await self.run_command(confirmed_command)
            else:
                return None, None
        
        logger.info("Execution finished.")
        logger.debug(f"Command: {confirmed_command} Output: {output}")
        return confirmed_command, output


    async def execute_command(self, command):
        """
        Executes a shell command asynchronously without starting a shell session.
        
        Args:
            command (str): The command to execute.
        
        Returns:
            str: The command output or an error message.
        """
        if not command:
            return "No command provided."

        logger.info("Executing command.")
       
        require_sudo = True if "sudo" in shlex.split(command) else False

        if require_sudo:
            if not self.sudo_password:
                logger.info("Requesting sudo password.")
                await self._get_sudo_password()
            if not self.sudo_password:
                logger.warning("Sudo password not provided.")
                return None
            command = f"echo {self.sudo_password} | sudo -S {command[5:]}"

        proc = await self._start_subprocess(command)
        if proc is None:
            logger.error("Subprocess creation failed.")
            return "Error: Command did not produce valid output or is not interactive."

        logger.info("Processing command output.")
        return await self._process_command_output(proc)
    
    async def _start_subprocess(self, command):
        """
        Starts an asynchronous subprocess to execute a command.
        
        Args:
            command (str): The command to execute.
        
        Returns:
            subprocess.Process: The subprocess object.
        """
        return await asyncio.create_subprocess_shell(
            f"{self.shell_type} -c '{command}'",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    async def _process_command_output(self, proc):
        """
        Processes the output of a running command.
        
        Args:
            proc (subprocess.Process): The running subprocess.        
        Returns:
            str: The processed command output.
        """
        logger.info("Processing command output.")
        output_lines = []
        monitor_task = asyncio.create_task(self._monitor_execution(proc))

        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode("utf-8", errors="ignore").strip()

                # Extract meaningful text
                extracted_text = self._extract_meaningful_text(decoded_line)
                if extracted_text:
                    output_lines.append(extracted_text)

                # Handle potential user prompts
                if self._should_handle_prompt(decoded_line):
                    await self._handle_prompt(proc, decoded_line)

        except asyncio.CancelledError:
            logger.warning("Command execution cancelled.")
            proc.terminate()
            await proc.wait()
            return "\n".join(output_lines)
        finally:
            monitor_task.cancel()

        # Validate if we received output
        if not output_lines:
            output_lines.append("No output received. Command may require user interaction or is piped.")
 
        logger.info("Command output processing completed.")
        return await self._finalize_command_output(output_lines)


    def _extract_meaningful_text(self, data):
        """
        Cleans and extracts meaningful text from command output.
        
        Args:
            data (str): The raw command output.
        
        Returns:
            str: The cleaned output or None if empty.
        """
        # Strip out known non-text patterns (control codes, escape sequences)
        cleaned_data = re.sub(r'\x1b[^m]*m', '', data)  # Remove ANSI escape sequences
        cleaned_data = re.sub(r'[\x00-\x1F\x7F]', '', cleaned_data)  # Remove control characters

        # Try to extract the core content from the output
        if len(cleaned_data.strip()) > 0:
            return cleaned_data.strip()
        else:
            return None
   

    async def _monitor_execution(self, proc):
        """
        Periodically checks the status of a running process and prompts the user 
        to cancel execution if it exceeds the monitoring interval.
        
        Args:
            proc (asyncio.subprocess.Process): The process being monitored.
        """
        while True:
            await asyncio.sleep(self.monitor_interval)
            if proc.returncode is not None:
                break
            user_choice = await self._get_user_input(
                "\nCommand is taking longer than expected. Cancel execution? (y/n): "
            )
            if user_choice.strip().lower() in ["y", "yes"]:
                await self._print_message("Terminating command execution...")
                proc.terminate()
                break

    
    async def _finalize_command_output(self, output_lines):
        """
        Finalizes the command output, ensuring truncation if too long and handling errors.

        Args:
            output_lines (list): Collected output lines.
        

        Returns:
            str: The final output.
        """
        logger.info("Finalizing command output.")

        # Truncate based on the number of lines
        if len(output_lines) > self.max_output_lines:
            logger.warning("Output truncated due to line limit.")
            output_lines = output_lines[:self.max_output_lines] + ["[Output truncated]"]

        output_str = "\n".join(output_lines) 
        self._clear_sudo_password()
        logger.info("Command execution completed.")
        
        return output_str

    async def _get_sudo_password(self):
        """
        Prompts the user for a sudo password if not already provided.
        Validates the password before storing it.
        """
        if self.ui and hasattr(self.ui, 'pswd') and self.ui.pswd:
            self.sudo_password = self.ui.pswd
        else:
            self.sudo_password = await self._get_user_input("Enter sudo password: ", is_password=True)
            if self.sudo_password:
                valid = await self._validate_sudo_password(self.sudo_password)
                if valid:
                    if self.ui:
                        self.ui.pswd = self.sudo_password
                    return self.sudo_password
                else:
                    if self.ui:
                        self.ui.pswd = None
                    self.sudo_password = None
                    await self._print_message("Wrong password")
                    logger.warning("Wrong sudo password")
                    return None

    
    async def _validate_sudo_password(self, sudo_password):
        """
        Validates the provided sudo password.
        
        Args:
            sudo_password (str): The sudo password to validate.
        
        Returns:
            bool: True if valid, False otherwise.
        """
        command = f"echo {sudo_password} | sudo -S -v"
        
        # If we have an existing persistent shell with valid stdin and stdout, use it.
        if self.process is not None and self.process.stdin is not None and self.process.stdout is not None:
            full_command = f"stdbuf -oL {command}\n echo $?\n"
            self.process.stdin.write(full_command.encode())
            await self.process.stdin.drain()
            
            exit_code = None
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode(errors="ignore").strip()
                # Assume the exit code is output as a standalone digit.
                if decoded_line.isdigit():
                    exit_code = int(decoded_line)
                    break
            proc_valid = (exit_code == 0)
        else:
            # Fall back to spawning a new subprocess.
            proc = await self._start_subprocess(command)
            # Wait for the process to complete.
            await proc.communicate()
            proc_valid = (proc.returncode == 0)

        if proc_valid:
            logger.info("Sudo password validated.")
            # Overwrite and clear the password for security.
            sudo_password = secrets.token_urlsafe(32)
            sudo_password = None
            return True
        else:
            logger.warning("Invalid sudo password.")
            return False

    def _clear_sudo_password(self):
        """
        Clears the stored sudo password securely by overwriting it before setting 
        it to None.
        """
        self.sudo_password = secrets.token_urlsafe(32)
        self.sudo_password = None
        logger.info("Clearing sudo password securely.")


    def _is_text(self, data):
        """
        Determines whether the given data is likely to be human-readable text.
        
        Args:
            data (str): The output data to check.
        
        Returns:
            bool: True if the data is mostly printable text, False otherwise.
        """
        if not data or "\x00" in data:
            return False

        # Remove ANSI escape sequences
        data = re.sub(r'\x1b[^m]*m', '', data)

        # Calculate printable ratio
        printable_chars = sum(c in string.printable for c in data)
        printable_ratio = printable_chars / len(data) if len(data) > 0 else 0

        # Allow outputs with more than 70% printable characters (but filter out pure control codes or binary data)
        if printable_ratio < 0.7 or any(c in "\x07\x1b" for c in data):
            return False

        return True 

   
    def _should_handle_prompt(self, decoded_line):
        """
        Checks if a command output line contains a user prompt requiring a response.
        
        Args:
            decoded_line (str): The command output line.
        
        Returns:
            bool: True if the line contains a recognized prompt, False otherwise.
        """
        return any(kw in decoded_line.lower() for kw in ["[y/n]", "(yes/no)", "(y/n)", "password:", "continue?"])


   
    async def _handle_prompt(self, proc, decoded_line):
        """
        Detects and responds to command-line prompts automatically.
        
        Args:
            proc (asyncio.subprocess.Process): The process awaiting input.
            decoded_line (str): The prompt message from the command output.
        """
        if "password:" in decoded_line.lower():
            response = self.sudo_password or await self._get_user_input("Enter password: ", is_password=True)
        else:
            response = "yes"

        proc.stdin.write(response.encode() + b"\n")
        await proc.stdin.drain()
        response = secrets.token_urlsafe(32)
        response = None

   
    async def confirm_execute_command(self, command):
        """
        Prompts the user to confirm and possibly edit a command before execution.
        
        Args:
            command (str): The command to confirm.
        
        Returns:
            str: The confirmed command or None if canceled.
        """
        command = command.lstrip()

        command = await self._get_user_input(
            'Validate the command and press [blue]Enter[/].\nOr delete the text and press [blue]Enter[/] to cancel',
            input_text=command
        )
        
        return command if command else None 


    async def _get_user_input(self, prompt_text: str = "Enter input: ", is_password=False, input_text=""):
        if self.ui is not None:
            return await self.ui.get_user_input(prompt_text, is_password=is_password, input_text=input_text)
        else:
            return input(prompt_text)


    async def _print_message(self, message: str):
        """Print messages either through UI or terminal."""
        if self.ui:
            await self.ui.fancy_print(f"[cyan]System:[/cyan] {message}")
        else:
            print(message)
