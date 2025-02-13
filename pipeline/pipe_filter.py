import re
import asyncio

class PipeFilter:
    def __init__(self, ollama_client):
        self.ollama_client = ollama_client
        self.input_buffer = ollama_client.output_buffer  
        self.buffer = asyncio.Queue()

    async def process_stream(self):
        self.full_input = []  
        self.results = []  
        thinking = False
        thought_buffer = []

        while True:
            message = await self.input_buffer.get()
            if message is None:
                break  

            self.full_input.append(message) 
            output = [] 
            i = 0

            while i < len(message):
                if message[i:].startswith("<think>"):
                    thinking = True
                    i += 7
                    continue
                elif message[i:].startswith("</think>"):
                    thinking = False
                    i += 8  

                    if self.ollama_client.show_thinking:
                        await self.buffer.put("\nFinal answer: ")
                    continue

                if thinking:
                    thought_buffer.append(message[i])
                    if self.ollama_client.show_thinking:
                        await self.buffer.put(message[i])
                else:
                    output.append(message[i])

                i += 1

            filtered_message = "".join(output)
            if filtered_message.strip():
                await self.buffer.put(filtered_message)
                self.results.append(filtered_message)

        full_text = "".join(self.full_input)
        thoughts = re.findall(r"<think>(.*?)</think>", full_text, flags=re.DOTALL)

        self.ollama_client.last_response = "".join(self.results)
        if self.ollama_client.config_name != "shell":
            self.ollama_client.history.append({"role": "assistant", "content": self.ollama_client.last_response})

        self.ollama_client.last_thoughts = thoughts
    


    async def extract_code(self, response = None, keep_formatting=True, shell=False):
            """Extracts code snippets enclosed in triple backticks.

            - If `shell` is True, extracts only the first shell snippet (from `bash` or `sh`).
              - If multiple lines exist, they are combined using `&&`.
            - Otherwise, extracts all code snippets and separates them with comments.
            """
            pattern = r'```(\w+)?\n(.*?)```'
            if not response:
                response = self.ollama_client.last_response
            
            if shell:
                self.buffer = asyncio.Queue()
                # Match the first shell snippet (either `sh` or `bash`)
                shell_pattern = r'```(?:sh|bash)\n(.*?)```'
                match = re.search(shell_pattern, response, re.DOTALL)
                
                if match:
                    full_command = match.group(1).strip()
                    combined_command = " && ".join(line.strip() for line in full_command.split("\n") if line.strip())
                    return combined_command  # Return the first shell snippet combined with &&

            else:
                matches = re.findall(pattern, response, re.DOTALL)
                code_snippets = []

                for i, match in enumerate(matches):
                    language, code = match
                    code = code.strip()

                    if keep_formatting:
                        if i > 0:
                            code_snippets.append("\n# --- Next Code Block ---\n")
                        code_snippets.append(f"```{language}\n{code}```")
                    else:
                        if i > 0:
                            code_snippets.append("\n# --- Next Code Block ---\n")
                        code_snippets.append(code)

                return "\n".join(code_snippets) if code_snippets else None
                
