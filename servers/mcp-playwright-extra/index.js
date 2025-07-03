#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { chromium } from 'playwright-extra';
import stealth from 'puppeteer-extra-plugin-stealth';
import AdblockerPlugin from 'puppeteer-extra-plugin-adblocker';
import RecaptchaPlugin from 'puppeteer-extra-plugin-recaptcha';

// Configure plugins
chromium.use(stealth());
chromium.use(AdblockerPlugin({ blockTrackers: true }));
chromium.use(RecaptchaPlugin({
  provider: {
    id: '2captcha',
    token: 'XXXXXXX' // Optional: add your token if you have one
  },
  visualFeedback: true
}));

class PlaywrightExtraServer {
  constructor() {
    this.browser = null;
    this.pages = new Map();
    this.server = new Server(
      {
        name: 'mcp-playwright-extra',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupHandlers();
  }

  setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'launch_browser',
          description: 'Launch a new browser instance with stealth mode',
          inputSchema: {
            type: 'object',
            properties: {
              headless: {
                type: 'boolean',
                description: 'Run browser in headless mode',
                default: false
              },
              userDataDir: {
                type: 'string',
                description: 'Path to user data directory for persistent sessions'
              }
            }
          }
        },
        {
          name: 'open_page',
          description: 'Open a new page/tab in the browser',
          inputSchema: {
            type: 'object',
            properties: {
              url: {
                type: 'string',
                description: 'URL to navigate to'
              },
              pageId: {
                type: 'string',
                description: 'Unique identifier for this page',
                default: 'default'
              }
            },
            required: ['url']
          }
        },
        {
          name: 'screenshot',
          description: 'Take a screenshot of the current page',
          inputSchema: {
            type: 'object',
            properties: {
              pageId: {
                type: 'string',
                description: 'Page identifier',
                default: 'default'
              },
              fullPage: {
                type: 'boolean',
                description: 'Capture full page screenshot',
                default: false
              },
              path: {
                type: 'string',
                description: 'Path to save screenshot'
              }
            }
          }
        },
        {
          name: 'click',
          description: 'Click an element on the page',
          inputSchema: {
            type: 'object',
            properties: {
              pageId: {
                type: 'string',
                description: 'Page identifier',
                default: 'default'
              },
              selector: {
                type: 'string',
                description: 'CSS selector or text selector'
              }
            },
            required: ['selector']
          }
        },
        {
          name: 'type',
          description: 'Type text into an input field',
          inputSchema: {
            type: 'object',
            properties: {
              pageId: {
                type: 'string',
                description: 'Page identifier',
                default: 'default'
              },
              selector: {
                type: 'string',
                description: 'CSS selector for the input field'
              },
              text: {
                type: 'string',
                description: 'Text to type'
              },
              delay: {
                type: 'number',
                description: 'Delay between keystrokes in ms',
                default: 50
              }
            },
            required: ['selector', 'text']
          }
        },
        {
          name: 'wait_for',
          description: 'Wait for an element or condition',
          inputSchema: {
            type: 'object',
            properties: {
              pageId: {
                type: 'string',
                description: 'Page identifier',
                default: 'default'
              },
              selector: {
                type: 'string',
                description: 'CSS selector to wait for'
              },
              timeout: {
                type: 'number',
                description: 'Timeout in milliseconds',
                default: 30000
              }
            },
            required: ['selector']
          }
        },
        {
          name: 'get_content',
          description: 'Get the HTML content of the page',
          inputSchema: {
            type: 'object',
            properties: {
              pageId: {
                type: 'string',
                description: 'Page identifier',
                default: 'default'
              }
            }
          }
        },
        {
          name: 'evaluate',
          description: 'Execute JavaScript in the page context',
          inputSchema: {
            type: 'object',
            properties: {
              pageId: {
                type: 'string',
                description: 'Page identifier',
                default: 'default'
              },
              script: {
                type: 'string',
                description: 'JavaScript code to execute'
              }
            },
            required: ['script']
          }
        },
        {
          name: 'close_page',
          description: 'Close a specific page',
          inputSchema: {
            type: 'object',
            properties: {
              pageId: {
                type: 'string',
                description: 'Page identifier',
                default: 'default'
              }
            }
          }
        },
        {
          name: 'close_browser',
          description: 'Close the browser instance',
          inputSchema: {
            type: 'object',
            properties: {}
          }
        }
      ]
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'launch_browser':
            return await this.launchBrowser(args);
          case 'open_page':
            return await this.openPage(args);
          case 'screenshot':
            return await this.screenshot(args);
          case 'click':
            return await this.click(args);
          case 'type':
            return await this.type(args);
          case 'wait_for':
            return await this.waitFor(args);
          case 'get_content':
            return await this.getContent(args);
          case 'evaluate':
            return await this.evaluate(args);
          case 'close_page':
            return await this.closePage(args);
          case 'close_browser':
            return await this.closeBrowser();
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${error.message}`
            }
          ]
        };
      }
    });
  }

  async launchBrowser(args) {
    const options = {
      headless: args.headless ?? false,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-blink-features=AutomationControlled',
      ]
    };

    if (args.userDataDir) {
      options.userDataDir = args.userDataDir;
    }

    this.browser = await chromium.launch(options);
    
    return {
      content: [
        {
          type: 'text',
          text: 'Browser launched successfully with stealth mode enabled'
        }
      ]
    };
  }

  async openPage(args) {
    if (!this.browser) {
      throw new Error('Browser not launched. Call launch_browser first.');
    }

    const page = await this.browser.newPage();
    const pageId = args.pageId || 'default';
    this.pages.set(pageId, page);

    await page.goto(args.url, { waitUntil: 'networkidle' });

    return {
      content: [
        {
          type: 'text',
          text: `Page opened: ${args.url} (ID: ${pageId})`
        }
      ]
    };
  }

  async screenshot(args) {
    const page = this.pages.get(args.pageId || 'default');
    if (!page) {
      throw new Error('Page not found. Open a page first.');
    }

    const screenshotOptions = {
      fullPage: args.fullPage || false
    };

    if (args.path) {
      screenshotOptions.path = args.path;
      await page.screenshot(screenshotOptions);
      return {
        content: [
          {
            type: 'text',
            text: `Screenshot saved to: ${args.path}`
          }
        ]
      };
    } else {
      const buffer = await page.screenshot(screenshotOptions);
      return {
        content: [
          {
            type: 'image',
            data: buffer.toString('base64'),
            mimeType: 'image/png'
          }
        ]
      };
    }
  }

  async click(args) {
    const page = this.pages.get(args.pageId || 'default');
    if (!page) {
      throw new Error('Page not found. Open a page first.');
    }

    await page.click(args.selector);

    return {
      content: [
        {
          type: 'text',
          text: `Clicked element: ${args.selector}`
        }
      ]
    };
  }

  async type(args) {
    const page = this.pages.get(args.pageId || 'default');
    if (!page) {
      throw new Error('Page not found. Open a page first.');
    }

    await page.type(args.selector, args.text, { delay: args.delay || 50 });

    return {
      content: [
        {
          type: 'text',
          text: `Typed text into: ${args.selector}`
        }
      ]
    };
  }

  async waitFor(args) {
    const page = this.pages.get(args.pageId || 'default');
    if (!page) {
      throw new Error('Page not found. Open a page first.');
    }

    await page.waitForSelector(args.selector, { timeout: args.timeout || 30000 });

    return {
      content: [
        {
          type: 'text',
          text: `Element appeared: ${args.selector}`
        }
      ]
    };
  }

  async getContent(args) {
    const page = this.pages.get(args.pageId || 'default');
    if (!page) {
      throw new Error('Page not found. Open a page first.');
    }

    const content = await page.content();

    return {
      content: [
        {
          type: 'text',
          text: content
        }
      ]
    };
  }

  async evaluate(args) {
    const page = this.pages.get(args.pageId || 'default');
    if (!page) {
      throw new Error('Page not found. Open a page first.');
    }

    const result = await page.evaluate(args.script);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(result, null, 2)
        }
      ]
    };
  }

  async closePage(args) {
    const pageId = args.pageId || 'default';
    const page = this.pages.get(pageId);
    if (!page) {
      throw new Error('Page not found.');
    }

    await page.close();
    this.pages.delete(pageId);

    return {
      content: [
        {
          type: 'text',
          text: `Page closed: ${pageId}`
        }
      ]
    };
  }

  async closeBrowser() {
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
      this.pages.clear();
    }

    return {
      content: [
        {
          type: 'text',
          text: 'Browser closed'
        }
      ]
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('MCP Playwright Extra server running...');
  }
}

const server = new PlaywrightExtraServer();
server.run().catch(console.error);