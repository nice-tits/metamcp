"""
Terminal Execution MCP Server
Provides direct terminal command execution for the AI Commander dashboard.
Agents can execute any command on the local system.
"""

import asyncio
import json
import subprocess
import sys
import os
from typing import Dict, Any, List
import websockets
from pathlib import Path
import uuid
import time
import shlex


class TerminalExecutionMCPServer:
    def __init__(self, host: str = "localhost", port: int = 8086):
        self.host = host
        self.port = port
        self.dashboard_connections = set()
        self.execution_history = []
        self.current_directory = os.getcwd()
        self.environment_vars = dict(os.environ)
        
    async def start_server(self):
        """Start the MCP server"""
        print(f"Starting Python Execution MCP Server on {self.host}:{self.port}")
        
        async def handle_client(websocket, path):
            self.dashboard_connections.add(websocket)
            try:
                await websocket.send(json.dumps({
                    "type": "connection_established",
                    "server": "python_execution",
                    "capabilities": [
                        "execute_python",
                        "install_package",
                        "list_packages",
                        "get_execution_history",
                        "clear_history",
                        "check_syntax",
                        "get_python_info"
                    ]
                }))
                
                async for message in websocket:
                    try:
                        request = json.loads(message)
                        response = await self.handle_request(request)
                        await websocket.send(json.dumps(response))
                    except json.JSONDecodeError:
                        await websocket.send(json.dumps({
                            "error": "Invalid JSON in request"
                        }))
                    except Exception as e:
                        await websocket.send(json.dumps({
                            "error": f"Request handling error: {str(e)}"
                        }))
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                self.dashboard_connections.discard(websocket)
        
        await websockets.serve(handle_client, self.host, self.port)
        print(f"Python Execution MCP Server running on ws://{self.host}:{self.port}")
        
        # Keep server running
        await asyncio.Future()
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "execute_python":
                return await self._execute_python(params)
            elif method == "install_package":
                return await self._install_package(params)
            elif method == "list_packages":
                return await self._list_packages()
            elif method == "get_execution_history":
                return await self._get_execution_history()
            elif method == "clear_history":
                return await self._clear_history()
            elif method == "check_syntax":
                return await self._check_syntax(params)
            elif method == "get_python_info":
                return await self._get_python_info()
            else:
                return {"error": f"Unknown method: {method}"}
                
        except Exception as e:
            return {"error": f"Method execution failed: {str(e)}"}
    
    async def _execute_python(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Python code in a safe environment"""
        code = params.get("code", "")
        if not code:
            return {"error": "No code provided"}
        
        # Create execution record
        execution_id = str(uuid.uuid4())
        execution_record = {
            "id": execution_id,
            "code": code,
            "timestamp": time.time(),
            "status": "running"
        }
        
        # Broadcast execution start to dashboard
        await self._broadcast_to_dashboard({
            "type": "execution_started",
            "execution": execution_record
        })
        
        try:
            # Create temporary file for execution
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            try:
                # Execute with timeout and capture output
                process = await asyncio.create_subprocess_exec(
                    sys.executable, temp_file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), 
                        timeout=self.max_execution_time
                    )
                    
                    # Decode output
                    stdout_text = stdout.decode('utf-8', errors='replace')
                    stderr_text = stderr.decode('utf-8', errors='replace')
                    
                    # Limit output size
                    if len(stdout_text) > self.max_output_size:
                        stdout_text = stdout_text[:self.max_output_size] + "\n... (output truncated)"
                    if len(stderr_text) > self.max_output_size:
                        stderr_text = stderr_text[:self.max_output_size] + "\n... (output truncated)"
                    
                    # Update execution record
                    execution_record.update({
                        "status": "completed",
                        "return_code": process.returncode,
                        "stdout": stdout_text,
                        "stderr": stderr_text,
                        "execution_time": time.time() - execution_record["timestamp"]
                    })
                    
                except asyncio.TimeoutError:
                    process.kill()
                    execution_record.update({
                        "status": "timeout",
                        "error": f"Execution timed out after {self.max_execution_time} seconds"
                    })
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
            
        except Exception as e:
            execution_record.update({
                "status": "error",
                "error": str(e)
            })
        
        # Add to history
        self.execution_history.append(execution_record)
        
        # Keep only last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
        
        # Broadcast completion to dashboard
        await self._broadcast_to_dashboard({
            "type": "execution_completed",
            "execution": execution_record
        })
        
        return {
            "success": True,
            "execution": execution_record
        }
    
    async def _install_package(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Install a Python package using pip"""
        package = params.get("package", "")
        if not package:
            return {"error": "No package specified"}
        
        try:
            # Use subprocess to install package
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "install", package,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=120  # 2 minutes for package installation
            )
            
            stdout_text = stdout.decode('utf-8', errors='replace')
            stderr_text = stderr.decode('utf-8', errors='replace')
            
            result = {
                "success": process.returncode == 0,
                "package": package,
                "return_code": process.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text
            }
            
            # Broadcast to dashboard
            await self._broadcast_to_dashboard({
                "type": "package_installed",
                "result": result
            })
            
            return result
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Package installation timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _list_packages(self) -> Dict[str, Any]:
        """List installed Python packages"""
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "list", "--format=json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                packages = json.loads(stdout.decode('utf-8'))
                return {
                    "success": True,
                    "packages": packages
                }
            else:
                return {
                    "success": False,
                    "error": stderr.decode('utf-8')
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_execution_history(self) -> Dict[str, Any]:
        """Get execution history"""
        return {
            "success": True,
            "history": self.execution_history
        }
    
    async def _clear_history(self) -> Dict[str, Any]:
        """Clear execution history"""
        self.execution_history.clear()
        
        # Broadcast to dashboard
        await self._broadcast_to_dashboard({
            "type": "history_cleared"
        })
        
        return {
            "success": True,
            "message": "Execution history cleared"
        }
    
    async def _check_syntax(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check Python code syntax without executing"""
        code = params.get("code", "")
        if not code:
            return {"error": "No code provided"}
        
        try:
            compile(code, '<string>', 'exec')
            return {
                "success": True,
                "valid": True,
                "message": "Syntax is valid"
            }
        except SyntaxError as e:
            return {
                "success": True,
                "valid": False,
                "error": str(e),
                "line": e.lineno,
                "offset": e.offset
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_python_info(self) -> Dict[str, Any]:
        """Get Python environment information"""
        try:
            info = {
                "version": sys.version,
                "version_info": {
                    "major": sys.version_info.major,
                    "minor": sys.version_info.minor,
                    "micro": sys.version_info.micro
                },
                "executable": sys.executable,
                "platform": sys.platform,
                "path": sys.path[:5]  # First 5 entries to avoid too much data
            }
            
            return {
                "success": True,
                "info": info
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _broadcast_to_dashboard(self, message: Dict[str, Any]):
        """Broadcast message to all connected dashboard clients"""
        if not self.dashboard_connections:
            return
        
        disconnected = set()
        for websocket in self.dashboard_connections:
            try:
                await websocket.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.dashboard_connections -= disconnected


async def main():
    server = PythonExecutionMCPServer()
    await server.start_server()


if __name__ == "__main__":
    asyncio.run(main())