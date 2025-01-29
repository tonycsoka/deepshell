import argparse
import readline
import sys
import time
from threading import Thread
from ollama import chat
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live

console = Console()

def fetch_stream(user_input, model, show_thinking, live):
    """
    Fetch the stream of responses and update the live console smoothly.
    """
    stream = chat(
        model=model,
        messages=[{'role': 'user', 'content': user_input}],
        stream=True,
    )

    response = ""
    thinking = False

    # Stream and accumulate chunks
    for chunk in stream:
        message = chunk['message']['content']

        if not show_thinking:
            # If thinking process starts, display "Hmmmm..." unless --thinking is set
            if "<think>" in message:
                thinking = True
                live.update("[bold cyan]AI:[/] Hmmmm...")
                continue  # Skip displaying <think> immediately

            if "</think>" in message:
                thinking = False
                live.update("[bold cyan]AI:[/] ")  # Clear "Hmmmm..." message
                continue  # Skip displaying </think> immediately

            # If the message is inside a "thinking" state, ignore it
            if thinking:
                continue

        # Accumulate response and show it
        response += message
        live.update(Markdown(response))  # Show the rest of the content
        sys.stdout.flush()  # Flush to ensure output is displayed

    live.update(Markdown(response))  # Final formatted update after streaming is done

def chat_mode(model,show_thinking):
    print("Chat mode activated. Type 'exit' to quit.\n")

    history = []
    while True:
        try:
            user_input = input("You: ")
        except KeyboardInterrupt:
            print("\nExiting chat.")
            break

        if user_input.lower() == 'exit':
            break

        if user_input.strip():
            history.append(user_input)
            readline.add_history(user_input)

        # Set up the live console with a high refresh rate
        with Live(console=console, refresh_per_second=30) as live:
            # Start a background thread for fetching the stream
            stream_thread = Thread(target=fetch_stream, args=(user_input, model, show_thinking, live))
            stream_thread.start()

            # Wait for the stream thread to complete
            stream_thread.join()

        print()  # Ensure a newline after response

def main():

    model = "deepseek-r1:14b"
    show_thinking = False
    parser = argparse.ArgumentParser(description="Ollama Chat Mode")
    parser.add_argument("--thinking", action="store_true", help="Show thinking sections")
    args = parser.parse_args()
    show_thinking = args.thinking

    chat_mode(model,show_thinking)

if __name__ == "__main__":
    main()
