import sys
from chat.user_input import UIManager
from chat.input_handler import CommandProcessor
from chat.streamer import rich_print
from utils.shell_utils import CommandExecutor

async def start_chat(ollama_client, user_input=None):
    command_processor = CommandProcessor(ollama_client)
    executor = CommandExecutor()
    get_user_input = UIManager().get_user_input
    
    if not sys.stdout.isatty():
        ollama_client.render_output = False
        response = await ollama_client.chat(user_input)
        print(response)
        return

    await rich_print(f"Chat with model: {ollama_client.model} in {ollama_client.config_name} mode. Type 'exit' to quit.\n")

    while True:
        if not user_input:
            user_input = await get_user_input()
        
        if user_input.lower() == "exit":
            await rich_print("Goodbye.")
            break
        else:
            user_input = await command_processor.handle_command(user_input)
            if not user_input:
                continue

        # Handle shell mode
        if ollama_client.config_name == "shell":
            response = await ollama_client.chat(user_input)
            await rich_print(response)
            output = await executor.start(response)
            if output:
                await rich_print(output)
            ollama_client.model = "deepseek-r1:14b"
            ollama_client.config_name = "default"
            user_input = output
            continue  

        # Handle code mode
        elif ollama_client.config_name == "code":
            response = await ollama_client.chat(user_input)
            await rich_print(response)

        # Normal chat flow
        elif ollama_client.config_name == "default":
            response = await ollama_client.chat(user_input)
            if response is None:
                continue  
           

        user_input = None  
