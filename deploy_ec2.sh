#!/bin/bash
# AWS EC2 One-Click Setup Script for Agent Orchestration System (AOS)

set -e

echo "🚀 Starting AOS Setup on AWS EC2..."

# 1. Force purge conflicting Ubuntu docker-compose packages if present
sudo dpkg --purge --force-all docker-compose-v2 docker-compose 2>/dev/null || true

# 2. Install Docker & Docker Compose Plugin if not present
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    sudo apt-get update -y
    sudo apt-get install -y ca-certificates curl gnupg lsb-release
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker $USER
    echo "✅ Docker installed successfully."
fi

# 3. Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying .env.example..."
    cp .env.example .env
    echo "❗ Please edit .env file and add your GROQ_API_KEY and TAVILY_API_KEY."
fi

# Extract HOST_PORT from .env or default to 8502
PORT=$(grep -E '^HOST_PORT=' .env | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "8502")
PORT=${PORT:-8502}

# 4. Build and run Docker containers using 'docker compose' or 'docker-compose'
echo "🛠️ Building and starting container services via Docker Compose on Port ${PORT}..."
if docker compose version &> /dev/null; then
    docker compose up --build -d
else
    docker-compose up --build -d
fi

echo "🎉 Deployment Complete!"
echo "🌐 App is accessible at: http://$(curl -s ifconfig.me):${PORT}"
