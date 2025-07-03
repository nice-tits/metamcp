# MCP Playwright Extra Server

This MCP server provides browser automation capabilities using Playwright with stealth plugins.

## Features

- **Stealth Mode**: Bypasses bot detection using puppeteer-extra-plugin-stealth
- **Ad Blocking**: Built-in ad blocker to improve performance
- **ReCAPTCHA Support**: Can handle ReCAPTCHA challenges (requires 2captcha token)
- **Multiple Pages**: Manage multiple browser tabs/pages
- **Screenshot Support**: Take screenshots and return them as images
- **JavaScript Execution**: Run custom JavaScript in page context

## Installation

1. Install dependencies:
```bash
cd mcp-playwright-extra
npm install
```

2. Add to Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "playwright-extra": {
      "command": "node",
      "args": ["/home/h/Downloads/ai_commander/mcp-playwright-extra/index.js"]
    }
  }
}
```

3. Restart Claude Desktop

## Available Tools

- `launch_browser`: Start a new browser instance
- `open_page`: Navigate to a URL
- `screenshot`: Take a screenshot
- `click`: Click an element
- `type`: Type text into a field
- `wait_for`: Wait for an element to appear
- `get_content`: Get page HTML
- `evaluate`: Execute JavaScript
- `close_page`: Close a specific page
- `close_browser`: Close the browser

## Usage Example

1. Launch browser: `launch_browser({"headless": false})`
2. Open page: `open_page({"url": "https://example.com"})`
3. Take screenshot: `screenshot({"fullPage": true})`
4. Click button: `click({"selector": "button.submit"})`
5. Type text: `type({"selector": "input#search", "text": "hello world"})`