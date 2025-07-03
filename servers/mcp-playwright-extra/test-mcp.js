#!/usr/bin/env node

// Simple MCP client test for the playwright-extra server
import { spawn } from 'child_process';
import { readFileSync } from 'fs';

console.log('Testing MCP Playwright Extra Server...\n');

// Test 1: Check if server starts without errors
console.log('1. Testing server startup...');
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

// Send MCP initialization request
setTimeout(() => {
  console.log('2. Sending MCP initialization request...');
  const initRequest = {
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2024-11-05",
      capabilities: {
        roots: {
          listChanged: true
        },
        sampling: {}
      },
      clientInfo: {
        name: "test-client",
        version: "1.0.0"
      }
    }
  };
  
  serverProcess.stdin.write(JSON.stringify(initRequest) + '\n');
}, 1000);

// Send tools list request
setTimeout(() => {
  console.log('3. Requesting tools list...');
  const toolsRequest = {
    jsonrpc: "2.0",
    id: 2,
    method: "tools/list",
    params: {}
  };
  
  serverProcess.stdin.write(JSON.stringify(toolsRequest) + '\n');
}, 2000);

// End test after 3 seconds
setTimeout(() => {
  console.log('\n4. Test Results:');
  console.log('STDOUT:');
  console.log(stdoutData || '(no stdout output)');
  console.log('\nSTDERR:');
  console.log(stderrData || '(no stderr output)');
  
  if (stderrData.includes('MCP Playwright Extra server running')) {
    console.log('\n✅ Server started successfully');
  } else {
    console.log('\n❌ Server startup issue detected');
  }
  
  if (stdoutData.includes('"result"') && stdoutData.includes('tools')) {
    console.log('✅ MCP protocol working correctly');
  } else {
    console.log('❌ MCP protocol communication issue');
  }
  
  serverProcess.kill();
  process.exit(0);
}, 3000);

serverProcess.on('error', (error) => {
  console.log('❌ Server process error:', error.message);
  process.exit(1);
});

serverProcess.on('exit', (code) => {
  if (code !== null && code !== 0) {
    console.log(`❌ Server exited with code: ${code}`);
  }
});