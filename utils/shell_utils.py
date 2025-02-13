import asyncio

class CommandExecutor:
    def __init__(self, ui=None):
        self.history = []
        self.ui = ui

    async def execute_command(self, command, sudo_password=None):
        """Executes a command asynchronously, handling long-running processes."""
        if not command:
            return "No command provided."

        require_sudo = command.startswith("sudo")
        if require_sudo and not sudo_password:
            sudo_password = await self._get_user_input("Enter password: ", is_password=True)
            command = f"echo {sudo_password} | sudo -S {command[5:]}"

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        if proc.stdout is None:
            raise ValueError("stdout is None, the process may not have started correctly.")

        output_lines = []
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode("utf-8", errors="ignore").strip()
                output_lines.append(decoded_line)
                await self._print_message(decoded_line)  # Real-time output

        except asyncio.CancelledError:
            proc.terminate()
            await proc.wait()
            return "\n".join(output_lines)

        output, error = await proc.communicate()
        output_str = "\n".join(output_lines) + "\n" + output.decode("utf-8", errors="ignore").strip()
        error_str = error.decode("utf-8", errors="ignore").strip()

        self.history.append({"command": command, "output": output_str, "error": error_str})

        return output_str if proc.returncode == 0 else f"Error: {error_str}"

    async def interactive_mode(self):
        """Runs an interactive shell session and returns full log on exit."""
        await self._print_message("Interactive mode: Type 'exit' to finish. Press Ctrl+C to force exit.")

        try:
            while True:
                user_input = await self._get_user_input("Command: ")

                if user_input.lower() == "exit":
                    await self._print_message("Exiting interactive mode.")
                    return "\n".join(f"{cmd['command']} -> {cmd['output']}" for cmd in self.history)

                output = await self.execute_command(user_input)
                await self._print_message(output)

        except KeyboardInterrupt:
            await self._print_message("\nForce exiting interactive mode.")
            return "\n".join(f"{cmd['command']} -> {cmd['output']}" for cmd in self.history)

    async def start(self, command=None, interactive=False):
        """Runs either interactive mode or a single command execution."""
        if interactive:
            return await self.interactive_mode()
        elif command:
            confirmed_command = await self.confirm_execute_command(command)
            if confirmed_command:
                return await self.execute_command(confirmed_command)
        else:
            await self._print_message("No command specified.")

    async def confirm_execute_command(self, command):
        """Prompts the user to execute, modify, or cancel a command."""
        await self._print_message(f"\n**System:** Command to be executed: `{command}`")

        while True:
            choice = await self._get_user_input("\n(E)xecute / (M)odify / (C)ancel: ")
            if choice:
                choice = choice.strip().lower()

            if choice in ("execute", "e"):
                return command  # Execute the command as-is

            elif choice in ("modify", "m"):
                if command:
                    command = await self._get_user_input("\nModify command: ")
                    return command  # Return modified command

            elif choice in ("cancel", "c"):
                await self._print_message("\n**System:** Command execution canceled.")
                return None  # Cancel execution

            else:
                await self._print_message("\n**System:** Invalid choice. Please select Execute (E), Modify (M), or Cancel (C).")

    async def _get_user_input(self, prompt_text: str = "Enter input: ", is_password=False):
        """Get user input asynchronously, either through UI or terminal."""
        if self.ui is not None:
            return await self.ui.get_user_input(prompt_text, is_password=is_password)
        else:
            # Fallback to classic terminal input
            return input(prompt_text)

    async def _print_message(self, message: str):
        """Print messages either through UI or terminal."""
        if self.ui is not None:
            await self.ui.fancy_print(message)
        else:
            print(message)

