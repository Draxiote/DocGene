# DocGene

[![Docker Build](https://github.com/db-agent/db-agent/actions/workflows/docker-image.yml/badge.svg)](https://github.com/db-agent/db-agent/actions/workflows/docker-image.yml)

## 🐳 Running the Model Locally with Ollama

- Works best on macOS or X86/Nvidia setups with enough GPU RAM.
- Install [Ollama](https://ollama.ai) and make sure you have [Docker](https://docker.com) configured.

### ✅ Pull the Model
```bash
curl http://localhost:11434/api/pull -d '{
  "model": "deepseek-r1"
}'

#⚡ Test the Model

curl http://localhost:11434/api/chat -d '{
  "model": "deepseek-r1",
  "messages": [{"role":"user","content":"Why is the sky blue?"}],
  "stream": false
}'
