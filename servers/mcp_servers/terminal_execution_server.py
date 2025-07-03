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
import signal


class TerminalExecutionMCPServer:
    def __init__(self, host: str = "localhost", port: int = 8086):
        self.host = host
        self.port = port
        self.dashboard_connections = set()
        self.execution_history = []
        self.current_directory = os.getcwd()
        self.environment_vars = dict(os.environ)
        self.running_processes = {}  # Store running processes
        
    async def start_server(self):
        """Start the MCP server"""
        print(f"Starting Terminal Execution MCP Server on {self.host}:{self.port}")
        
        async def handle_client(websocket, path):
            self.dashboard_connections.add(websocket)
            try:
                await websocket.send(json.dumps({
                    "type": "connection_established",
                    "server": "terminal_execution",
                    "capabilities": [
                        "execute_command",
                        "execute_command_interactive",
                        "change_directory",
                        "get_current_directory", 
                        "set_environment_variable",
                        "get_environment_variables",
                        "get_execution_history",
                        "clear_history",
                        "kill_process",
                        "list_running_processes"
                    ],
                    "current_directory": self.current_directory
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
        print(f"Terminal Execution MCP Server running on ws://{self.host}:{self.port}")
        
        # Keep server running
        await asyncio.Future()
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "execute_command":
                return await self._execute_command(params)
            elif method == "execute_command_interactive":
                return await self._execute_command_interactive(params)
            elif method == "change_directory":
                return await self._change_directory(params)
            elif method == "get_current_directory":
                return await self._get_current_directory()
            elif method == "set_environment_variable":
                return await self._set_environment_variable(params)
            elif method == "get_environment_variables":
                return await self._get_environment_variables()
            elif method == "get_execution_history":
                return await self._get_execution_history()
            elif method == "clear_history":
                return await self._clear_history()
            elif method == "kill_process":
                return await self._kill_process(params)
            elif method == "list_running_processes":
                return await self._list_running_processes()
            else:
                return {"error": f"Unknown method: {method}"}
                
        except Exception as e:
            return {"error": f"Method execution failed: {str(e)}"}
    
    async def _execute_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a terminal command"""
        command = params.get("command", "")
        if not command:
            return {"error": "No command provided"}
        
        timeout = params.get("timeout", 300)  # Default 5 minutes
        
        # Create execution record
        execution_id = str(uuid.uuid4())
        execution_record = {
            "id": execution_id,
            "command": command,
            "directory": self.current_directory,
            "timestamp": time.time(),
            "status": "running"
        }
        
        # Broadcast execution start to dashboard
        await self._broadcast_to_dashboard({
            "type": "command_started",
            "execution": execution_record
        })
        
        try:
            # Execute command directly in current directory with current environment
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.current_directory,
                env=self.environment_vars
            )
            
            # Store the process for potential killing
            self.running_processes[execution_id] = process
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                
                # Decode output
                stdout_text = stdout.decode('utf-8', errors='replace')
                stderr_text = stderr.decode('utf-8', errors='replace')
                
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
                await process.wait()
                execution_record.update({
                    "status": "timeout",
                    "error": f"Command timed out after {timeout} seconds",
                    "execution_time": time.time() - execution_record["timestamp"]
                })
                
        except Exception as e:
            execution_record.update({
                "status": "error",
                "error": str(e),
                "execution_time": time.time() - execution_record["timestamp"]
            })
        finally:
            # Remove from running processes
            self.running_processes.pop(execution_id, None)
        
        # Add to history
        self.execution_history.append(execution_record)
        
        # Keep only last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
        
        # Broadcast completion to dashboard
        await self._broadcast_to_dashboard({
            "type": "command_completed",
            "execution": execution_record
        })
        
        return {
            "success": True,
            "execution": execution_record
        }
    
    async def _execute_command_interactive(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command that may require interaction"""
        command = params.get("command", "")
        input_data = params.get("input", "")
        
        if not command:
            return {"error": "No command provided"}
        
        execution_id = str(uuid.uuid4())
        execution_record = {
            "id": execution_id,
            "command": command,
            "directory": self.current_directory,
            "timestamp": time.time(),
            "status": "running",
            "interactive": True
        }
        
        await self._broadcast_to_dashboard({
            "type": "command_started",
            "execution": execution_record
        })
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.current_directory,
                env=self.environment_vars
            )
            
            self.running_processes[execution_id] = process
            
            # Send input if provided
            if input_data:
                process.stdin.write(input_data.encode())
                await process.stdin.drain()
            
            process.stdin.close()
            
            stdout, stderr = await process.communicate()
            
            stdout_text = stdout.decode('utf-8', errors='replace')
            stderr_text = stderr.decode('utf-8', errors='replace')
            
            execution_record.update({
                "status": "completed",
                "return_code": process.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "execution_time": time.time() - execution_record["timestamp"]
            })
            
        except Exception as e:
            execution_record.update({
                "status": "error",
                "error": str(e),
                "execution_time": time.time() - execution_record["timestamp"]
            })
        finally:
            self.running_processes.pop(execution_id, None)
        
        self.execution_history.append(execution_record)
        
        await self._broadcast_to_dashboard({
            "type": "command_completed",
            "execution": execution_record
        })
        
        return {
            "success": True,
            "execution": execution_record
        }
    
    async def _change_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Change current working directory"""
        path = params.get("path", "")
        if not path:
            return {"error": "No path provided"}
        
        try:
            # Resolve the path
            if path.startswith("~"):
                path = os.path.expanduser(path)
            
            new_path = os.path.abspath(os.path.join(self.current_directory, path))
            
            if os.path.exists(new_path) and os.path.isdir(new_path):
                self.current_directory = new_path
                
                # Broadcast directory change
                await self._broadcast_to_dashboard({
                    "type": "directory_changed",
                    "directory": self.current_directory
                })
                
                return {
                    "success": True,
                    "current_directory": self.current_directory
                }
            else:
                return {
                    "success": False,
                    "error": f"Directory does not exist: {new_path}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_current_directory(self) -> Dict[str, Any]:
        """Get current working directory"""
        return {
            "success": True,
            "current_directory": self.current_directory
        }
    
    async def _set_environment_variable(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set an environment variable"""
        name = params.get("name", "")
        value = params.get("value", "")
        
        if not name:
            return {"error": "No variable name provided"}
        
        self.environment_vars[name] = value
        
        # Broadcast environment change
        await self._broadcast_to_dashboard({
            "type": "environment_variable_set",
            "name": name,
            "value": value
        })
        
        return {
            "success": True,
            "name": name,
            "value": value
        }
    
    async def _get_environment_variables(self) -> Dict[str, Any]:
        """Get all environment variables"""
        return {
            "success": True,
            "environment_variables": dict(self.environment_vars)
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
        
        await self._broadcast_to_dashboard({
            "type": "history_cleared"
        })
        
        return {
            "success": True,
            "message": "Execution history cleared"
        }
    
    async def _kill_process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Kill a running process by execution ID"""
        execution_id = params.get("execution_id", "")
        
        if not execution_id:
            return {"error": "No execution ID provided"}
        
        process = self.running_processes.get(execution_id)
        if not process:
            return {
                "success": False,
                "error": "Process not found or already finished"
            }
        
        try:
            process.kill()
            await process.wait()
            
            await self._broadcast_to_dashboard({
                "type": "process_killed",
                "execution_id": execution_id
            })
            
            return {
                "success": True,
                "message": f"Process {execution_id} killed"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _list_running_processes(self) -> Dict[str, Any]:
        """List currently running processes"""
        running = []
        for execution_id, process in self.running_processes.items():
            running.append({
                "execution_id": execution_id,
                "pid": process.pid,
                "returncode": process.returncode
            })
        
        return {
            "success": True,
            "running_processes": running
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
    server = TerminalExecutionMCPServer()
    await server.start_server()


if __name__ == "__main__":
    asyncio.run(main())