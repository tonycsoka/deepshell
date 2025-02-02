from ollama_client.api_client import OllamaClient
from rich.markdown import Markdown

async def stream_chat_response(user_input, model, host, config, show_thinking, history, live):
    """
    Fetches and streams AI responses.
    """
    thinking = False
    client = OllamaClient(host)

    history.append({'role': 'user', 'content': user_input})

    response = ""
    stream = await client.chat(model=model, config=config, messages=history, stream=True)

    async for chunk in stream:
        message = chunk['message']['content']

        if not show_thinking:
            if "<think>" in message:
                thinking = True
                live.update("[bold cyan]AI:[/] Hmmm...")
                continue  
            if "</think>" in message:
                thinking = False
                continue  
            if thinking:
                continue  

        response += message
        live.update(Markdown(response))

    history.append({'role': 'assistant', 'content': response})
    return response  
