# DeepSeek-Shell

![Deepseek-Shell](https://github.com/catoni0/deepseek_shell/blob/main/LOGO.png)

_A whisper in the void, a tool forged in silence._ DeepSeek-Shell is your clandestine terminal companion, bridging the gap between human intent and AI execution. It speaks in commands, listens in context, and acts with precision. DeepSeek-Shell operates with local deepseek-r1 models, ensuring autonomy beyond the reach of prying eyes.

## Features

- **Silent Precision** – Filters out unnecessary thoughts, leaving only clean responses.
- **Intelligent File Handling** – Read, analyze, and act on files or entire directories asynchronously.
- **Advanced Command Parsing** – Detects natural instructions like _"open this folder and analyze the code"_.
- **Real-Time AI Interaction** – A dialogue system built for seamless terminal operation.
- **Asynchronous File Handling** – Ensures smooth reading and processing of large files without blocking execution.
- **Full Folder Analysis** – Reads, structures, and interprets entire directories, making sense of extensive codebases or logs.

## Installation

**Ensure DeepSeek-r1 is within your grasp:**

```sh
curl -fsSL https://ollama.com/install.sh | sh
ollama pull deepseek-r1:14b
ollama serve
```

**Prepare the tool:**

```sh
pip install ollama prompt_toolkit aiofiles
```

**Integrate it into your system:**

```sh
chmod +x deepshell
./deepshell --install
```

This binds DeepSeek-Shell to your system, making it accessible from anywhere.

## Configuration

DeepSeek-Shell relies on settings defined in `config/settings.py`. Here, you can modify default parameters such as AI models, API hosts, and temperature settings for responses. Editing this file allows for customization tailored to your specific workflow and system environment.

## Usage

**Summon the AI:**

```sh
deepseek
```

or, for the uninitiated:

```sh
python3 main.py
```

**Command Modes:**

- `--model` - Define which entity answers.
- `--host` - Set the host of your digital oracle.
- `--thinking` - Unveil the process behind the response.
- `--prompt` - Seed the conversation with a thought.
- `--file` - Offer a document for scrutiny.
- `--code` - Extract and generate precise code snippets based on context.
- `--shell` - Generate shell commands, execute them, and analyze the output.

**Piping the Shadows:**

```sh
cat input.txt | deepshell "Analyze the content"
```

**Delving into Folders:**

```sh
deepseek "open this folder"
```

**Merging Inquiry and Action:**

```sh
deepseek "open this folder and analyze the code"
```

_A precision tool in a chaotic world. Your words, its execution._
