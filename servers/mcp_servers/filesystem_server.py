#!/usr/bin/env python3
"""
File System MCP Server for File Operations
Provides safe file system access for AI agents
"""

import asyncio
import json
import os
import shutil
import mimetypes
from pathlib import Path
from typing import Dict, Any, List
import websockets

class FileSystemMCPServer:
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or os.getcwd()).resolve()
        self.dashboard_ws = None
        
    async def start(self):
        """Initialize file system server"""
        try:
            self.dashboard_ws = await websockets.connect("ws://localhost:3001/ws/filesystem")
            print("✅ Connected to dashboard WebSocket")
        except Exception as e:
            print(f"⚠️  Dashboard WebSocket not available: {e}")
    
    def _safe_path(self, path: str) -> Path:
        """Ensure path is within base directory"""
        full_path = (self.base_path / path).resolve()
        if not str(full_path).startswith(str(self.base_path)):
            raise ValueError(f"Path outside allowed directory: {path}")
        return full_path
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "list_files":
                return await self.list_files(params.get("path", "."))
            elif method == "read_file":
                return await self.read_file(params.get("path"))
            elif method == "write_file":
                return await self.write_file(params.get("path"), params.get("content"))
            elif method == "create_directory":
                return await self.create_directory(params.get("path"))
            elif method == "delete":
                return await self.delete(params.get("path"))
            elif method == "move":
                return await self.move(params.get("src"), params.get("dst"))
            elif method == "copy":
                return await self.copy(params.get("src"), params.get("dst"))
            elif method == "get_info":
                return await self.get_info(params.get("path"))
            elif method == "search":
                return await self.search(params.get("pattern"), params.get("path", "."))
            else:
                return {"error": f"Unknown method: {method}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def list_files(self, path: str) -> Dict[str, Any]:
        """List files and directories"""
        try:
            safe_path = self._safe_path(path)
            if not safe_path.exists():
                return {"error": f"Path does not exist: {path}"}
            
            if not safe_path.is_dir():
                return {"error": f"Path is not a directory: {path}"}
            
            files = []
            for item in safe_path.iterdir():
                try:
                    stat = item.stat()
                    files.append({
                        "name": item.name,
                        "path": str(item.relative_to(self.base_path)),
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "permissions": oct(stat.st_mode)[-3:],
                        "mime_type": mimetypes.guess_type(str(item))[0] if item.is_file() else None
                    })
                except (PermissionError, OSError):
                    continue
            
            result = {
                "success": True,
                "path": path,
                "files": sorted(files, key=lambda x: (x["type"] == "file", x["name"].lower()))
            }
            
            await self.send_to_dashboard({
                "type": "file_list",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def read_file(self, path: str) -> Dict[str, Any]:
        """Read file content"""
        try:
            safe_path = self._safe_path(path)
            if not safe_path.exists():
                return {"error": f"File does not exist: {path}"}
            
            if not safe_path.is_file():
                return {"error": f"Path is not a file: {path}"}
            
            # Check file size (limit to 10MB)
            if safe_path.stat().st_size > 10 * 1024 * 1024:
                return {"error": f"File too large (>10MB): {path}"}
            
            try:
                content = safe_path.read_text(encoding='utf-8')
                is_binary = False
            except UnicodeDecodeError:
                # Try reading as binary
                content = safe_path.read_bytes().hex()
                is_binary = True
            
            result = {
                "success": True,
                "path": path,
                "content": content,
                "is_binary": is_binary,
                "size": safe_path.stat().st_size,
                "mime_type": mimetypes.guess_type(str(safe_path))[0]
            }
            
            await self.send_to_dashboard({
                "type": "file_content",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to file"""
        try:
            safe_path = self._safe_path(path)
            
            # Create parent directories if needed
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            
            safe_path.write_text(content, encoding='utf-8')
            
            result = {
                "success": True,
                "path": path,
                "size": len(content.encode('utf-8'))
            }
            
            await self.send_to_dashboard({
                "type": "file_written",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def create_directory(self, path: str) -> Dict[str, Any]:
        """Create directory"""
        try:
            safe_path = self._safe_path(path)
            safe_path.mkdir(parents=True, exist_ok=True)
            
            result = {
                "success": True,
                "path": path
            }
            
            await self.send_to_dashboard({
                "type": "directory_created",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def delete(self, path: str) -> Dict[str, Any]:
        """Delete file or directory"""
        try:
            safe_path = self._safe_path(path)
            if not safe_path.exists():
                return {"error": f"Path does not exist: {path}"}
            
            if safe_path.is_dir():
                shutil.rmtree(safe_path)
            else:
                safe_path.unlink()
            
            result = {
                "success": True,
                "path": path
            }
            
            await self.send_to_dashboard({
                "type": "file_deleted",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def move(self, src: str, dst: str) -> Dict[str, Any]:
        """Move file or directory"""
        try:
            safe_src = self._safe_path(src)
            safe_dst = self._safe_path(dst)
            
            if not safe_src.exists():
                return {"error": f"Source does not exist: {src}"}
            
            safe_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(safe_src), str(safe_dst))
            
            result = {
                "success": True,
                "src": src,
                "dst": dst
            }
            
            await self.send_to_dashboard({
                "type": "file_moved",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def copy(self, src: str, dst: str) -> Dict[str, Any]:
        """Copy file or directory"""
        try:
            safe_src = self._safe_path(src)
            safe_dst = self._safe_path(dst)
            
            if not safe_src.exists():
                return {"error": f"Source does not exist: {src}"}
            
            safe_dst.parent.mkdir(parents=True, exist_ok=True)
            
            if safe_src.is_dir():
                shutil.copytree(str(safe_src), str(safe_dst))
            else:
                shutil.copy2(str(safe_src), str(safe_dst))
            
            result = {
                "success": True,
                "src": src,
                "dst": dst
            }
            
            await self.send_to_dashboard({
                "type": "file_copied",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_info(self, path: str) -> Dict[str, Any]:
        """Get file/directory information"""
        try:
            safe_path = self._safe_path(path)
            if not safe_path.exists():
                return {"error": f"Path does not exist: {path}"}
            
            stat = safe_path.stat()
            
            return {
                "success": True,
                "path": path,
                "type": "directory" if safe_path.is_dir() else "file",
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime,
                "permissions": oct(stat.st_mode)[-3:],
                "mime_type": mimetypes.guess_type(str(safe_path))[0] if safe_path.is_file() else None
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def search(self, pattern: str, path: str = ".") -> Dict[str, Any]:
        """Search for files matching pattern"""
        try:
            safe_path = self._safe_path(path)
            if not safe_path.exists() or not safe_path.is_dir():
                return {"error": f"Invalid search path: {path}"}
            
            matches = []
            for item in safe_path.rglob(pattern):
                try:
                    if self._safe_path(str(item.relative_to(self.base_path))):
                        stat = item.stat()
                        matches.append({
                            "name": item.name,
                            "path": str(item.relative_to(self.base_path)),
                            "type": "directory" if item.is_dir() else "file",
                            "size": stat.st_size,
                            "modified": stat.st_mtime
                        })
                except (ValueError, PermissionError, OSError):
                    continue
            
            result = {
                "success": True,
                "pattern": pattern,
                "search_path": path,
                "matches": matches[:100]  # Limit results
            }
            
            await self.send_to_dashboard({
                "type": "search_results",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
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
    # Allow setting base path via environment variable
    base_path = os.getenv("FILESYSTEM_BASE_PATH", os.getcwd())
    server = FileSystemMCPServer(base_path)
    await server.start()
    
    print("📁 File System MCP Server started")
    print(f"Base path: {server.base_path}")
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