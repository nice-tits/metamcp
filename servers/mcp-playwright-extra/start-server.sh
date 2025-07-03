#!/bin/bash

# MCP Playwright Extra Server Launcher
# Usage: ./start-server.sh [--test]

cd "$(dirname "$0")"

if [ "$1" = "--test" ]; then
    echo "Running server test..."
    node test-full.js
else
    echo "Starting MCP Playwright Extra Server..."
    echo "Press Ctrl+C to stop"
    node index.js
fi