import asyncio
import itertools
from rich.markdown import Markdown
from rich.live import Live
from rich.console import Console

console = Console()

async def rich_print(content):
    """
    Custom print function that handles both live-streaming (async generator) 
    and regular string output using Rich.
    """
    if hasattr(content, "__aiter__"): 
        displayed_text = ""
        with Live("", console=console, refresh_per_second=10) as live:
            async for chunk in content:
                if chunk.strip():
                    for char in chunk: 
                        displayed_text += char
                        live.update(Markdown(displayed_text), refresh=True)
                        await asyncio.sleep(0.01)
    else:
        displayed_text = ""
        with Live("", console=console, refresh_per_second=10) as live:
            for char in content:  
                displayed_text += char
                live.update(Markdown(displayed_text), refresh=True)
                await asyncio.sleep(0.01)


async def thinking_animation():
    """
    Function that shows a 'thinking' animation while waiting for the response.
    Loops the animation until raw stream starts.
    """
    thinking_animation = itertools.cycle([".  ", ".. ", "...", "   "])
    thinking_message = "**AI is thinking** "
    
    with Live("", console=console, refresh_per_second=10) as live:
        while True: 
            live.update(Markdown(thinking_message + next(thinking_animation)), refresh=True)
            await asyncio.sleep(0.3)
