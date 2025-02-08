import re

class Filtering:
    def __init__(self, ollama_client):
        self.ollama_client = ollama_client
        self.thoughts_buffer = ollama_client.thoughts_buffer

    async def _filter_thoughts(self, stream):
        """
        Processes the raw stream:
         - Extracts `<think>` segments.
         - Stores thoughts in self.thoughts_buffer.
         - Yields a cleaned stream (an async generator of text chunks).
        """
        thinking = False
        partial_thought = ""
        first_chunk = True
        response = ""

        async for chunk in stream:
            message = chunk.get('message', {}).get('content', '')

            if thinking:
                partial_thought += message

            if "<think>" in message:
                thinking = True
                before_think, after_think = message.split("<think>", 1)
                response += before_think  # Add text before the thinking block
                partial_thought = after_think  # Start capturing thoughts
                continue

            if "</think>" in message:
                thinking = False
                thought_content, after_think = partial_thought.split("</think>", 1)
                self.thoughts_buffer.append(thought_content.strip())

                if self.ollama_client.show_thinking:
                    response += f"\n**AI's Thoughts:** {thought_content.strip()}\n"
                message = after_think  
                partial_thought = ""

            elif thinking:
                continue  
           
            if first_chunk and message.strip():
                message = f"\n**AI:** {message.strip()}\n"
                first_chunk = False

            response += message

        yield response


    def _extract_code(self, response, keep_formatting=True, shell=False):
        """Extracts code snippets enclosed in triple backticks.

        If `shell` is True, extracts only the first shell command and its description.
        """
        pattern = r'```(.*?)\n(.*?)```'
        
        if shell:
            
            shell_pattern = r'```bash\n(.*?)```'
            match = re.search(shell_pattern, response, re.DOTALL)
            
            if match:
                full_command = match.group(1).strip()
                lines = full_command.split("\n")
                return lines  
        else:
           
            matches = re.findall(pattern, response, re.DOTALL)
            code_snippets = []
            for match in matches:
                language, code = match
                if keep_formatting:
                    code_snippets.append(f"```{language}\n{code}```")
                else:
                    code_snippets.append(code.strip())  # Remove formatting if not kept
            return code_snippets

