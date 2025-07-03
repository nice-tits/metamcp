#!/usr/bin/env python3
"""
SQLite Database MCP Server
Provides database operations for AI agents
"""

import asyncio
import json
import sqlite3
import os
from typing import Dict, Any, List, Optional
import websockets
from pathlib import Path

class SQLiteMCPServer:
    def __init__(self, db_path: str = "ai_commander.db"):
        self.db_path = Path(db_path).resolve()
        self.dashboard_ws = None
        self._init_database()
        
    def _init_database(self):
        """Initialize database with basic tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    config TEXT,
                    status TEXT DEFAULT 'stopped',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    user_message TEXT,
                    agent_response TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (agent_id) REFERENCES agents (id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    size INTEGER,
                    mime_type TEXT,
                    checksum TEXT,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            
    async def start(self):
        """Initialize database server"""
        try:
            self.dashboard_ws = await websockets.connect("ws://localhost:3001/ws/database")
            print("✅ Connected to dashboard WebSocket")
        except Exception as e:
            print(f"⚠️  Dashboard WebSocket not available: {e}")
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "query":
                return await self.execute_query(params.get("sql"), params.get("params", []))
            elif method == "insert":
                return await self.insert_data(params.get("table"), params.get("data"))
            elif method == "update":
                return await self.update_data(params.get("table"), params.get("data"), params.get("where"))
            elif method == "delete":
                return await self.delete_data(params.get("table"), params.get("where"))
            elif method == "get_tables":
                return await self.get_tables()
            elif method == "get_schema":
                return await self.get_schema(params.get("table"))
            elif method == "backup":
                return await self.backup_database(params.get("path"))
            elif method == "restore":
                return await self.restore_database(params.get("path"))
            else:
                return {"error": f"Unknown method: {method}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def execute_query(self, sql: str, params: List = None) -> Dict[str, Any]:
        """Execute SQL query"""
        if not sql:
            return {"error": "No SQL query provided"}
        
        # Basic SQL injection protection
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
        sql_upper = sql.upper().strip()
        
        if any(keyword in sql_upper for keyword in dangerous_keywords) and not sql_upper.startswith('SELECT'):
            return {"error": "Only SELECT queries allowed via execute_query method"}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(sql, params or [])
                
                if sql_upper.startswith('SELECT'):
                    rows = [dict(row) for row in cursor.fetchall()]
                    result = {
                        "success": True,
                        "rows": rows,
                        "count": len(rows)
                    }
                else:
                    result = {
                        "success": True,
                        "rows_affected": cursor.rowcount
                    }
                
                await self.send_to_dashboard({
                    "type": "query_result",
                    "sql": sql,
                    **result
                })
                
                return result
                
        except Exception as e:
            error_result = {"error": str(e), "sql": sql}
            await self.send_to_dashboard({
                "type": "query_error",
                **error_result
            })
            return error_result
    
    async def insert_data(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert data into table"""
        try:
            columns = list(data.keys())
            placeholders = ', '.join(['?' for _ in columns])
            values = list(data.values())
            
            sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(sql, values)
                conn.commit()
                
                result = {
                    "success": True,
                    "table": table,
                    "inserted_id": cursor.lastrowid,
                    "rows_affected": cursor.rowcount
                }
                
                await self.send_to_dashboard({
                    "type": "data_inserted",
                    **result
                })
                
                return result
                
        except Exception as e:
            return {"error": str(e)}
    
    async def update_data(self, table: str, data: Dict[str, Any], where: Dict[str, Any]) -> Dict[str, Any]:
        """Update data in table"""
        try:
            set_clause = ', '.join([f"{col} = ?" for col in data.keys()])
            where_clause = ' AND '.join([f"{col} = ?" for col in where.keys()])
            
            sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
            values = list(data.values()) + list(where.values())
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(sql, values)
                conn.commit()
                
                result = {
                    "success": True,
                    "table": table,
                    "rows_affected": cursor.rowcount
                }
                
                await self.send_to_dashboard({
                    "type": "data_updated",
                    **result
                })
                
                return result
                
        except Exception as e:
            return {"error": str(e)}
    
    async def delete_data(self, table: str, where: Dict[str, Any]) -> Dict[str, Any]:
        """Delete data from table"""
        try:
            where_clause = ' AND '.join([f"{col} = ?" for col in where.keys()])
            sql = f"DELETE FROM {table} WHERE {where_clause}"
            values = list(where.values())
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(sql, values)
                conn.commit()
                
                result = {
                    "success": True,
                    "table": table,
                    "rows_affected": cursor.rowcount
                }
                
                await self.send_to_dashboard({
                    "type": "data_deleted",
                    **result
                })
                
                return result
                
        except Exception as e:
            return {"error": str(e)}
    
    async def get_tables(self) -> Dict[str, Any]:
        """Get list of tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                return {
                    "success": True,
                    "tables": tables
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    async def get_schema(self, table: str) -> Dict[str, Any]:
        """Get table schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(f"PRAGMA table_info({table})")
                columns = []
                for row in cursor.fetchall():
                    columns.append({
                        "name": row[1],
                        "type": row[2],
                        "not_null": bool(row[3]),
                        "default": row[4],
                        "primary_key": bool(row[5])
                    })
                
                return {
                    "success": True,
                    "table": table,
                    "columns": columns
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    async def backup_database(self, backup_path: str) -> Dict[str, Any]:
        """Backup database"""
        try:
            backup_path = Path(backup_path).resolve()
            
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            
            result = {
                "success": True,
                "backup_path": str(backup_path),
                "size": backup_path.stat().st_size
            }
            
            await self.send_to_dashboard({
                "type": "database_backed_up",
                **result
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def restore_database(self, backup_path: str) -> Dict[str, Any]:
        """Restore database from backup"""
        try:
            backup_path = Path(backup_path).resolve()
            
            if not backup_path.exists():
                return {"error": f"Backup file not found: {backup_path}"}
            
            # Create backup of current database
            current_backup = self.db_path.with_suffix('.backup')
            
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(current_backup) as backup:
                    source.backup(backup)
            
            # Restore from backup
            with sqlite3.connect(backup_path) as source:
                with sqlite3.connect(self.db_path) as target:
                    source.backup(target)
            
            result = {
                "success": True,
                "restored_from": str(backup_path),
                "backup_created": str(current_backup)
            }
            
            await self.send_to_dashboard({
                "type": "database_restored",
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
    db_path = os.getenv("SQLITE_DB_PATH", "ai_commander.db")
    server = SQLiteMCPServer(db_path)
    await server.start()
    
    print("🗄️  SQLite MCP Server started")
    print(f"Database: {server.db_path}")
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