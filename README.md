# DeepSeek-Shell

DeepSeek-Shell is a command-line tool for interacting with AI models via the Ollama API. It supports both user input through prompts and content from files or piped input. Alternative to Shell-GPT that works with locally running deepseek-r1 models.

### Features

* Terminal-based interface
* Real-time chat with the AI model
* Filtering out thinking process by default
* Streamed responses with markdown formatting
* File and Pipe support


### Requirements

* Python 3.7 or higher
* ollama package for interacting with the AI with installed and accessible model


### Installation

**You can install the necessary dependencies using pip:**

```
pip install ollama rich

```

If you want to access program anywhere from Linux terminal you can install it

```
chmod +x deepshell

./deepshell --install

```
This creates a symlink to deepshell in ~/.local/bin, making it globally accessible

### Usage

**Running the Chat**

To run the chat mode, simply execute the script:

```
deepshell

```
or if you haven't installed it:

```
python3 main.py

```

**Command-Line Arguments**

specify additional arguments:

* --model: The AI model to use (defaults to DEFAULT_MODEL).
* --host: The Ollama API host (defaults to DEFAULT_HOST).
* --thinking: Show the AI's thinking process (useful for debugging or understanding).
* --prompt: Provide the initial message to start the conversation.
* --file: Specify a file to include in the chat.


**Pipe Support**

You can also pipe input to deepshell:

```
cat input.txt | deepshell --prompt "Analyze the content"

```
As for now, piping will not be able to start a chat session.

**File support**

You can point deepshell at a file directly:

```
deepshell --file "input.txt" --prompt "Analyze the content"

```
This will start an interactive chat session with the file content provided as context. You can continue the conversation by typing more prompts after the initial file content is processed.

**Launching with a specific model**

```
$ python deepseek --model "deepseek-r1:14b" 
Chat mode activated with model: deepseek-r1:14b. Type 'exit' to quit.
You: Hello!
AI: Hmmm... 
Hello! How can I assist you today? 😊
You:

```
### Settings

The settings for the AI model and host are located in config/settings.py

```
# config/settings.py

# Default AI model
DEFAULT_MODEL = "deepseek-r1:14b"

# Default Ollama API host
DEFAULT_HOST = "http://localhost:11434"

```
