import asyncio
from ui.rendering import Rendering 

def printer(
        content: str,
        system: bool = False
) -> None:
    if system:
        content = "[cyan]System: [/]" + content
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(Rendering._fancy_print(content))
        else:
            asyncio.run(Rendering._fancy_print(content))
    except Exception:
       pass
