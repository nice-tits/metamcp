#!/usr/bin/env python3
"""
Playwright MCP Server for Browser Automation
Routes browser sessions to AI Commander dashboard
"""

import asyncio
import json
from playwright.async_api import async_playwright
import websockets
from typing import Dict, Any

class PlaywrightMCPServer:
    def __init__(self):
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None
        self.dashboard_ws = None
        
    async def start(self):
        """Initialize Playwright browser"""
        self.playwright = await async_playwright().start()
        # Launch browser in non-headless mode
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
        # Connect to dashboard WebSocket
        try:
            self.dashboard_ws = await websockets.connect("ws://localhost:3001/ws/browser")
            print("✅ Connected to dashboard WebSocket")
        except Exception as e:
            print(f"⚠️  Dashboard WebSocket not available: {e}")
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "navigate":
                return await self.navigate(params.get("url"))
            elif method == "click":
                return await self.click(params.get("selector"))
            elif method == "type":
                return await self.type_text(params.get("selector"), params.get("text"))
            elif method == "screenshot":
                return await self.screenshot()
            elif method == "extract_text":
                return await self.extract_text(params.get("selector"))
            elif method == "get_url":
                return {"url": self.page.url if self.page else None}
            else:
                return {"error": f"Unknown method: {method}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to URL"""
        if not self.page:
            return {"error": "Browser not initialized"}
        
        await self.page.goto(url)
        await self.send_to_dashboard({
            "type": "navigation",
            "url": url,
            "title": await self.page.title()
        })
        
        return {
            "success": True,
            "url": url,
            "title": await self.page.title()
        }
    
    async def click(self, selector: str) -> Dict[str, Any]:
        """Click element"""
        if not self.page:
            return {"error": "Browser not initialized"}
        
        await self.page.click(selector)
        return {"success": True, "action": "click", "selector": selector}
    
    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into element"""
        if not self.page:
            return {"error": "Browser not initialized"}
        
        await self.page.fill(selector, text)
        return {"success": True, "action": "type", "selector": selector, "text": text}
    
    async def screenshot(self) -> Dict[str, Any]:
        """Take screenshot"""
        if not self.page:
            return {"error": "Browser not initialized"}
        
        screenshot_bytes = await self.page.screenshot()
        # Save screenshot and return path
        screenshot_path = f"/tmp/screenshot_{int(asyncio.get_event_loop().time())}.png"
        with open(screenshot_path, "wb") as f:
            f.write(screenshot_bytes)
        
        await self.send_to_dashboard({
            "type": "screenshot",
            "path": screenshot_path
        })
        
        return {"success": True, "screenshot_path": screenshot_path}
    
    async def extract_text(self, selector: str = None) -> Dict[str, Any]:
        """Extract text from page or element"""
        if not self.page:
            return {"error": "Browser not initialized"}
        
        if selector:
            text = await self.page.text_content(selector)
        else:
            text = await self.page.text_content("body")
        
        return {"success": True, "text": text}
    
    async def send_to_dashboard(self, data: Dict[str, Any]):
        """Send data to dashboard WebSocket"""
        if self.dashboard_ws:
            try:
                await self.dashboard_ws.send(json.dumps(data))
            except Exception as e:
                print(f"Failed to send to dashboard: {e}")
    
    async def close(self):
        """Clean up resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        if self.dashboard_ws:
            await self.dashboard_ws.close()

# MCP Server implementation
async def main():
    server = PlaywrightMCPServer()
    await server.start()
    
    print("🌐 Playwright MCP Server started")
    print("Browser opened in non-headless mode")
    print("Waiting for commands...")
    
    try:
        while True:
            # In a real MCP implementation, this would listen for MCP protocol messages
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        await server.close()

if __name__ == "__main__":
    asyncio.run(main())