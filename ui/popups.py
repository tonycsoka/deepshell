import asyncio
from textual.app import ComposeResult
from textual.widgets import Static, RadioSet, RadioButton
from textual import events
from textual.widget import Widget

class RadiolistPopup(Widget):
    """A popup widget that displays a radio list for selection and returns the chosen value."""
    def __init__(self, title: str, text: str, options: list[tuple[str, str]], **kwargs):
        """
        :param title: The title of the popup.
        :param text: The prompt text.
        :param options: A list of (option_value, label) tuples.
        """
        super().__init__(**kwargs)
        self.title = title
        self.text = text
        self.options = options
        self.choice_future: asyncio.Future = asyncio.Future()

    def compose(self) -> ComposeResult:
        yield Static(f"[bold]{self.title}[/bold]\n{self.text}\n")
        with RadioSet(id="popup_radio_set"):
            for _, label in self.options:
                yield RadioButton(label)

    async def on_mount(self) -> None:
        self.query_one(RadioSet).focus()

    async def on_key(self, event: events.Key) -> None:
        if event.key in ("enter", "space"):
            radio_set = self.query_one(RadioSet)
            index = radio_set.pressed_index  
            if index != -1:
                choice = self.options[index][0]
                if not self.choice_future.done():
                    self.choice_future.set_result(choice)

    async def wait_for_choice(self) -> str:
        return await self.choice_future


