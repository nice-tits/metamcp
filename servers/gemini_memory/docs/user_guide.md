# User Guide: Gemini Memory MCP Server

This guide explains how to set up and use the Memory MCP Server with Gemini Cli for persistent memory capabilities.

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [How Memory Works](#how-memory-works)
4. [Usage Examples](#usage-examples)
5. [Advanced Configuration](#advanced-configuration)
6. [Troubleshooting](#troubleshooting)

## Installation

### Option 1: Standard Installation

1. **Prerequisites**:
   - Python 3.8-3.12
   - pip package manager

2. **Clone the repository**:
   ```bash
   git clone https://github.com/WhenMoon-afk/Gemini-memory-mcp.git
   cd Gemini-memory-mcp
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run setup script**:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

### Option 2: Docker Installation (Recommended)

See the [Docker Usage Guide](docker_usage.md) for detailed instructions on running the server in a container.

## Configuration

### Gemini Cli Integration

To integrate with Gemini Cli, add the Memory MCP Server to your Gemini configuration file:

**Location**:
- Windows: `%APPDATA%\Gemini\Gemini_Cli_config.json`
- macOS: `~/Library/Application Support/Gemini/Gemini_Cli_config.json`
- Linux: `~/.config/Gemini/Gemini_Cli_config.json`

**Configuration**:
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

### Memory System Prompt

For optimal memory usage, add these instructions to your Gemini Cli System Prompt:

```
This Gemini instance has been enhanced with persistent memory capabilities.
Gemini will automatically:
1. Remember important details about you across conversations
2. Store key facts and preferences you share
3. Recall relevant information when needed

You don't need to explicitly ask Gemini to remember or recall information.
Simply have natural conversations, and Gemini will maintain memory of important details.

To see what Gemini remembers about you, just ask "What do you remember about me?"
```

## How Memory Works

### Memory Types

The Memory MCP Server supports several types of memories:

1. **Entity Memories**: Information about people, places, things
   - User preferences and traits
   - Personal information

2. **Fact Memories**: Factual information
   - General knowledge
   - Specific facts shared by the user

3. **Conversation Memories**: Important parts of conversations
   - Significant exchanges
   - Key discussion points

4. **Reflection Memories**: Insights and patterns
   - Observations about the user
   - Recurring themes

### Memory Tiers

Memories are stored in three tiers:

1. **Short-term Memory**: Recently created or accessed memories
   - Higher importance (>0.3 by default)
   - Frequently accessed

2. **Long-term Memory**: Older, less frequently accessed memories
   - Lower importance (<0.3 by default)
   - Less frequently accessed

3. **Archived Memory**: Rarely accessed but potentially valuable memories
   - Used for long-term storage
   - Still searchable but less likely to be retrieved

## Usage Examples

### Scenario 1: Remembering User Preferences

**User**: "I really prefer to code in Python rather than JavaScript."

*Gemini will automatically store this preference without any explicit command. In future conversations, Gemini will remember this preference and tailor responses accordingly.*

**User**: "What programming language do I prefer?"

*Gemini will automatically retrieve the memory:*

**Gemini**: "You've mentioned that you prefer to code in Python rather than JavaScript."

### Scenario 2: Storing and Retrieving Personal Information

**User**: "My dog's name is Buddy, he's a golden retriever."

*Gemini will automatically store this entity information.*

**User**: "What do you remember about my pet?"

**Gemini**: "You mentioned that you have a golden retriever named Buddy."

### Scenario 3: Explicit Memory Operations (if needed)

While automatic memory is enabled by default, you can still use explicit commands:

**User**: "Please remember that my favorite color is blue."

**Gemini**: "I'll remember that your favorite color is blue."

**User**: "What's my favorite color?"

**Gemini**: "Your favorite color is blue."

## Advanced Configuration

### Custom Configuration File

Create a custom configuration file at `~/.memory_mcp/config/config.json`:

```json
{
  "auto_memory": {
    "enabled": true,
    "threshold": 0.6,
    "store_assistant_messages": false,
    "entity_extraction_enabled": true
  },
  "memory": {
    "max_short_term_items": 200,
    "max_long_term_items": 2000,
    "consolidation_interval_hours": 48
  }
}
```

### Auto-Memory Settings

- `enabled`: Enable/disable automatic memory (default: true)
- `threshold`: Minimum importance threshold for auto-storage (0.0-1.0)
- `store_assistant_messages`: Whether to store assistant messages (default: false)
- `entity_extraction_enabled`: Enable entity extraction from messages (default: true)

## Troubleshooting

### Memory Not Being Stored

1. **Check auto-memory settings**: Ensure auto_memory.enabled is true in config
2. **Check threshold**: Lower the auto_memory.threshold value (e.g., to 0.4)
3. **Use explicit commands**: You can always use explicit "please remember..." commands

### Memory Not Being Retrieved

1. **Check query relevance**: Ensure your query is related to stored memories
2. **Check memory existence**: Use the list_memories tool to see if the memory exists
3. **Try more specific queries**: Be more specific in your retrieval queries

### Server Not Starting

See the [Compatibility Guide](compatibility.md) for resolving dependency and compatibility issues.

### Additional Help

If you continue to experience issues, please:
1. Check the server logs for error messages
2. Refer to the [Compatibility Guide](compatibility.md)
3. Open an issue on GitHub with detailed information about your problem