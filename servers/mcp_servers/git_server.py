#!/usr/bin/env python3
"""
Git Operations MCP Server
Provides Git version control operations for AI agents
"""

import asyncio
import json
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import websockets

class GitMCPServer:
    def __init__(self, repo_path: str = None):
        self.repo_path = Path(repo_path or os.getcwd()).resolve()
        self.dashboard_ws = None
        
    async def start(self):
        """Initialize git server"""
        try:
            self.dashboard_ws = await websockets.connect("ws://localhost:3001/ws/git")
            print("✅ Connected to dashboard WebSocket")
        except Exception as e:
            print(f"⚠️  Dashboard WebSocket not available: {e}")
    
    async def _run_git_command(self, command: List[str], cwd: str = None) -> Dict[str, Any]:
        """Run git command safely"""
        try:
            result = subprocess.run(
                ['git'] + command,
                cwd=cwd or str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git command timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "status":
                return await self.get_status()
            elif method == "log":
                return await self.get_log(params.get("limit", 10))
            elif method == "diff":
                return await self.get_diff(params.get("file"))
            elif method == "add":
                return await self.add_files(params.get("files", []))
            elif method == "commit":
                return await self.commit(params.get("message"), params.get("author"))
            elif method == "push":
                return await self.push(params.get("remote", "origin"), params.get("branch"))
            elif method == "pull":
                return await self.pull(params.get("remote", "origin"), params.get("branch"))
            elif method == "checkout":
                return await self.checkout(params.get("branch"), params.get("create", False))
            elif method == "branch":
                return await self.get_branches()
            elif method == "create_branch":
                return await self.create_branch(params.get("name"))
            elif method == "delete_branch":
                return await self.delete_branch(params.get("name"))
            elif method == "remote":
                return await self.get_remotes()
            elif method == "add_remote":
                return await self.add_remote(params.get("name"), params.get("url"))
            elif method == "clone":
                return await self.clone_repo(params.get("url"), params.get("path"))
            elif method == "init":
                return await self.init_repo(params.get("path"))
            elif method == "stash":
                return await self.stash(params.get("message"))
            elif method == "stash_pop":
                return await self.stash_pop()
            elif method == "reset":
                return await self.reset(params.get("mode", "soft"), params.get("commit"))
            else:
                return {"error": f"Unknown method: {method}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get git status"""
        result = await self._run_git_command(['status', '--porcelain'])
        
        if result["success"]:
            status_lines = result["stdout"].split('\n') if result["stdout"] else []
            files = []
            
            for line in status_lines:
                if line.strip():
                    status_code = line[:2]
                    filename = line[3:]
                    files.append({
                        "file": filename,
                        "status": self._parse_status_code(status_code)
                    })
            
            # Get current branch
            branch_result = await self._run_git_command(['branch', '--show-current'])
            current_branch = branch_result["stdout"] if branch_result["success"] else "unknown"
            
            response = {
                "success": True,
                "current_branch": current_branch,
                "files": files,
                "clean": len(files) == 0
            }
        else:
            response = {"success": False, "error": result["stderr"] or "Git status failed"}
        
        await self.send_to_dashboard({
            "type": "git_status",
            **response
        })
        
        return response
    
    def _parse_status_code(self, code: str) -> str:
        """Parse git status code"""
        status_map = {
            ' M': 'modified',
            'M ': 'staged_modified',
            'MM': 'modified_staged_modified',
            'A ': 'staged_new',
            'AM': 'staged_new_modified',
            'D ': 'staged_deleted',
            ' D': 'deleted',
            'R ': 'staged_renamed',
            'C ': 'staged_copied',
            '??': 'untracked',
            '!!': 'ignored'
        }
        return status_map.get(code, 'unknown')
    
    async def get_log(self, limit: int = 10) -> Dict[str, Any]:
        """Get git log"""
        result = await self._run_git_command([
            'log', 
            f'--max-count={limit}',
            '--pretty=format:%H|%an|%ae|%ad|%s',
            '--date=iso'
        ])
        
        if result["success"]:
            commits = []
            for line in result["stdout"].split('\n'):
                if line.strip():
                    parts = line.split('|', 4)
                    if len(parts) == 5:
                        commits.append({
                            "hash": parts[0],
                            "author_name": parts[1],
                            "author_email": parts[2],
                            "date": parts[3],
                            "message": parts[4]
                        })
            
            response = {
                "success": True,
                "commits": commits
            }
        else:
            response = {"success": False, "error": result["stderr"] or "Git log failed"}
        
        await self.send_to_dashboard({
            "type": "git_log",
            **response
        })
        
        return response
    
    async def get_diff(self, file: str = None) -> Dict[str, Any]:
        """Get git diff"""
        command = ['diff']
        if file:
            command.append(file)
        
        result = await self._run_git_command(command)
        
        response = {
            "success": result["success"],
            "diff": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "git_diff",
            "file": file,
            **response
        })
        
        return response
    
    async def add_files(self, files: List[str]) -> Dict[str, Any]:
        """Add files to staging area"""
        if not files:
            files = ['.']
        
        result = await self._run_git_command(['add'] + files)
        
        response = {
            "success": result["success"],
            "files": files,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "git_add",
            **response
        })
        
        return response
    
    async def commit(self, message: str, author: str = None) -> Dict[str, Any]:
        """Create git commit"""
        if not message:
            return {"error": "Commit message required"}
        
        command = ['commit', '-m', message]
        if author:
            command.extend(['--author', author])
        
        result = await self._run_git_command(command)
        
        response = {
            "success": result["success"],
            "message": message,
            "output": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "git_commit",
            **response
        })
        
        return response
    
    async def push(self, remote: str = "origin", branch: str = None) -> Dict[str, Any]:
        """Push changes to remote"""
        command = ['push', remote]
        if branch:
            command.append(branch)
        
        result = await self._run_git_command(command)
        
        response = {
            "success": result["success"],
            "remote": remote,
            "branch": branch,
            "output": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "git_push",
            **response
        })
        
        return response
    
    async def pull(self, remote: str = "origin", branch: str = None) -> Dict[str, Any]:
        """Pull changes from remote"""
        command = ['pull', remote]
        if branch:
            command.append(branch)
        
        result = await self._run_git_command(command)
        
        response = {
            "success": result["success"],
            "remote": remote,
            "branch": branch,
            "output": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "git_pull",
            **response
        })
        
        return response
    
    async def checkout(self, branch: str, create: bool = False) -> Dict[str, Any]:
        """Checkout branch"""
        command = ['checkout']
        if create:
            command.append('-b')
        command.append(branch)
        
        result = await self._run_git_command(command)
        
        response = {
            "success": result["success"],
            "branch": branch,
            "created": create,
            "output": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "git_checkout",
            **response
        })
        
        return response
    
    async def get_branches(self) -> Dict[str, Any]:
        """Get all branches"""
        result = await self._run_git_command(['branch', '-a'])
        
        if result["success"]:
            branches = []
            current_branch = None
            
            for line in result["stdout"].split('\n'):
                line = line.strip()
                if line:
                    if line.startswith('* '):
                        current_branch = line[2:]
                        branches.append({"name": current_branch, "current": True})
                    else:
                        branches.append({"name": line, "current": False})
            
            response = {
                "success": True,
                "branches": branches,
                "current_branch": current_branch
            }
        else:
            response = {"success": False, "error": result["stderr"]}
        
        return response
    
    async def create_branch(self, name: str) -> Dict[str, Any]:
        """Create new branch"""
        result = await self._run_git_command(['checkout', '-b', name])
        
        response = {
            "success": result["success"],
            "branch": name,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "git_branch_created",
            **response
        })
        
        return response
    
    async def delete_branch(self, name: str) -> Dict[str, Any]:
        """Delete branch"""
        result = await self._run_git_command(['branch', '-d', name])
        
        response = {
            "success": result["success"],
            "branch": name,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "git_branch_deleted",
            **response
        })
        
        return response
    
    async def get_remotes(self) -> Dict[str, Any]:
        """Get remote repositories"""
        result = await self._run_git_command(['remote', '-v'])
        
        if result["success"]:
            remotes = {}
            for line in result["stdout"].split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        name, url = parts[0], parts[1]
                        if name not in remotes:
                            remotes[name] = {"fetch": None, "push": None}
                        if "(fetch)" in line:
                            remotes[name]["fetch"] = url
                        elif "(push)" in line:
                            remotes[name]["push"] = url
            
            response = {
                "success": True,
                "remotes": remotes
            }
        else:
            response = {"success": False, "error": result["stderr"]}
        
        return response
    
    async def add_remote(self, name: str, url: str) -> Dict[str, Any]:
        """Add remote repository"""
        result = await self._run_git_command(['remote', 'add', name, url])
        
        response = {
            "success": result["success"],
            "name": name,
            "url": url,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "git_remote_added",
            **response
        })
        
        return response
    
    async def clone_repo(self, url: str, path: str = None) -> Dict[str, Any]:
        """Clone repository"""
        command = ['clone', url]
        if path:
            command.append(path)
        
        result = await self._run_git_command(command, cwd=str(self.repo_path.parent))
        
        response = {
            "success": result["success"],
            "url": url,
            "path": path,
            "output": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "git_cloned",
            **response
        })
        
        return response
    
    async def init_repo(self, path: str = None) -> Dict[str, Any]:
        """Initialize git repository"""
        init_path = path or str(self.repo_path)
        result = await self._run_git_command(['init'], cwd=init_path)
        
        response = {
            "success": result["success"],
            "path": init_path,
            "output": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "git_initialized",
            **response
        })
        
        return response
    
    async def stash(self, message: str = None) -> Dict[str, Any]:
        """Stash changes"""
        command = ['stash']
        if message:
            command.extend(['push', '-m', message])
        
        result = await self._run_git_command(command)
        
        response = {
            "success": result["success"],
            "message": message,
            "output": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "git_stashed",
            **response
        })
        
        return response
    
    async def stash_pop(self) -> Dict[str, Any]:
        """Pop stashed changes"""
        result = await self._run_git_command(['stash', 'pop'])
        
        response = {
            "success": result["success"],
            "output": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "git_stash_popped",
            **response
        })
        
        return response
    
    async def reset(self, mode: str = "soft", commit: str = None) -> Dict[str, Any]:
        """Reset repository"""
        command = ['reset', f'--{mode}']
        if commit:
            command.append(commit)
        
        result = await self._run_git_command(command)
        
        response = {
            "success": result["success"],
            "mode": mode,
            "commit": commit,
            "output": result["stdout"] if result["success"] else None,
            "error": result["stderr"] if not result["success"] else None
        }
        
        await self.send_to_dashboard({
            "type": "git_reset",
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
    repo_path = os.getenv("GIT_REPO_PATH", os.getcwd())
    server = GitMCPServer(repo_path)
    await server.start()
    
    print("🔧 Git Operations MCP Server started")
    print(f"Repository path: {server.repo_path}")
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