#!/usr/bin/env python3
"""
System Monitoring MCP Server using psutil
Provides system metrics and monitoring for AI agents
"""

import asyncio
import json
import psutil
import time
from typing import Dict, Any, List
import websockets
from datetime import datetime

class MonitoringMCPServer:
    def __init__(self):
        self.dashboard_ws = None
        self.monitoring_active = False
        self.monitoring_task = None
        
    async def start(self):
        """Initialize monitoring server"""
        try:
            self.dashboard_ws = await websockets.connect("ws://localhost:3001/ws/monitoring")
            print("✅ Connected to dashboard WebSocket")
        except Exception as e:
            print(f"⚠️  Dashboard WebSocket not available: {e}")
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "get_system_info":
                return await self.get_system_info()
            elif method == "get_cpu_info":
                return await self.get_cpu_info()
            elif method == "get_memory_info":
                return await self.get_memory_info()
            elif method == "get_disk_info":
                return await self.get_disk_info()
            elif method == "get_network_info":
                return await self.get_network_info()
            elif method == "get_processes":
                return await self.get_processes(params.get("limit", 20))
            elif method == "get_process_info":
                return await self.get_process_info(params.get("pid"))
            elif method == "kill_process":
                return await self.kill_process(params.get("pid"))
            elif method == "start_monitoring":
                return await self.start_monitoring(params.get("interval", 5))
            elif method == "stop_monitoring":
                return await self.stop_monitoring()
            elif method == "get_temperatures":
                return await self.get_temperatures()
            elif method == "get_battery":
                return await self.get_battery()
            else:
                return {"error": f"Unknown method: {method}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get basic system information"""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            
            result = {
                "success": True,
                "system": {
                    "platform": psutil.POSIX if hasattr(psutil, 'POSIX') else "unknown",
                    "boot_time": boot_time.isoformat(),
                    "uptime_seconds": time.time() - psutil.boot_time(),
                    "users": [{"name": user.name, "terminal": user.terminal} for user in psutil.users()]
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await self.send_to_dashboard({
                "type": "system_info",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information and usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
            cpu_freq = psutil.cpu_freq()
            
            result = {
                "success": True,
                "cpu": {
                    "count_logical": psutil.cpu_count(logical=True),
                    "count_physical": psutil.cpu_count(logical=False),
                    "usage_percent": psutil.cpu_percent(interval=1),
                    "usage_per_core": cpu_percent,
                    "frequency": {
                        "current": cpu_freq.current if cpu_freq else None,
                        "min": cpu_freq.min if cpu_freq else None,
                        "max": cpu_freq.max if cpu_freq else None
                    } if cpu_freq else None,
                    "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await self.send_to_dashboard({
                "type": "cpu_info",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_memory_info(self) -> Dict[str, Any]:
        """Get memory information"""
        try:
            virtual_mem = psutil.virtual_memory()
            swap_mem = psutil.swap_memory()
            
            result = {
                "success": True,
                "memory": {
                    "virtual": {
                        "total": virtual_mem.total,
                        "available": virtual_mem.available,
                        "used": virtual_mem.used,
                        "free": virtual_mem.free,
                        "percent": virtual_mem.percent
                    },
                    "swap": {
                        "total": swap_mem.total,
                        "used": swap_mem.used,
                        "free": swap_mem.free,
                        "percent": swap_mem.percent
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await self.send_to_dashboard({
                "type": "memory_info",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_disk_info(self) -> Dict[str, Any]:
        """Get disk information"""
        try:
            disk_usage = []
            disk_io = psutil.disk_io_counters()
            
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "filesystem": partition.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": round((usage.used / usage.total) * 100, 2)
                    })
                except PermissionError:
                    continue
            
            result = {
                "success": True,
                "disk": {
                    "partitions": disk_usage,
                    "io": {
                        "read_count": disk_io.read_count,
                        "write_count": disk_io.write_count,
                        "read_bytes": disk_io.read_bytes,
                        "write_bytes": disk_io.write_bytes
                    } if disk_io else None
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await self.send_to_dashboard({
                "type": "disk_info",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        try:
            net_io = psutil.net_io_counters()
            net_connections = psutil.net_connections()
            
            # Count connections by status
            connection_stats = {}
            for conn in net_connections:
                status = conn.status
                connection_stats[status] = connection_stats.get(status, 0) + 1
            
            result = {
                "success": True,
                "network": {
                    "io": {
                        "bytes_sent": net_io.bytes_sent,
                        "bytes_recv": net_io.bytes_recv,
                        "packets_sent": net_io.packets_sent,
                        "packets_recv": net_io.packets_recv,
                        "errors_in": net_io.errin,
                        "errors_out": net_io.errout,
                        "drops_in": net_io.dropin,
                        "drops_out": net_io.dropout
                    } if net_io else None,
                    "connections": {
                        "total": len(net_connections),
                        "by_status": connection_stats
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
            
            await self.send_to_dashboard({
                "type": "network_info",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_processes(self, limit: int = 20) -> Dict[str, Any]:
        """Get running processes"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            result = {
                "success": True,
                "processes": processes[:limit],
                "total_count": len(processes),
                "timestamp": datetime.now().isoformat()
            }
            
            await self.send_to_dashboard({
                "type": "processes_info",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_process_info(self, pid: int) -> Dict[str, Any]:
        """Get detailed process information"""
        try:
            proc = psutil.Process(pid)
            
            result = {
                "success": True,
                "process": {
                    "pid": proc.pid,
                    "name": proc.name(),
                    "username": proc.username(),
                    "status": proc.status(),
                    "created": datetime.fromtimestamp(proc.create_time()).isoformat(),
                    "cpu_percent": proc.cpu_percent(),
                    "memory_percent": proc.memory_percent(),
                    "memory_info": proc.memory_info()._asdict(),
                    "cmdline": proc.cmdline(),
                    "cwd": proc.cwd() if proc.cwd() else None,
                    "num_threads": proc.num_threads(),
                    "num_fds": proc.num_fds() if hasattr(proc, 'num_fds') else None
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except psutil.NoSuchProcess:
            return {"error": f"Process {pid} not found"}
        except psutil.AccessDenied:
            return {"error": f"Access denied to process {pid}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def kill_process(self, pid: int) -> Dict[str, Any]:
        """Kill a process"""
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
            proc.terminate()
            
            result = {
                "success": True,
                "pid": pid,
                "name": proc_name,
                "action": "terminated"
            }
            
            await self.send_to_dashboard({
                "type": "process_killed",
                **result
            })
            
            return result
            
        except psutil.NoSuchProcess:
            return {"error": f"Process {pid} not found"}
        except psutil.AccessDenied:
            return {"error": f"Access denied to kill process {pid}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_temperatures(self) -> Dict[str, Any]:
        """Get system temperatures"""
        try:
            temps = psutil.sensors_temperatures() if hasattr(psutil, 'sensors_temperatures') else {}
            
            result = {
                "success": True,
                "temperatures": temps,
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_battery(self) -> Dict[str, Any]:
        """Get battery information"""
        try:
            battery = psutil.sensors_battery() if hasattr(psutil, 'sensors_battery') else None
            
            if battery:
                result = {
                    "success": True,
                    "battery": {
                        "percent": battery.percent,
                        "seconds_left": battery.secsleft,
                        "power_plugged": battery.power_plugged
                    },
                    "timestamp": datetime.now().isoformat()
                }
            else:
                result = {
                    "success": True,
                    "battery": None,
                    "message": "No battery found"
                }
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def start_monitoring(self, interval: int = 5) -> Dict[str, Any]:
        """Start continuous monitoring"""
        if self.monitoring_active:
            return {"error": "Monitoring already active"}
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop(interval))
        
        return {
            "success": True,
            "message": f"Monitoring started with {interval}s interval"
        }
    
    async def stop_monitoring(self) -> Dict[str, Any]:
        """Stop continuous monitoring"""
        if not self.monitoring_active:
            return {"error": "Monitoring not active"}
        
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        return {
            "success": True,
            "message": "Monitoring stopped"
        }
    
    async def _monitoring_loop(self, interval: int):
        """Continuous monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect basic metrics
                metrics = {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_usage": psutil.disk_usage('/').percent,
                    "timestamp": datetime.now().isoformat()
                }
                
                await self.send_to_dashboard({
                    "type": "monitoring_update",
                    "metrics": metrics
                })
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Monitoring error: {e}")
                await asyncio.sleep(interval)
    
    async def send_to_dashboard(self, data: Dict[str, Any]):
        """Send data to dashboard WebSocket"""
        if self.dashboard_ws:
            try:
                await self.dashboard_ws.send(json.dumps(data))
            except Exception as e:
                print(f"Failed to send to dashboard: {e}")
    
    async def close(self):
        """Clean up resources"""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
        if self.dashboard_ws:
            await self.dashboard_ws.close()

async def main():
    server = MonitoringMCPServer()
    await server.start()
    
    print("📊 System Monitoring MCP Server started")
    print("Monitoring system metrics...")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        await server.close()

if __name__ == "__main__":
    asyncio.run(main())