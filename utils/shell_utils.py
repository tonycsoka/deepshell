import asyncio
from chat.streamer import rich_print
from chat.user_input import UIManager
class CommandExecutor:
    def __init__(self):
        self.history = []
        self.get_user_input = UIManager.get_user_input
        self.confirm_execute_command = UIManager.confirm_execute_command

    async def execute_command(self, command, sudo_password=None):
        """Executes a command asynchronously, handling long-running processes."""
        if not command:
            return "No command provided."

        require_sudo = command.startswith("sudo")
        if require_sudo and not sudo_password:
            sudo_password = await get_user_input("Enter sudo password: ", is_password=True)
            command = f"echo {sudo_password} | sudo -S {command[5:]}" 
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        output_lines = []
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode("utf-8", errors="ignore").strip()
                output_lines.append(decoded_line)
                await rich_print(decoded_line)

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
        await rich_print("Interactive mode: Type 'exit' to finish. Press Ctrl+C to force exit.")

        try:
            while True:
                user_input = await self.get_user_input("Command: ")

                if user_input.lower() == "exit":
                    await rich_print("Exiting interactive mode.")
                    return "\n".join(f"{cmd['command']} -> {cmd['output']}" for cmd in self.history)

                output = await self.execute_command(user_input)
                await rich_print(output)

        except KeyboardInterrupt:
            await rich_print("\nForce exiting interactive mode.")
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
            await rich_print("No command specified.")

