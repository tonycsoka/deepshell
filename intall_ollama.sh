#!/bin/bash
set -e

# Ensure we source the profile (if necessary)
if [ -f ~/.bash_profile ]; then
  source ~/.bash_profile
fi

# Define expected binary locations.
OLLAMA_LIB="/usr/local/lib/ollama"
OLLAMA_BIN="/usr/local/bin"
export PATH="$OLLAMA_BIN:$OLLAMA_LIB:$PATH"

# Debugging: print PATH.
echo "Using PATH: $PATH"

# Try to locate Ollama.
if command -v ollama &> /dev/null; then
  OLLAMA=$(command -v ollama)
elif [ -x "$OLLAMA_LIB/ollama" ]; then
  OLLAMA="$OLLAMA_LIB/ollama"
else
  echo "Ollama not found in expected locations. Installing..."
  curl -fsSL https://ollama.com/install.sh | sh
  export PATH="$OLLAMA_BIN:$OLLAMA_LIB:$PATH"
  if command -v ollama &> /dev/null; then
    OLLAMA=$(command -v ollama)
  elif [ -x "$OLLAMA_LIB/ollama" ]; then
    OLLAMA="$OLLAMA_LIB/ollama"
  else
    echo "Error: Ollama installation failed or binary not found."
    exit 1
  fi
fi

echo "Using Ollama binary at: $OLLAMA"
$OLLAMA -v

echo "Ollama is installed. Version: $($OLLAMA -v)"

# Extract unique models from config/settings.py
MODELS=$(grep -E "^[A-Z_]+_MODEL\s*=" config/settings.py | sed 's/.*= *"\(.*\)".*/\1/' | sort -u)
echo "Extracted unique models:"
echo "$MODELS"

# Iterate over each model and pull it if not present.
while IFS= read -r model; do
  echo "Checking for model: $model"
  if ! $OLLAMA list | grep -q "$model"; then
    echo "Model '$model' not found. Pulling..."
    $OLLAMA pull "$model"
  else
    echo "Model '$model' is already available."
  fi
done <<EOF
$MODELS
EOF

# Start the Ollama server.
echo "Starting Ollama server..."
$OLLAMA serve





