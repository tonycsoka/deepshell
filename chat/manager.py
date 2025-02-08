import sys
from chat.user_input import get_user_input
from chat.input_handler import CommandProcessor 
from chat.streamer import rich_print

async def start_chat(ollama_client, user_input=None):
    command_processor = CommandProcessor(ollama_client)
   
    if not sys.stdout.isatty():
        ollama_client.render_output = False
        response = await ollama_client.chat(user_input)
        print(response)
        return

    await rich_print(f"Chat with  model: {ollama_client.model} in {ollama_client.config_name} mode. Type 'exit' to quit.\n")

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
        
        response = await ollama_client.chat(user_input)
        user_input = None
    
