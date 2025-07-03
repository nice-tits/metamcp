#!/usr/bin/env python3
"""
Docker Management MCP Server
Provides Docker container operations for AI agents (if Docker is installed)
"""

import asyncio
import json
import subprocess
import shutil
from typing import Dict, Any, List, Optional
import websockets

class DockerMCPServer:
    def __init__(self):
        self.dashboard_ws = None
        self.docker_available = self._check_docker_availability()
        
    def _check_docker_availability(self) -> bool:
        """Check if Docker is installed and accessible"""
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    async def start(self):
        """Initialize docker server"""
        try:
            self.dashboard_ws = await websockets.connect("ws://localhost:3001/ws/docker")
            print("✅ Connected to dashboard WebSocket")
        except Exception as e:
            print(f"⚠️  Dashboard WebSocket not available: {e}")
    
    async def _run_docker_command(self, command: List[str]) -> Dict[str, Any]:
        """Run docker command safely"""
        if not self.docker_available:
            return {"success": False, "error": "Docker not available"}
        
        try:
            result = subprocess.run(
                ['docker'] + command,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Docker command timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        if not self.docker_available:
            return {"error": "Docker not installed or not accessible"}
        
        try:
            if method == "list_containers":
                return await self.list_containers(params.get("all", False))
            elif method == "list_images":
                return await self.list_images()
            elif method == "run_container":
                return await self.run_container(
                    params.get("image"),
                    params.get("name"),
                    params.get("ports", {}),
                    params.get("volumes", {}),
                    params.get("environment", {}),
                    params.get("command")
                )
            elif method == "stop_container":
                return await self.stop_container(params.get("container_id"))
            elif method == "start_container":
                return await self.start_container(params.get("container_id"))
            elif method == "remove_container":
                return await self.remove_container(params.get("container_id"))
            elif method == "container_logs":
                return await self.get_container_logs(params.get("container_id"), params.get("lines", 100))
            elif method == "container_stats":
                return await self.get_container_stats(params.get("container_id"))
            elif method == "pull_image":
                return await self.pull_image(params.get("image"))
            elif method == "remove_image":
                return await self.remove_image(params.get("image_id"))
            elif method == "build_image":
                return await self.build_image(params.get("path"), params.get("tag"))
            elif method == "exec_command":
                return await self.exec_command(params.get("container_id"), params.get("command"))
            elif method == "docker_info":
                return await self.get_docker_info()
            elif method == "docker_version":
                return await self.get_docker_version()
            elif method == "prune_system":
                return await self.prune_system()
            else:
                return {"error": f"Unknown method: {method}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def list_containers(self, all_containers: bool = False) -> Dict[str, Any]:
        """List Docker containers"""
        command = ['ps', '--format', 'table {{.ID}}\t{{.Image}}\t{{.Command}}\t{{.CreatedAt}}\t{{.Status}}\t{{.Ports}}\t{{.Names}}']
        if all_containers:
            command.append('-a')
        
        result = await self._run_docker_command(command)
        
        if result["success"]:
            lines = result["stdout"].split('\n')
            containers = []
            
            for line in lines[1:]:  # Skip header
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        containers.append({
                            "id": parts[0],
                            "image": parts[1],
                            "command": parts[2],
                            "created": parts[3],
                            "status": parts[4],
                            "ports": parts[5],
                            "names": parts[6]
                        })
            
            response = {
                "success": True,
                "containers": containers,
                "count": len(containers)
            }
        else:
            response = {"success": False, "error": result["stderr"]}
        
        await self.send_to_dashboard({
            "type": "docker_containers",
            **response
        })
        
        return response
    
    async def list_images(self) -> Dict[str, Any]:
        """List Docker images"""
        result = await self._run_docker_command(['images', '--format', 'table {{.ID}}\t{{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}'])
        
        if result["success"]:
            lines = result["stdout"].split('\n')
            images = []
            
            for line in lines[1:]:  # Skip header
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 5:
                        images.append({
                            "id": parts[0],
                            "repository": parts[1],
                            "tag": parts[2],
                            "created": parts[3],
                            "size": parts[4]
                        })
            
            response = {
                "success": True,
                "images": images,
                "count": len(images)
            }
        else:
            response = {"success": False, "error": result["stderr"]}
        
        await self.send_to_dashboard({
            "type": "docker_images",
            **response
        })
        
        return response
    
    async def run_container(self, image: str, name: str = None, ports: Dict[str, str] = None, 
                           volumes: Dict[str, str] = None, environment: Dict[str, str] = None, 
                           command: str = None) -> Dict[str, Any]:
        """Run a new container"""
        if not image:
            return {"error": "Image name required"}
        
        cmd = ['run', '-d']  # Detached mode
        
        if name:
            cmd.extend(['--name', name])
        
        if ports:
            for host_port, container_port in ports.items():
                cmd.extend(['-p', f'{host_port}:{container_port}'])
        
        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(['-v', f'{host_path}:{container_path}'])
        
        if environment:
            for key, value in environment.items():
                cmd.extend(['-e', f'{key}={value}'])
        
        cmd.append(image)
        
        if command:
            cmd.extend(command.split())
        
        result = await self._run_docker_command(cmd)
        
        response = {
            "success": result["success"],
            "container_id": result["stdout"] if result["success"] else None,
            "image": image,
            "name": name,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "docker_container_started",
            **response
        })
        
        return response
    
    async def stop_container(self, container_id: str) -> Dict[str, Any]:
        """Stop a container"""
        result = await self._run_docker_command(['stop', container_id])
        
        response = {
            "success": result["success"],
            "container_id": container_id,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "docker_container_stopped",
            **response
        })
        
        return response
    
    async def start_container(self, container_id: str) -> Dict[str, Any]:
        """Start a stopped container"""
        result = await self._run_docker_command(['start', container_id])
        
        response = {
            "success": result["success"],
            "container_id": container_id,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "docker_container_started",
            **response
        })
        
        return response
    
    async def remove_container(self, container_id: str) -> Dict[str, Any]:
        """Remove a container"""
        result = await self._run_docker_command(['rm', '-f', container_id])
        
        response = {
            "success": result["success"],
            "container_id": container_id,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "docker_container_removed",
            **response
        })
        
        return response
    
    async def get_container_logs(self, container_id: str, lines: int = 100) -> Dict[str, Any]:
        """Get container logs"""
        result = await self._run_docker_command(['logs', '--tail', str(lines), container_id])
        
        response = {
            "success": result["success"],
            "container_id": container_id,
            "logs": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "docker_container_logs",
            **response
        })
        
        return response
    
    async def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """Get container resource stats"""
        result = await self._run_docker_command(['stats', '--no-stream', '--format', 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}', container_id])
        
        if result["success"] and result["stdout"]:
            lines = result["stdout"].split('\n')
            if len(lines) > 1:  # Skip header
                parts = lines[1].split('\t')
                if len(parts) >= 5:
                    stats = {
                        "container": parts[0],
                        "cpu_percent": parts[1],
                        "memory_usage": parts[2],
                        "network_io": parts[3],
                        "block_io": parts[4]
                    }
                    response = {
                        "success": True,
                        "container_id": container_id,
                        "stats": stats
                    }
                else:
                    response = {"success": False, "error": "Unable to parse stats"}
            else:
                response = {"success": False, "error": "No stats available"}
        else:
            response = {"success": False, "error": result["stderr"]}
        
        return response
    
    async def pull_image(self, image: str) -> Dict[str, Any]:
        """Pull Docker image"""
        result = await self._run_docker_command(['pull', image])
        
        response = {
            "success": result["success"],
            "image": image,
            "output": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "docker_image_pulled",
            **response
        })
        
        return response
    
    async def remove_image(self, image_id: str) -> Dict[str, Any]:
        """Remove Docker image"""
        result = await self._run_docker_command(['rmi', image_id])
        
        response = {
            "success": result["success"],
            "image_id": image_id,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "docker_image_removed",
            **response
        })
        
        return response
    
    async def build_image(self, path: str, tag: str = None) -> Dict[str, Any]:
        """Build Docker image"""
        cmd = ['build', path]
        if tag:
            cmd.extend(['-t', tag])
        
        result = await self._run_docker_command(cmd)
        
        response = {
            "success": result["success"],
            "path": path,
            "tag": tag,
            "output": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "docker_image_built",
            **response
        })
        
        return response
    
    async def exec_command(self, container_id: str, command: str) -> Dict[str, Any]:
        """Execute command in container"""
        result = await self._run_docker_command(['exec', container_id] + command.split())
        
        response = {
            "success": result["success"],
            "container_id": container_id,
            "command": command,
            "output": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "docker_command_executed",
            **response
        })
        
        return response
    
    async def get_docker_info(self) -> Dict[str, Any]:
        """Get Docker system information"""
        result = await self._run_docker_command(['info', '--format', 'json'])
        
        if result["success"]:
            try:
                info = json.loads(result["stdout"])
                response = {
                    "success": True,
                    "info": info
                }
            except json.JSONDecodeError:
                response = {"success": False, "error": "Failed to parse Docker info"}
        else:
            response = {"success": False, "error": result["stderr"]}
        
        return response
    
    async def get_docker_version(self) -> Dict[str, Any]:
        """Get Docker version"""
        result = await self._run_docker_command(['version', '--format', 'json'])
        
        if result["success"]:
            try:
                version = json.loads(result["stdout"])
                response = {
                    "success": True,
                    "version": version
                }
            except json.JSONDecodeError:
                response = {"success": False, "error": "Failed to parse Docker version"}
        else:
            response = {"success": False, "error": result["stderr"]}
        
        return response
    
    async def prune_system(self) -> Dict[str, Any]:
        """Prune Docker system (remove unused data)"""
        result = await self._run_docker_command(['system', 'prune', '-f'])
        
        response = {
            "success": result["success"],
            "output": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "docker_system_pruned",
            **response
        })
        
        return response
    
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

async def main():
    server = DockerMCPServer()
    await server.start()
    
    print("🐳 Docker Management MCP Server started")
    if server.docker_available:
        print("Docker is available")
    else:
        print("⚠️  Docker not available - install Docker to use this server")
    print("Waiting for commands...")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        await server.close()

if __name__ == "__main__":
    asyncio.run(main())