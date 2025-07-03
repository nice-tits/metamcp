# Docker Deployment

This document explains how to run the Memory MCP Server using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, for easier deployment)

## Option 1: Using Docker Compose (Recommended)

1. Clone the repository:
   ```
   git clone https://github.com/WhenMoon-afk/gemini-memory-mcp.git
   cd gemini-memory-mcp
   ```

2. Start the service:
   ```
   docker-compose up -d
   ```

3. Configure Gemini Cli to use the containerized MCP server by adding the following to your Gemini configuration file:
   ```json
   {
     "mcpServers": {
       "memory": {
         "command": "docker",
         "args": [
           "exec",
           "-i",
           "gemini-memory-mcp_memory-mcp_1",
           "python",
           "-m", 
           "memory_mcp"
         ],
         "env": {
           "MEMORY_FILE_PATH": "/app/data/memory.json"
         }
       }
     }
   }
   ```

## Option 2: Using Docker Directly

1. Build the Docker image:
   ```
   docker build -t memory-mcp .
   ```

2. Create directories for configuration and data:
   ```
   mkdir -p config data
   ```

3. Run the container:
   ```
   docker run -d \
     --name memory-mcp \
     -v "$(pwd)/config:/app/config" \
     -v "$(pwd)/data:/app/data" \
     memory-mcp
   ```

4. Configure Gemini Cli to use the containerized MCP server by adding the following to your Gemini configuration file:
   ```json
   {
     "mcpServers": {
       "memory": {
         "command": "docker",
         "args": [
           "exec",
           "-i",
           "memory-mcp",
           "python",
           "-m", 
           "memory_mcp"
         ],
         "env": {
           "MEMORY_FILE_PATH": "/app/data/memory.json"
         }
       }
     }
   }
   ```

## Using Prebuilt Images

You can also use the prebuilt Docker image from Docker Hub:

```
docker run -d \
  --name memory-mcp \
  -v "$(pwd)/config:/app/config" \
  -v "$(pwd)/data:/app/data" \
  whenmoon-afk/gemini-memory-mcp
```

## Customizing Configuration

You can customize the server configuration by creating a `config.json` file in the `config` directory before starting the container.