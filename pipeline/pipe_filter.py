import re
from ui.printer import printer
from utils.logger import Logger
from config.settings import Mode

logger = Logger.get_logger()

class PipeFilter:
    def __init__(self, ollama_client):
        self.ollama_client = ollama_client
        self.input_buffer = ollama_client.output_buffer  
        self.formatting = ollama_client.render_output
        self.extracted_code = None

    
    async def process_stream(self, extract_code=False, render=True):
        """Processes the input stream, handling thoughts and code differently based on config."""
        full_input = ""
        results = ""

        if extract_code:
            while True:
                message = await self.input_buffer.get()
                if message is None:
                    break
                full_input += message

            self.ollama_client.last_response = full_input
            self.extracted_code = await self.extract_code(response=full_input)
            logger.debug(f"Extracted code: {self.extracted_code}")
            return

        # --- Default behavior: Process thoughts and full response ---
        thinking = False
        thought_buffer = []
        accumulated_line = ""
        first_chunk = True

        while True:
            chunk = await self.input_buffer.get()
            if chunk is None:
                break

            output = ""
            i = 0

            while i < len(chunk):
                if chunk[i:].startswith("<think>"):
                    thinking = True
                    i += 7
                    continue
                elif chunk[i:].startswith("</think>"):
                    thinking = False
                    i += 8
                    if self.ollama_client.show_thinking:
                        output += "\n[blue]Final answer:[/] "
                    continue

                char = chunk[i]

                if thinking:
                    thought_buffer.append(char)
                    if self.ollama_client.show_thinking:
                        output += char
                else:
                    output += char

                i += 1

            if output:
                if first_chunk:
                    output = "[green]AI: [/]" + output.lstrip("\n")
                    first_chunk = False
                results += output
                accumulated_line += output

            
            if "\n" in accumulated_line:
                lines = accumulated_line.split("\n")
                for line in lines[:-1]:
                    if line.strip() and render:
                        printer(line)
                accumulated_line = lines[-1]

        if accumulated_line.strip() and render:
            printer(accumulated_line)

        self.ollama_client.last_response = results
        self.ollama_client.thoughts = thought_buffer
        logger.debug(f"PipeFilter output: {results} \nThoughts: {thought_buffer}")


    async def process_static(self, text: str, extract_code=False):
        """Processes a static string, handling thoughts and code differently based on config."""
        if extract_code:
            self.ollama_client.last_response = text
            self.extracted_code = await self.extract_code(response=text)

            if self.extracted_code:
                logger.debug(f"Extracted code: {self.extracted_code}")
                return self.extracted_code

        # Process thoughts and filter them
        thoughts = re.findall(r"<think>(.*?)</think>", text, flags=re.DOTALL)
        filtered_text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

        self.ollama_client.last_response = filtered_text
        self.ollama_client.thoughts.append(thoughts)
         

        logger.debug(f"Filtered text: {filtered_text} \nThoughts: {thoughts}")
        return filtered_text
   
    async def extract_code(self, response):
        """Extracts shell or code snippets from the response.

        - If `shell` mode:
          - Extracts the first `sh` or `bash` snippet.
          - If multiple lines exist, they are combined with `&&`.
          - If only one line exists, it's returned as is.
          - If no code block is found but the response is a single line, it's returned as a shell command.
        - Otherwise, extracts all code snippets and separates them with comments.
        """
        pattern = r'```(\w+)?\n(.*?)```'

        if self.ollama_client.mode == Mode.SHELL:
            # Match the first shell snippet (either `sh` or `bash`)
            shell_pattern = r'```(?:sh|bash)\n(.*?)```'
            match = re.search(shell_pattern, response, re.DOTALL)

            if match:
                full_command = match.group(1).strip()
                commands = [line.strip() for line in full_command.split("\n") if line.strip()]

                if len(commands) == 1:
                    return commands[0]  # Return single command directly
                return " && ".join(commands)  # Combine multiple lines with &&

            # No triple-backtick code block found, check if response is a single line
            single_line = response.strip().split("\n")
            if len(single_line) == 1 and single_line[0]:  
                return single_line[0]  # Return as a shell command

        # Extract all code snippets if not in shell mode
        matches = re.findall(pattern, response, re.DOTALL)
        code_snippets = []

        for i, match in enumerate(matches):
            language, code = match
            code = code.strip()

            if self.formatting:
                if i > 0:
                    code_snippets.append("\n# --- Next Code Block ---\n")
                code_snippets.append(f"```{language}\n{code}```")
            else:
                if i > 0:
                    code_snippets.append("\n# --- Next Code Block ---\n")
                code_snippets.append(code)

        return "\n".join(code_snippets) if code_snippets else None

