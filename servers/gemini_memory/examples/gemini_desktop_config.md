# Gemini Cli Integration Guide

This guide explains how to integrate the Memory MCP Server with the Gemini Cli application for enhanced memory capabilities.

## Overview

The Memory MCP Server implements the Model Context Protocol (MCP) to provide Gemini with persistent memory capabilities. After setting up the server, you can configure Gemini Cli to use it for remembering information across conversations.

## Prerequisites

- Gemini Cli application installed
- Memory MCP Server installed and configured

## Configuration

### 1. Locate Gemini Cli Configuration

The Gemini Cli configuration file is typically located at:

- **Windows**: `%APPDATA%\Gemini\gemini_desktop_config.json`
- **macOS**: `~/Library/Application Support/Gemini/gemini_desktop_config.json`
- **Linux**: `~/.config/Gemini/gemini_desktop_config.json`

### 2. Add Memory MCP Server Configuration

Edit your `gemini_desktop_config.json` file to include the Memory MCP Server:

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["-m", "memory_mcp"],
      "env": {
        "MEMORY_FILE_PATH": "/path/to/your/memory.json"
      }
    }
  }
}
```

Replace `/path/to/your/memory.json` with your desired memory file location.

### 3. Optional: Configure MCP Server

You can customize the Memory MCP Server by creating a configuration file at `~/.memory_mcp/config/config.json`:

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8000,
    "debug": false
  },
  "memory": {
    "max_short_term_items": 100,
    "max_long_term_items": 1000,
    "max_archival_items": 10000,
    "consolidation_interval_hours": 24,
    "short_term_threshold": 0.3,
    "file_path": "/path/to/your/memory.json"
  },
  "embedding": {
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "dimensions": 384,
    "cache_dir": "~/.memory_mcp/cache"
  },
  "retrieval": {
    "default_top_k": 5,
    "semantic_threshold": 0.75,
    "recency_weight": 0.3,
    "importance_weight": 0.7
  }
}
```

### 4. Docker Container Option

Alternatively, you can run the Memory MCP Server as a Docker container:

```json
{
  "mcpServers": {
    "memory": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "-v", "/path/to/memory/directory:/app/memory",
        "--rm",
        "whenmoon-afk/gemini-memory-mcp"
      ],
      "env": {
        "MEMORY_FILE_PATH": "/app/memory/memory.json"
      }
    }
  }
}
```

Make sure to create the directory `/path/to/memory/directory` on your host system before running.

## Using Memory Tools in Gemini

Once configured, Gemini Cli will automatically connect to the Memory MCP Server. You can use the provided memory tools in your conversations with Gemini:

### Store Memory

To explicitly store information in memory:

```
Could you remember that my favorite color is blue?
```

Gemini will use the `store_memory` tool to save this information.

### Retrieve Memory

To recall information from memory:

```
What's my favorite color?
```

Gemini will use the `retrieve_memory` tool to search for relevant memories.

### System Prompt

For optimal memory usage, consider adding these instructions to your Gemini Cli System Prompt:

```
Follow these steps for each interaction:

1. Memory Retrieval:
   - Always begin your chat by saying only "Remembering..." and retrieve all relevant information from your knowledge graph
   - Always refer to your knowledge graph as your "memory"

2. Memory Update:
   - While conversing with the user, be attentive to any new information about the user
   - If any new information was gathered during the interaction, update your memory
```

## Troubleshooting

### Memory Server Not Starting

If the Memory MCP Server fails to start:

1. Check your Python installation and ensure all dependencies are installed
2. Verify the configuration file paths are correct
3. Check if the memory file directory exists and is writable
4. Look for error messages in the Gemini Cli logs

### Memory Not Being Stored

If Gemini is not storing memories:

1. Ensure the MCP server is running (check Gemini Cli logs)
2. Verify that your system prompt includes instructions to use memory
3. Make sure Gemini has clear information to store (be explicit)

### Memory File Corruption

If the memory file becomes corrupted:

1. Stop Gemini Cli
2. Rename the corrupted file
3. The MCP server will create a new empty memory file on next start

## Advanced Configuration

### Custom Embedding Models

You can use different embedding models by changing the `embedding.model` configuration:

```json
"embedding": {
  "model": "sentence-transformers/paraphrase-MiniLM-L6-v2",
  "dimensions": 384
}
```

### Memory Consolidation Settings

Adjust memory consolidation behavior:

```json
"memory": {
  "consolidation_interval_hours": 12,
  "importance_decay_rate": 0.02
}
```

### Retrieval Fine-Tuning

Fine-tune memory retrieval by adjusting these parameters:

```json
"retrieval": {
  "recency_weight": 0.4,
  "importance_weight": 0.6
}
```

Increase `recency_weight` to prioritize recent memories, or increase `importance_weight` to prioritize important memories.
