import asyncio
import itertools
from rich.markdown import Markdown
from rich.live import Live

async def render_response(response, client_console):
    """
    Renders the response live using Rich.
    - Displays a brief "AI is thinking" animation immediately upon function call.
    - If response is a string, simulates a live typing effect.
    - If response is an async generator, streams it dynamically.
    """
    thinking_animation = itertools.cycle([".  ", ".. ", "...", "   "])
    
    # Start showing the "AI is thinking" animation as soon as the function is called.
    with Live("", console=client_console, refresh_per_second=10, vertical_overflow="ellipsis") as live:
        displayed_text = ""
        thinking_message = "**AI is thinking** "
        # Display animation until stream starts
        while not hasattr(response, "__aiter__") and not isinstance(response, str):
            # Loop the animation while we are not yet receiving the response stream
            live.update(Markdown(thinking_message + next(thinking_animation)))
            await asyncio.sleep(0.05)
        
        if isinstance(response, str):
            # If it's a string response, we type it out live
            for char in response:
                displayed_text += char
                live.update(Markdown(displayed_text))
                await asyncio.sleep(0.02)

        elif hasattr(response, "__aiter__"):
            # If it's an async generator, we stream it
            async for chunk in response:
                text = chunk if isinstance(chunk, str) else str(chunk)
                if text.strip():
                    displayed_text += text
                    live.update(Markdown(displayed_text))
                await asyncio.sleep(0.02)

