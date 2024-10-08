#!/bin/bash

echo "Starting Ollama..."
ollama serve &

echo "Waiting for Ollama to be ready..."
while ! ollama list >/dev/null 2>&1; do
    sleep 1
done
echo "Ollama is ready."

if [ "${OLLAMA_LOAD_MODEL}" = "false" ]; then
    echo "OLLAMA_LOAD_MODEL is set to false. Skipping model load."
elif ! ollama list | grep -q "^${OLLAMA_LOAD_MODEL}[: ]"; then
    echo "Pulling ${OLLAMA_LOAD_MODEL} model..."
    ollama pull ${OLLAMA_LOAD_MODEL}
    echo "llama3 model pulled successfully."
else
    echo "llama3 model is already present."
fi
