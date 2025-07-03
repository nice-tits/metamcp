"""
Web Scraping MCP Server
Provides web scraping capabilities using BeautifulSoup and requests for the AI Commander dashboard.
"""

import asyncio
import json
import requests
from bs4 import BeautifulSoup
import time
import uuid
from typing import Dict, Any, List, Optional
import websockets
from urllib.parse import urljoin, urlparse
import re


class WebScrapingMCPServer:
    def __init__(self, host: str = "localhost", port: int = 8087):
        self.host = host
        self.port = port
        self.dashboard_connections = set()
        self.scraping_history = []
        self.session = requests.Session()
        
        # Default headers to appear more like a regular browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    async def start_server(self):
        """Start the MCP server"""
        print(f"Starting Web Scraping MCP Server on {self.host}:{self.port}")
        
        async def handle_client(websocket, path):
            self.dashboard_connections.add(websocket)
            try:
                await websocket.send(json.dumps({
                    "type": "connection_established",
                    "server": "web_scraping",
                    "capabilities": [
                        "scrape_url",
                        "scrape_multiple_urls",
                        "extract_links",
                        "extract_images",
                        "extract_text",
                        "extract_tables",
                        "search_content",
                        "get_page_info",
                        "set_headers",
                        "get_scraping_history",
                        "clear_history"
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
        print(f"Web Scraping MCP Server running on ws://{self.host}:{self.port}")
        
        # Keep server running
        await asyncio.Future()
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "scrape_url":
                return await self._scrape_url(params)
            elif method == "scrape_multiple_urls":
                return await self._scrape_multiple_urls(params)
            elif method == "extract_links":
                return await self._extract_links(params)
            elif method == "extract_images":
                return await self._extract_images(params)
            elif method == "extract_text":
                return await self._extract_text(params)
            elif method == "extract_tables":
                return await self._extract_tables(params)
            elif method == "search_content":
                return await self._search_content(params)
            elif method == "get_page_info":
                return await self._get_page_info(params)
            elif method == "set_headers":
                return await self._set_headers(params)
            elif method == "get_scraping_history":
                return await self._get_scraping_history()
            elif method == "clear_history":
                return await self._clear_history()
            else:
                return {"error": f"Unknown method: {method}"}
                
        except Exception as e:
            return {"error": f"Method execution failed: {str(e)}"}
    
    async def _scrape_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Scrape a single URL and return parsed content"""
        url = params.get("url", "")
        if not url:
            return {"error": "No URL provided"}
        
        timeout = params.get("timeout", 30)
        custom_headers = params.get("headers", {})
        
        scrape_id = str(uuid.uuid4())
        scrape_record = {
            "id": scrape_id,
            "url": url,
            "timestamp": time.time(),
            "status": "scraping"
        }
        
        # Broadcast scraping start to dashboard
        await self._broadcast_to_dashboard({
            "type": "scraping_started",
            "scrape": scrape_record
        })
        
        try:
            # Prepare headers
            headers = dict(self.session.headers)
            headers.update(custom_headers)
            
            # Make request
            response = self.session.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract various elements
            result = {
                "url": url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "title": soup.title.string if soup.title else None,
                "text": soup.get_text(strip=True),
                "html": str(soup),
                "links": [{"text": a.get_text(strip=True), "href": urljoin(url, a.get('href', ''))} 
                         for a in soup.find_all('a', href=True)],
                "images": [{"alt": img.get('alt', ''), "src": urljoin(url, img.get('src', ''))} 
                          for img in soup.find_all('img', src=True)],
                "meta_tags": [{"name": meta.get('name', ''), "content": meta.get('content', '')} 
                             for meta in soup.find_all('meta')],
                "headings": {
                    f"h{i}": [h.get_text(strip=True) for h in soup.find_all(f'h{i}')] 
                    for i in range(1, 7)
                }
            }
            
            scrape_record.update({
                "status": "completed",
                "result": result,
                "scrape_time": time.time() - scrape_record["timestamp"]
            })
            
        except requests.exceptions.RequestException as e:
            scrape_record.update({
                "status": "error",
                "error": f"Request failed: {str(e)}",
                "scrape_time": time.time() - scrape_record["timestamp"]
            })
        except Exception as e:
            scrape_record.update({
                "status": "error", 
                "error": str(e),
                "scrape_time": time.time() - scrape_record["timestamp"]
            })
        
        # Add to history
        self.scraping_history.append(scrape_record)
        
        # Keep only last 50 scrapes
        if len(self.scraping_history) > 50:
            self.scraping_history = self.scraping_history[-50:]
        
        # Broadcast completion to dashboard
        await self._broadcast_to_dashboard({
            "type": "scraping_completed",
            "scrape": scrape_record
        })
        
        return {
            "success": scrape_record["status"] == "completed",
            "scrape": scrape_record
        }
    
    async def _scrape_multiple_urls(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Scrape multiple URLs concurrently"""
        urls = params.get("urls", [])
        if not urls:
            return {"error": "No URLs provided"}
        
        timeout = params.get("timeout", 30)
        custom_headers = params.get("headers", {})
        max_concurrent = params.get("max_concurrent", 5)
        
        results = []
        
        async def scrape_single(url):
            return await self._scrape_url({
                "url": url,
                "timeout": timeout,
                "headers": custom_headers
            })
        
        # Process URLs in batches to avoid overwhelming servers
        for i in range(0, len(urls), max_concurrent):
            batch = urls[i:i + max_concurrent]
            batch_results = await asyncio.gather(
                *[scrape_single(url) for url in batch],
                return_exceptions=True
            )
            results.extend(batch_results)
        
        return {
            "success": True,
            "results": results,
            "total_urls": len(urls)
        }
    
    async def _extract_links(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all links from a webpage"""
        url = params.get("url", "")
        if not url:
            return {"error": "No URL provided"}
        
        filter_pattern = params.get("filter_pattern", "")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            links = []
            for a in soup.find_all('a', href=True):
                link_data = {
                    "text": a.get_text(strip=True),
                    "href": urljoin(url, a.get('href')),
                    "title": a.get('title', ''),
                    "target": a.get('target', '')
                }
                
                # Apply filter if provided
                if filter_pattern:
                    if re.search(filter_pattern, link_data["href"]) or re.search(filter_pattern, link_data["text"]):
                        links.append(link_data)
                else:
                    links.append(link_data)
            
            return {
                "success": True,
                "url": url,
                "links": links,
                "total_links": len(links)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _extract_images(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all images from a webpage"""
        url = params.get("url", "")
        if not url:
            return {"error": "No URL provided"}
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            images = []
            for img in soup.find_all('img'):
                img_data = {
                    "src": urljoin(url, img.get('src', '')),
                    "alt": img.get('alt', ''),
                    "title": img.get('title', ''),
                    "width": img.get('width', ''),
                    "height": img.get('height', ''),
                    "class": ' '.join(img.get('class', []))
                }
                images.append(img_data)
            
            return {
                "success": True,
                "url": url,
                "images": images,
                "total_images": len(images)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _extract_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract clean text content from a webpage"""
        url = params.get("url", "")
        if not url:
            return {"error": "No URL provided"}
        
        include_links = params.get("include_links", False)
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "aside"]):
                script.decompose()
            
            # Get text
            if include_links:
                text = soup.get_text()
            else:
                # Remove link text too
                for a in soup.find_all('a'):
                    a.decompose()
                text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return {
                "success": True,
                "url": url,
                "text": text,
                "length": len(text)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _extract_tables(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract table data from a webpage"""
        url = params.get("url", "")
        if not url:
            return {"error": "No URL provided"}
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            tables = []
            for i, table in enumerate(soup.find_all('table')):
                table_data = {
                    "index": i,
                    "rows": []
                }
                
                for row in table.find_all('tr'):
                    row_data = []
                    for cell in row.find_all(['td', 'th']):
                        row_data.append(cell.get_text(strip=True))
                    if row_data:
                        table_data["rows"].append(row_data)
                
                if table_data["rows"]:
                    tables.append(table_data)
            
            return {
                "success": True,
                "url": url,
                "tables": tables,
                "total_tables": len(tables)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _search_content(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for specific content within a webpage"""
        url = params.get("url", "")
        search_term = params.get("search_term", "")
        
        if not url or not search_term:
            return {"error": "URL and search term are required"}
        
        case_sensitive = params.get("case_sensitive", False)
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()
            
            if not case_sensitive:
                search_text = text.lower()
                term = search_term.lower()
            else:
                search_text = text
                term = search_term
            
            matches = []
            start = 0
            while True:
                pos = search_text.find(term, start)
                if pos == -1:
                    break
                
                # Get context around match
                context_start = max(0, pos - 100)
                context_end = min(len(text), pos + len(search_term) + 100)
                context = text[context_start:context_end]
                
                matches.append({
                    "position": pos,
                    "context": context
                })
                
                start = pos + 1
            
            return {
                "success": True,
                "url": url,
                "search_term": search_term,
                "matches": matches,
                "total_matches": len(matches)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_page_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get basic information about a webpage"""
        url = params.get("url", "")
        if not url:
            return {"error": "No URL provided"}
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            info = {
                "url": url,
                "status_code": response.status_code,
                "title": soup.title.string if soup.title else None,
                "description": None,
                "keywords": None,
                "author": None,
                "language": soup.get('lang', ''),
                "content_type": response.headers.get('content-type', ''),
                "content_length": len(response.content),
                "links_count": len(soup.find_all('a', href=True)),
                "images_count": len(soup.find_all('img', src=True)),
                "forms_count": len(soup.find_all('form'))
            }
            
            # Extract meta information
            for meta in soup.find_all('meta'):
                name = meta.get('name', '').lower()
                content = meta.get('content', '')
                
                if name == 'description':
                    info['description'] = content
                elif name == 'keywords':
                    info['keywords'] = content
                elif name == 'author':
                    info['author'] = content
            
            return {
                "success": True,
                "info": info
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _set_headers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set custom headers for future requests"""
        headers = params.get("headers", {})
        
        if headers:
            self.session.headers.update(headers)
        
        return {
            "success": True,
            "current_headers": dict(self.session.headers)
        }
    
    async def _get_scraping_history(self) -> Dict[str, Any]:
        """Get scraping history"""
        return {
            "success": True,
            "history": self.scraping_history
        }
    
    async def _clear_history(self) -> Dict[str, Any]:
        """Clear scraping history"""
        self.scraping_history.clear()
        
        await self._broadcast_to_dashboard({
            "type": "history_cleared"
        })
        
        return {
            "success": True,
            "message": "Scraping history cleared"
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
    server = WebScrapingMCPServer()
    await server.start_server()


if __name__ == "__main__":
    asyncio.run(main())