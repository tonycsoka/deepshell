# DeepSeek-Shell

DeepSeek-Shell is a command-line tool for interacting with AI models via the Ollama API. It supports both user input through prompts and content from files or piped input. An alternative to Shell-GPT, it works with locally running deepseek-r1 models.

### Features

- Terminal-based interface
- Real-time chat with the AI model
- Filtering out thinking process by default
- Streamed responses with markdown formatting
- Support for reading files and folders
- Advanced command handling: Open files, folders, and execute subsequent actions (e.g., `analyze the code`)

### Requirements

- Python 3.7 or higher
- Ollama package for interacting with the AI and installed models

### Installation

**Install the necessary dependencies using pip:**

```
pip install ollama rich prompt_toolkit
```

**To access the script globally from the terminal, create a symlink:**

```
chmod +x deepshell
./deepshell --install
```

This creates a symlink to `deepshell` in `~/.local/bin`, making it globally accessible.

### Usage

**Running the Chat**

To start the chat mode, simply execute the script:

```
deepshell
```

Or, if you haven't installed it:

```
python3 main.py
```

**Command-Line Arguments**

Specify additional arguments to customize the behavior:

- `--model`: The AI model to use (defaults to `DEFAULT_MODEL`).
- `--host`: The Ollama API host (defaults to `DEFAULT_HOST`).
- `--thinking`: Show the AI's thinking process (useful for debugging or understanding).
- `--prompt`: Provide the initial message to start the conversation.
- `--file`: Specify a file to include in the chat.

**Pipe Support**

You can pipe input to DeepSeek-Shell:

```
cat input.txt | deepshell --prompt "Analyze the content"
```

Currently, piping will not start a chat session, but you can use it to pass content to the tool.

**File Support**

You can specify a file directly using the `--file` flag:

```
deepshell --file "input.txt" --prompt "Analyze the content"
```

This will start an interactive chat session with the file content provided as context. You can continue the conversation by typing additional prompts after the initial file content is processed.

**Folder Support**

You can open and read a folder’s contents using the following command:

```
deepshell "open this folder"
```

This will read the contents of the current folder, and you can continue with other commands based on the folder’s structure.

**Advanced Command Parsing**

DeepSeek-Shell allows you to read files or folders and then perform additional actions in the same command. For example, you can read a file and analyze the content using the `"and"` command:

```
deepshell "open this folder and analyze the code"
```

In this case, the tool will:
1. Open and read the content of current folder, including the content of files.
2. Perform the action `"analyze the code"` on the content, which will be handled by the AI model.

Also you can naturally ask to open file or a folder while in chat:
```
$ deepshell
Chat mode activated with model: deepseek-r1:14b on http://localhost:11434. Type 'exit' to quit.

You: open LICENSE and translate it to Chinese
Reading file LICENSE:
许可协议： MIT License

版权信息： 版权所有 (c) catoni0

特此授权，免费授予任何获得本软件及其相关文档文件副本的人（“软件”），无限制地处理该软件，包括但不限于使用、复制、修改、合
并、发布、分发、 sublicense 和/或出售软件副本的权限，并允许向其提供的人员也这样做，但需遵守以下条件：
...

```

### Settings

The settings for the AI model and host are located in `config/settings.py`.

```python
# config/settings.py

# Default AI model
DEFAULT_MODEL = "deepseek-r1:14b"

# Default Ollama API host
DEFAULT_HOST = "http://localhost:11434"
```
