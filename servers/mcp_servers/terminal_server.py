#!/usr/bin/env python3
"""
Terminal MCP Server for Command Execution
Routes terminal output to AI Commander dashboard
"""

import asyncio
import subprocess
import json
import os
import websockets
from typing import Dict, Any

class TerminalMCPServer:
    def __init__(self):
        self.cwd = os.path.expanduser("~")
        self.dashboard_ws = None
        self.shell_history = []
        
    async def start(self):
        """Initialize terminal server"""
        # Connect to dashboard WebSocket
        try:
            self.dashboard_ws = await websockets.connect("ws://localhost:3001/ws/terminal")
            print("✅ Connected to dashboard WebSocket")
        except Exception as e:
            print(f"⚠️  Dashboard WebSocket not available: {e}")
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "exec":
                return await self.execute_command(params.get("command"))
            elif method == "cd":
                return await self.change_directory(params.get("path"))
            elif method == "pwd":
                return {"cwd": self.cwd}
            elif method == "history":
                return {"history": self.shell_history}
            else:
                return {"error": f"Unknown method: {method}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute shell command"""
        if not command:
            return {"error": "No command provided"}
        
        # Add to history
        self.shell_history.append({
            "command": command,
            "cwd": self.cwd,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        try:
            # Execute command in current working directory
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            output = {
                "success": True,
                "command": command,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "cwd": self.cwd
            }
            
            # Send to dashboard
            await self.send_to_dashboard({
                "type": "command_output",
                **output
            })
            
            return output
            
        except subprocess.TimeoutExpired:
            error_output = {
                "success": False,
                "command": command,
                "error": "Command timeout (30s)",
                "cwd": self.cwd
            }
            
            await self.send_to_dashboard({
                "type": "command_error",
                **error_output
            })
            
            return error_output
            
        except Exception as e:
            error_output = {
                "success": False,
                "command": command,
                "error": str(e),
                "cwd": self.cwd
            }
            
            await self.send_to_dashboard({
                "type": "command_error", 
                **error_output
            })
            
            return error_output
    
    async def change_directory(self, path: str) -> Dict[str, Any]:
        """Change working directory"""
        if not path:
            path = os.path.expanduser("~")
        
        try:
            # Expand user path and resolve
            full_path = os.path.expanduser(path)
            if not os.path.isabs(full_path):
                full_path = os.path.join(self.cwd, full_path)
            
            full_path = os.path.abspath(full_path)
            
            if os.path.isdir(full_path):
                self.cwd = full_path
                
                await self.send_to_dashboard({
                    "type": "directory_change",
                    "cwd": self.cwd
                })
                
                return {"success": True, "cwd": self.cwd}
            else:
                return {"success": False, "error": f"Directory not found: {path}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_to_dashboard(self, data: Dict[str, Any]):
        """Send data to dashboard WebSocket"""
        if self.dashboard_ws:
            try:
                await self.dashboard_ws.send(json.dumps(data))
            except Exception as e:
                print(f"Failed to send to dashboard: {e}")
    
    async def close(self):
        """Clean up resources"""
        if self.dashboard_ws:
            await self.dashboard_ws.close()

# MCP Server implementation
async def main():
    server = TerminalMCPServer()
    await server.start()
    
    print("💻 Terminal MCP Server started")
    print(f"Working directory: {server.cwd}")
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