import sys
import asyncio
import secrets
import string

class CommandExecutor:
    def __init__(self, ui=None, monitor_interval=5, max_output_length=1000, output_validation=True):
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
        if command:
            confirmed_command = await self.confirm_execute_command(command)
            if confirmed_command:
                return await self.execute_command(confirmed_command)
        else:
            await self._print_message("No command specified.")

    async def execute_command(self, command):
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
        command = f"echo {sudo_password} | sudo -S -v"
        proc = await self._start_subprocess(command)
        _, stderr = await proc.communicate()
        if proc.returncode == 0:
            return True 
        else:
            print(f"Error: {stderr.decode('utf-8', errors='ignore')}")
            return False

    async def _start_subprocess(self, command):
        return await asyncio.create_subprocess_shell(
            command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    async def _process_command_output(self, proc, command):
        output_lines = []
        monitor_task = asyncio.create_task(self._monitor_execution(proc))
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode("utf-8", errors="ignore").strip()

                if self.output_validation and not self._is_text(decoded_line):
                    monitor_task.cancel()
                    return "Error: Command output contains non-text data."
                
                output_lines.append(decoded_line)

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

    async def _monitor_execution(self, proc):
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
        self.sudo_password = secrets.token_urlsafe(32)
        self.sudo_password = None

    def _is_text(self, data):
        if not data or "\x00" in data:
            return False
        printable_ratio = sum(c in string.printable for c in data) / len(data)
        if printable_ratio < 0.9 or any(c in "\x07\x1b" for c in data):
            return False
        return True

    def _should_handle_prompt(self, decoded_line):
        return any(kw in decoded_line.lower() for kw in ["[y/n]", "(yes/no)", "(y/n)"])

    async def _handle_prompt(self, proc, decoded_line):
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
        await self._print_message(f"\nCommand to be executed: `{command}`")
        while True:
            choice = await self._get_user_input("\n(E)xecute / (M)odify / (C)ancel: ")
            if choice:
                choice = choice.strip().lower()
            if choice in ("execute", "e"):
                return command  
            elif choice in ("modify", "m"):
                command = await self._get_user_input("\nModify command: ", input_text=command)
                return command 
            elif choice in ("cancel", "c"):
                await self._print_message("\nCommand execution canceled.")
                return None  
            else:
                await self._print_message("\nInvalid choice. Please select Execute (E), Modify (M), or Cancel (C).")

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

