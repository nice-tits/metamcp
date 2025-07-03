# image-generator MCP Server

An mcp server that generates images based on image prompts

This is a TypeScript-based MCP server that implements image generation using **OPENAI**'s `dall-e-3` image generation model.

## Features

### Tools
- `generate_image` - Generate an image for given prompt
  - Takes `prompt` as a required parameter
  - Takes `imageName` as a required parameter to save the generated image in a `generated-images` directory on your desktop

## Development

Install dependencies:
```bash
npm install
```

Build the server:
```bash
npm run build
```

For development with auto-rebuild:
```bash
npm run watch
```

## Installation

To use with Claude Desktop, add the server config:

On MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "command": "image-generator",
      "env": {
        "OPENAI_API_KEY": "<your-openai-api-key>"
    }
  }
}
```
Make sure to replace `<your-openai-api-key>` with your actual **OPENAI** Api Key.

### Debugging

Since MCP servers communicate over stdio, debugging can be challenging. We recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector), which is available as a package script:

```bash
npm run inspector
```

The Inspector will provide a URL to access debugging tools in your browser.
