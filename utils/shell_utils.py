import asyncio
import sys

class CommandExecutor:
    def __init__(self, ui=None):
        self.history = []
        self.ui = ui


    async def start(self, command=None):
        """Runs either interactive mode or a single command execution."""
        if command:
            confirmed_command = await self.confirm_execute_command(command)
            if confirmed_command:
                return await self.execute_command(confirmed_command)
        else:
            await self._print_message("No command specified.")

    async def execute_command(self, command, sudo_password=None):
        """Executes a command asynchronously, handling user prompts and long-running processes."""
        if not command:
            return "No command provided."

        require_sudo = command.startswith("sudo")
        if require_sudo and not sudo_password:
            sudo_password = await self._get_user_input("\n\nEnter password: ", is_password=True)
            command = f"echo {sudo_password} | sudo -S {command[5:]}"

        proc = await asyncio.create_subprocess_shell(
            command,
            stdin=asyncio.subprocess.PIPE,  # Allow sending input to the process
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        if proc.stdout is None or proc.stdin is None:
            return "Error: Command did not produce valid output or is not interactive."

        output_lines = []
        
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break  # End of output

                decoded_line = line.decode("utf-8", errors="ignore").strip()
                output_lines.append(decoded_line)
           
                if any(kw in decoded_line.lower() for kw in ["[y/n]", "(yes/no)", "(y/n)"]):
                    user_response = "yes"  
                    if sys.stdin and sys.stdin.isatty():
                        user_response = await self._get_user_input(f"{decoded_line} ", is_password=False)

                    if user_response.lower() in ["y", "yes"]:
                        await self._print_message("\n\nSending 'yes'...")
                        proc.stdin.write(b"yes\n")
                    else:
                        await self._print_message("\n\nSending 'no'...")
                        proc.stdin.write(b"no\n")

                    await proc.stdin.drain()

        except asyncio.CancelledError:
            proc.terminate()
            await proc.wait()
            return "\n".join(output_lines)

        output, error = await proc.communicate()
        output_str = "\n".join(output_lines) + "\n" + (output.decode("utf-8", errors="ignore").strip() if output else "")
        error_str = error.decode("utf-8", errors="ignore").strip() if error else ""

        self.history.append({"command": command, "output": output_str, "error": error_str})

        return output_str if proc.returncode == 0 else f"Error: {error_str}"

    async def confirm_execute_command(self, command):
        """Prompts the user to execute, modify, or cancel a command."""
        await self._print_message(f"\n\n**System:** Command to be executed: `{command}`")

        while True:
            choice = await self._get_user_input("\n\n(E)xecute / (M)odify / (C)ancel: ")
            if choice:
                choice = choice.strip().lower()

            if choice in ("execute", "e"):
                return command  

            elif choice in ("modify", "m"):
                if command:
                    command = await self._get_user_input("\n\nModify command: ",input_text = command)
                    return command 

            elif choice in ("cancel", "c"):
                await self._print_message("\n\n**System:** Command execution canceled.")
                return None  

            else:
                await self._print_message("\n\n**System:** Invalid choice. Please select Execute (E), Modify (M), or Cancel (C).")

    async def _get_user_input(self, prompt_text: str = "Enter input: ", is_password=False,input_text = ""):
        """Get user input asynchronously, either through UI or terminal."""
        if self.ui is not None:
            return await self.ui.get_user_input(prompt_text, is_password=is_password, input_text=input_text)
        else:
            # Fallback to classic terminal input
            return input(prompt_text)

    async def _print_message(self, message: str):
        """Print messages either through UI or terminal."""
        if self.ui is not None:
            await self.ui.fancy_print(message)
        else:
            print(message)

