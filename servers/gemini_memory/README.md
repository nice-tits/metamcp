# Gemini Memory MCP Server

An MCP (Model Context Protocol) server implementation that provides persistent memory capabilities for Large Language Models, specifically designed to integrate with the Gemini CLI application.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## Overview

This project implements optimal memory techniques based on comprehensive research of current approaches in the field. It provides a standardized way for Gemini to maintain persistent memory across conversations and sessions.

## Features

- **Tiered Memory Architecture**: Short-term, long-term, and archival memory tiers
- **Multiple Memory Types**: Support for conversations, knowledge, entities, and reflections
- **Semantic Search**: Retrieve memories based on semantic similarity
- **Automatic Memory Management**: Intelligent memory capture without explicit commands
- **Memory Consolidation**: Automatic consolidation of short-term memories into long-term memory
- **Memory Management**: Importance-based memory retention and forgetting
- **Gemini Integration**: Ready-to-use integration with Gemini CLI application
- **MCP Protocol Support**: Compatible with the Model Context Protocol
- **Docker Support**: Easy deployment using Docker containers

## Quick Start

### Option 1: Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/WhenMoon-afk/gemini-memory-mcp.git
cd gemini-memory-mcp

# Start with Docker Compose
docker-compose up -d
```

Configure Gemini CLI to use the containerized MCP server (see [Docker Usage Guide](docs/docker_usage.md) for details).

### Option 2: Standard Installation

1. **Prerequisites**:
   - Python 3.8-3.12
   - pip package manager

2. **Installation**:
   ```bash
   # Clone the repository
   git clone https://github.com/WhenMoon-afk/gemini-memory-mcp.git
   cd gemini-memory-mcp
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run setup script
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Gemini CLI Integration**:

   Add the following to your Gemini configuration file:

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

## Using Memory with Gemini

The Memory MCP Server enables Gemini to remember information across conversations without requiring explicit commands. 

1. **Automatic Memory**: Gemini will automatically:
   - Remember important details you share
   - Store user preferences and facts
   - Recall relevant information when needed

2. **Memory Recall**: To see what Gemini remembers, simply ask:
   - "What do you remember about me?"
   - "What do you know about my preferences?"

3. **System Prompt**: For optimal memory usage, add this to your Gemini system prompt:

   ```
   This Gemini instance has been enhanced with persistent memory capabilities.
   Gemini will automatically remember important details about you across
   conversations and recall them when relevant, without needing explicit commands.
   ```

See the [User Guide](docs/user_guide.md) for detailed usage instructions and examples.

## Documentation

- [User Guide](docs/user_guide.md)
- [Docker Usage Guide](docs/docker_usage.md)
- [Compatibility Guide](docs/compatibility.md)
- [Architecture](docs/architecture.md)
- [Gemini Integration Guide](docs/gemini_integration.md)

## Examples

The `examples` directory contains scripts demonstrating how to interact with the Memory MCP Server:

- `store_memory_example.py`: Example of storing a memory
- `retrieve_memory_example.py`: Example of retrieving memories

## Troubleshooting

If you encounter issues:

1. Check the [Compatibility Guide](docs/compatibility.md) for dependency requirements
2. Ensure your Python version is 3.8-3.12
3. For NumPy issues, use: `pip install "numpy>=1.20.0,<2.0.0"`
4. Try using Docker for simplified deployment

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.