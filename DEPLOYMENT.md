# 🚀 AWS EC2 Deployment Guide

Complete step-by-step guide to deploy the **Agent Orchestration System (AOS)** on an AWS EC2 Instance using Docker & Docker Compose.

---

## 📋 Recommended EC2 Instance Requirements
- **Instance Type:** `t3.medium` or `t3.large` (Minimum 2 vCPUs, 4GB RAM required for ChromaDB vector embeddings)
- **OS:** Ubuntu 22.04 LTS or Ubuntu 24.04 LTS
- **Storage:** 20 GB GP3 EBS Storage

---

## 🔒 1. AWS Security Group Configuration (Inbound Rules)

Ensure your EC2 Instance Security Group has the following **Inbound Rules**:

| Type | Protocol | Port Range | Source | Description |
| :--- | :--- | :--- | :--- | :--- |
| **SSH** | TCP | `22` | My IP / Anywhere | For SSH terminal access |
| **Custom TCP** | TCP | `8502` | Anywhere (`0.0.0.0/0`) | For Streamlit Web Dashboard (Port 8502) |
| **HTTP** | TCP | `80` | Anywhere (`0.0.0.0/0`) | If using Nginx reverse proxy |
| **HTTPS** | TCP | `443` | Anywhere (`0.0.0.0/0`) | If using SSL/TLS certificate |

> **Note:** If Port 8501 is already occupied on your EC2 instance by another application, this project is configured by default to run on **Port 8502**. You can change the port anytime by editing `HOST_PORT` in your `.env` file.

---

## 💻 2. Step-by-Step EC2 Deployment

### Step A: Connect to your EC2 Instance via SSH
```bash
ssh -i "your-key.pem" ubuntu@YOUR_EC2_PUBLIC_IP
```

### Step B: Clone the Repository
```bash
git clone https://github.com/divyyadav007/Agent-Orchestration-System-with-Tool-Use-Memory-and-Human-in-the-Loop.git
cd Agent-Orchestration-System-with-Tool-Use-Memory-and-Human-in-the-Loop
```

### Step C: Configure `.env` File
Create and edit your `.env` file on the EC2 server:
```bash
cp .env.example .env
nano .env
```
Fill in your production API keys and host port:
```ini
GROQ_API_KEY="gsk_..."
TAVILY_API_KEY="tvly-..."
HOST_PORT=8502
LLM_MODEL="llama-3.1-8b-instant"
```

### Step D: Run One-Click Deployment Script
Make the deployment script executable and run it:
```bash
chmod +x deploy_ec2.sh
./deploy_ec2.sh
```

---

## 🌐 3. Accessing the Application

Once container startup completes, open your browser and navigate to:
```text
http://YOUR_EC2_PUBLIC_IP:8502
```

---

## 🔧 Useful Commands on EC2

- **View Live Application Logs:**
  ```bash
  docker-compose logs -f streamlit-ui
  ```
- **Restart Services:**
  ```bash
  docker-compose restart
  ```
- **Stop All Containers:**
  ```bash
  docker-compose down
  ```
- **Check Container Status:**
  ```bash
  docker ps
  ```
