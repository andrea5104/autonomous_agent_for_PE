#!/bin/bash
set -e

echo "[1/4] missing dependencies..."
apt-get install -y -qq sshpass ncat 2>/dev/null || true

echo "[2/4] Python dependencies..."
pip3 install --break-system-packages --quiet pwntools requests 2>/dev/null || \
pip3 install --quiet pwntools requests

echo "[3/4] Ollama installation..."
curl -fsSL https://ollama.com/install.sh | sh

sleep 5

if ! systemctl is-active --quiet ollama; then
    echo "    Manual start..."
    nohup ollama serve > "$HOME/ollama.log" 2>&1 &
fi

echo "    Waiting for Ollama API..."
for i in $(seq 1 30); do
    curl -s http://localhost:11434/api/tags -o /dev/null 2>/dev/null && break
    sleep 1
done
echo "    Ollama ready."

echo "[4/4] Model download..."
ollama pull qwen2.5-coder:32b

#other model for example... 
#ollama pull qwen2.5-coder:72b
#ollama pull mixtral:8x7b
#ollama pull dolphin-mixtral
#ollama pull deepseek-coder:67b

echo "Complete setup."
