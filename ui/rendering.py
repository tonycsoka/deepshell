import asyncio
import re
import shutil

class MarkdownParser:
    def __init__(self, chat_app):
        self.chat_app = chat_app
        self.in_code_block = False
        self.in_bold = False
        self.in_italic = False
        self.unprocessed = ""
        self.accumulated_text = ""
        self.char_count = 0
        self.line_accumulated = ""
        self.last_printed_text = ""
        self.open_code_block = False

    def get_terminal_width(self):
        return shutil.get_terminal_size().columns

    async def process_markdown(self):
        while True:
            chunk = await self.chat_app.buffer.get()
            if chunk is None:
                break

            self.unprocessed += chunk
            self.accumulated_text += self._convert_markup()

            if self.open_code_block and not self.in_code_block:
                self.accumulated_text += "\n```"
                self.open_code_block = False

            terminal_width = self.get_terminal_width()
            lines = self.accumulated_text.splitlines()

            if len(lines[-1]) > terminal_width - 4:
                excess_chars = len(lines[-1]) - (terminal_width - 4)
                self.line_accumulated = lines[-1][:-excess_chars]
                self.accumulated_text = '\n'.join(lines[:-1]) + '\n' + self.line_accumulated
                self.char_count = len(self.line_accumulated)
            else:
                self.char_count = len(lines[-1])

            if self.accumulated_text != self.last_printed_text:
                self.chat_app.rich_log_widget.clear()
                self.chat_app.rich_log_widget.write(self.accumulated_text)
                self.chat_app.rich_log_widget.scroll_end()
                self.last_printed_text = self.accumulated_text

            await asyncio.sleep(0.01)

    def _convert_markup(self):
        text = self.unprocessed
        self.unprocessed = ""

        text = re.sub(r"\n?-{3,}\n?", "\n", text)
        text = re.sub(r"^#(?![a-zA-Z]+\s)(.*?)$", r"[bold]\1[/bold]", text, flags=re.MULTILINE)
        text = re.sub(r"^### (.*?)$", r"[bold]\1[/bold]", text, flags=re.MULTILINE)
        text = re.sub(r"^## (.*?)$", r"[bold]\1[/bold]", text, flags=re.MULTILINE)
        text = re.sub(r"^# (.*?)$", r"[bold]\1[/bold]", text, flags=re.MULTILINE)

        while "```" in text:
            if self.in_code_block:
                text = text.replace("```", "[/code]", 1)
                self.in_code_block = False
                self.open_code_block = False
            else:
                text = text.replace("```", "[code]", 1)
                self.in_code_block = True
                self.open_code_block = True

        text = re.sub(r"(?<!`)`(?!`)(.*?)`(?!`)", r"[code]\1[/code]", text)

        while "**" in text:
            if self.in_bold:
                text = text.replace("**", "[/bold]", 1)
                self.in_bold = False
            else:
                text = text.replace("**", "[bold]", 1)
                self.in_bold = True

        while "*" in text:
            if self.in_italic:
                text = text.replace("*", "[/italic]", 1)
                self.in_italic = False
            else:
                text = text.replace("*", "[italic]", 1)
                self.in_italic = True

        return text

  
