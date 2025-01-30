# Ollama Chat Mode with Real-Time Stream

This is a Python-based chat mode interface that interacts with an AI model using the Ollama API. The chat interface fetches real-time responses, filtering out thinking part and displays them in the terminal using the rich library for live streaming. It is a simple alternative for Shell-GPT that works with locally running deepseek-r1 models.

### Features

* Real-time chat with the AI model
* Streamed responses with markdown formatting
* Option to display thinking status while waiting for responses
* Conversation history tracking
* Terminal-based interface

### Requirements

* Python 3.7 or higher
* ollama package for interacting with the AI
* rich package for live updating and markdown rendering

**You can install the necessary dependencies using pip:**

```
pip install ollama rich
```

### Usage

**Command-Line Arguments**

* --model `<model>`: Specify which AI model to use (default is deepseek-r1:14b).
* --thinking: If enabled, shows thinking sections where the model is processing.

**Running the Chat**

To run the chat mode, simply execute the script:

```
python ollama_wrapper.py
```

For custom model selection and thinking display, use:

```
python ollama_wrapper.py --model 
```

**Example**

```
$ python ollama_wrapper.py --model deepseek-r1:14b 
Chat mode activated with model: deepseek-r1:14b. Type 'exit' to quit.
You: Hello!
AI: Hmmm... 
Hello! How can I assist you today? 😊
You:
```
