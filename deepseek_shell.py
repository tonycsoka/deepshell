import argparse
import readline
import asyncio
from ollama import AsyncClient
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live

console = Console()

async def fetch_stream(user_input, model, host, show_thinking, history, live):
    """
    Fetch the response stream and update the UI in real-time.
    """
    thinking = False
    client = AsyncClient(host=host)  # Use specified host

    # Append user message to history
    history.append({'role': 'user', 'content': user_input})

    response = ""

    # Await coroutine properly
    stream = await client.chat(model=model, messages=history, stream=True)

    async for chunk in stream:
        message = chunk['message']['content']

        if not show_thinking:
            if "<think>" in message:
                thinking = True
                live.update("[bold cyan]AI:[/] Hmmm...")
                continue  # Skip <think> tag itself
            if "</think>" in message:
                thinking = False
                continue  # Skip </think> tag itself
            if thinking:
                continue  # Skip text inside <think> tags

        # Update the live stream with the new chunk of text
        response += message
        live.update(Markdown(response))  # Update the live stream with the new content

    # Append AI response to history
    history.append({'role': 'assistant', 'content': response})

    return response  # Return full response

async def chat_mode(model, host, show_thinking):
    print(f"Chat mode activated with model: {model} on {host}). Type 'exit' to quit.\n")

    history = []  # Stores conversation history

    while True:
        try:
            user_input = input("You: ")
        except KeyboardInterrupt:
            print("\nExiting chat.")
            break

        if user_input.lower() == 'exit':
            break

        readline.add_history(user_input)

        with Live(console=console, refresh_per_second=30, vertical_overflow="ellipsis") as live:
            response = await fetch_stream(user_input, model,host, show_thinking, history, live)
            live.update(Markdown(response))  # Final full response update

        print()  # Ensure clean newline after response

async def main():
    parser = argparse.ArgumentParser(description="Ollama Chat Mode")
    parser.add_argument("--model", type=str, default="deepseek-r1:14b", help="Specify the AI model")
    parser.add_argument("--host", type=str, default="http://localhost:11434", help="Specify the Ollama API host")
    parser.add_argument("--thinking", action="store_true", help="Show thinking sections")
    args = parser.parse_args()

    await chat_mode(model=args.model, host=args.host, show_thinking=args.thinking)

if __name__ == "__main__":
    asyncio.run(main())
