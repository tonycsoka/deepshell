import re
import asyncio

class PipeFilter:
    def __init__(self, ollama_client):
        self.ollama_client = ollama_client
        self.input_buffer = ollama_client.output_buffer  
        self.buffer = asyncio.Queue()



    async def process_stream(self):
        thinking = False
        partial_thought = ""
        self.results = []  # Ensure results list exists

        while True:
            message = await self.input_buffer.get()
            # print(f"raw : {message}")# Fetch one item at a time

            if message is None:
                break  

            if "<think>" in message:
                thinking = True
                parts = message.split("<think>", 1)
                partial_thought = parts[1] if len(parts) > 1 else ""  # Start accumulating thoughts
                continue 

            if "</think>" in message and thinking:
                thinking = False
                parts = partial_thought.split("</think>", 1)
                thought_content = parts[0].strip()  

                if self.ollama_client.show_thinking:
                    await self.buffer.put(f"\n**AI's Thoughts:** {thought_content}\n")

                partial_thought = "" 
                message = parts[1] if len(parts) > 1 else "" 
            if not thinking and message:
                self.results.append(message)  
                await self.buffer.put(message) 

        self.ollama_client.last_response = ''.join(self.results)
        if self.ollama_client.config_name != "shell":
            self.ollama_client.history.append({"role": "assistant", "content": self.ollama_client.last_response})
        await self.buffer.put(None)


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
                
