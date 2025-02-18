import sys
import asyncio
import secrets
import string
import re


class CommandExecutor:
    """
    A class for executing shell commands asynchronously, handling sudo authentication,
    monitoring execution, and processing command outputs.
    """

    def __init__(self, ui=None, monitor_interval=90, max_output_length=600, output_validation=True):
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
        self.monitor_interval = monitor_interval
        self.max_output_length = max_output_length
        self.output_validation = output_validation
        if self.ui:
            self.sudo_password = self.ui.pswd

    async def start(self, command=None):
        """
        Starts execution of the given command.
        
        Args:
            command (str, optional): The command to execute.
        
        Returns:
            str: The command output or an error message.
        """
        if command:
            confirmed_command = await self.confirm_execute_command(command)
            if confirmed_command:
                return await self.execute_command(confirmed_command)
        else:
            await self._print_message("No command specified.")

    async def execute_command(self, command):
        """
        Executes a shell command asynchronously.
        
        Args:
            command (str): The command to execute.
        
        Returns:
            str: The command output or an error message.
        """
        if not command:
            return "No command provided."

        require_sudo = command.startswith("sudo")
        if require_sudo:
            if not self.sudo_password:
                await self._get_sudo_password()
            if not self.sudo_password:
                return None
            command = f"echo {self.sudo_password} | sudo -S {command[5:]}"

        proc = await self._start_subprocess(command)
        if proc is None:
            return "Error: Command did not produce valid output or is not interactive."

        return await self._process_command_output(proc, command)

    async def _get_sudo_password(self):
        """
        Prompts the user for a sudo password if not already provided.
        Validates the password before storing it.
        """
        if self.ui and hasattr(self.ui, 'pswd') and self.ui.pswd:
            self.sudo_password = self.ui.pswd
        else:
            self.sudo_password = await self._get_user_input("\nEnter sudo password: ", is_password=True)
            if self.sudo_password:
                valid = await self._validate_sudo_password(self.sudo_password)
                if valid:
                    if self.ui:
                        self.ui.pswd = self.sudo_password
                    return self.sudo_password
                else:
                    if self.ui:
                        self.ui.buffer.put("\nWrong password")
                        self.ui.pswd = None
                    self.sudo_password = None
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
        proc = await self._start_subprocess(command)
        _, stderr = await proc.communicate()
        if proc.returncode == 0:
            return True 
        else:
            print(f"Error: {stderr.decode('utf-8', errors='ignore')}")
            return False

    async def _start_subprocess(self, command):
        """
        Starts an asynchronous subprocess to execute a command.
        
        Args:
            command (str): The command to execute.
        
        Returns:
            subprocess.Process: The subprocess object.
        """
        return await asyncio.create_subprocess_shell(
            command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )


    async def _process_command_output(self, proc, command):
        """
        Processes the output of a running command.
        
        Args:
            proc (subprocess.Process): The running subprocess.
            command (str): The executed command.
        
        Returns:
            str: The processed command output.
        """
        output_lines = []
        monitor_task = asyncio.create_task(self._monitor_execution(proc))

        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode("utf-8", errors="ignore").strip()

                # Attempt to extract meaningful text even if the output contains non-text data
                extracted_text = self._extract_meaningful_text(decoded_line)
                if extracted_text:
                    output_lines.append(extracted_text)

                if self._should_handle_prompt(decoded_line):
                    await self._handle_prompt(proc, decoded_line)
        except asyncio.CancelledError:
            proc.terminate()
            await proc.wait()
            return "\n".join(output_lines)
        finally:
            monitor_task.cancel()

        # Check if any output was received
        if not output_lines:
            output_lines.append("No output received. Command may require user interaction or is piped.")

        output, error = await proc.communicate()
        return await self._finalize_command_output(proc, command, output_lines, output, error)

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
                await self._print_message("\nTerminating command execution...")
                proc.terminate()
                break

    async def _finalize_command_output(self, proc, command, output_lines, output, error):
        """
        Processes the final output of a command execution, including error handling 
        and history storage. Truncates output if it exceeds the maximum length.
        
        Args:
            proc (asyncio.subprocess.Process): The completed process.
            command (str): The executed command.
            output_lines (list): Collected output lines.
            output (bytes): Standard output from the process.
            error (bytes): Standard error from the process.
        
        Returns:
            str: The final output or an error message if the command failed.
        """
        
        additional_output = output.decode("utf-8", errors="ignore").strip() if output else ""
        output_str = "\n".join(output_lines)
        if additional_output:
            output_str += "\n" + additional_output

        error_str = error.decode("utf-8", errors="ignore").strip() if error else ""
        
        # Truncate output if it's too big
        if len(output_str) > self.max_output_length:
            output_str = output_str[:self.max_output_length] + "\n[Output truncated]"
        
        self.history.append({"command": command, "output": output_str, "error": error_str})
        self._clear_sudo_password()

        return output_str if proc.returncode == 0 else f"Error: {error_str}"

    def _clear_sudo_password(self):
        """
        Clears the stored sudo password securely by overwriting it before setting 
        it to None.
        """
        self.sudo_password = secrets.token_urlsafe(32)
        self.sudo_password = None

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
        return any(kw in decoded_line.lower() for kw in ["[y/n]", "(yes/no)", "(y/n)"])

    async def _handle_prompt(self, proc, decoded_line):
        """
        Detects and responds to command-line prompts automatically.
        
        Args:
            proc (asyncio.subprocess.Process): The process awaiting input.
            decoded_line (str): The prompt message from the command output.
        """
        user_response = "yes"
        if sys.stdin and sys.stdin.isatty():
            user_response = await self._get_user_input(f"{decoded_line} ", is_password=False)
        if user_response.lower() in ["y", "yes"]:
            await self._print_message("\nSending 'yes'...")
            proc.stdin.write(b"yes\n")
        else:
            await self._print_message("\nSending 'no'...")
            proc.stdin.write(b"no\n")
        await proc.stdin.drain()

   
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
            '\nValidate the command and press Enter.\n(Delete and press Enter to cancel): ',
            input_text=command
        )
        
        return command if command else None 


    async def _get_user_input(self, prompt_text: str = "Enter input: ", is_password=False, input_text=""):
        if self.ui is not None:
            return await self.ui.get_user_input(prompt_text, is_password=is_password, input_text=input_text)
        else:
            return input(prompt_text)

    async def _print_message(self, message: str):
        if self.ui is not None:
            await self.ui.fancy_print(message)
        else:
            print(message)

