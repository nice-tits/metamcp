#!/usr/bin/env node

// Test browser functionality
import { spawn } from 'child_process';

console.log('Testing browser launch functionality...\n');

const serverProcess = spawn('node', ['index.js'], {
  stdio: ['pipe', 'pipe', 'pipe'],
  cwd: process.cwd()
});

let stdoutData = '';
let stderrData = '';

serverProcess.stdout.on('data', (data) => {
  stdoutData += data.toString();
});

serverProcess.stderr.on('data', (data) => {
  stderrData += data.toString();
});

// Initialize MCP
setTimeout(() => {
  const initRequest = {
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "test-client", version: "1.0.0" }
    }
  };
  serverProcess.stdin.write(JSON.stringify(initRequest) + '\n');
}, 500);

// Test browser launch
setTimeout(() => {
  console.log('Testing browser launch...');
  const browserRequest = {
    jsonrpc: "2.0",
    id: 2,
    method: "tools/call",
    params: {
      name: "launch_browser",
      arguments: {
        headless: true
      }
    }
  };
  serverProcess.stdin.write(JSON.stringify(browserRequest) + '\n');
}, 1500);

// Close browser
setTimeout(() => {
  console.log('Closing browser...');
  const closeRequest = {
    jsonrpc: "2.0",
    id: 3,
    method: "tools/call",
    params: {
      name: "close_browser",
      arguments: {}
    }
  };
  serverProcess.stdin.write(JSON.stringify(closeRequest) + '\n');
}, 8000);

// End test
setTimeout(() => {
  console.log('\nTest Results:');
  console.log('STDOUT:');
  console.log(stdoutData);
  console.log('\nSTDERR:');
  console.log(stderrData);
  
  if (stdoutData.includes('Browser launched successfully')) {
    console.log('\n✅ Browser launch test passed');
  } else {
    console.log('\n❌ Browser launch test failed');
  }
  
  serverProcess.kill();
  process.exit(0);
}, 10000);

serverProcess.on('error', (error) => {
  console.log('❌ Server process error:', error.message);
  process.exit(1);
});