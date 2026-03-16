#!/usr/bin/env python3
"""
Documentation Agent with Tool Calling
Task 2: The Documentation Agent - Can read files and list directories in wiki
"""

import os
import sys
import json
import httpx
from dotenv import load_dotenv
import asyncio
from typing import Dict, Any, List, Optional
import base64

# Load environment variables
load_dotenv('.env.agent.secret')

# Configuration
API_KEY = os.getenv('LLM_API_KEY')
API_BASE = os.getenv('LLM_API_BASE', 'https://openrouter.ai/api/v1')
MODEL = os.getenv('LLM_MODEL', 'mistralai/mistral-small-3.1-24b-instruct:free')
TIMEOUT = 55
MAX_TOOL_CALLS = 10

# Get project root directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Store conversation history
messages = []
tool_calls_history = []

def log_debug(msg: str) -> None:
    """Print debug messages to stderr"""
    print(f"[DEBUG] {msg}", file=sys.stderr)

def log_error(msg: str) -> None:
    """Print error messages to stderr"""
    print(f"[ERROR] {msg}", file=sys.stderr)

def validate_path(path: str) -> Optional[str]:
    """
    Validate and normalize path to prevent directory traversal
    Returns absolute path if valid, None if invalid
    """
    # Remove any leading/trailing slashes
    path = path.strip('/')
    
    # Block path traversal attempts
    if '..' in path.split('/'):
        log_error(f"Path traversal attempt blocked: {path}")
        return None
    
    # Construct absolute path
    abs_path = os.path.abspath(os.path.join(PROJECT_ROOT, path))
    
    # Check if path is within project root
    if not abs_path.startswith(PROJECT_ROOT):
        log_error(f"Path outside project root: {path}")
        return None
    
    return abs_path

def list_files(path: str = ".") -> str:
    """
    List files and directories at the given path
    Tool for LLM to discover available documentation
    """
    log_debug(f"list_files called with path: {path}")
    
    # Validate path
    abs_path = validate_path(path)
    if not abs_path:
        return f"Error: Invalid path '{path}'"
    
    # Check if path exists
    if not os.path.exists(abs_path):
        return f"Error: Path '{path}' does not exist"
    
    # Check if it's a directory
    if not os.path.isdir(abs_path):
        return f"Error: '{path}' is not a directory"
    
    try:
        # List directory contents
        items = os.listdir(abs_path)
        
        # Separate files and directories for better readability
        files = []
        dirs = []
        
        for item in sorted(items):
            item_path = os.path.join(abs_path, item)
            if os.path.isdir(item_path):
                dirs.append(f"{item}/")
            else:
                files.append(item)
        
        # Format output
        result = []
        if dirs:
            result.append("Directories:")
            result.extend([f"  {d}" for d in dirs])
        if files:
            if dirs:
                result.append("Files:")
            result.extend([f"  {f}" for f in files])
        
        return "\n".join(result) if result else "Directory is empty"
        
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def read_file(path: str) -> str:
    """
    Read contents of a file
    Tool for LLM to read documentation files
    """
    log_debug(f"read_file called with path: {path}")
    
    # Validate path
    abs_path = validate_path(path)
    if not abs_path:
        return f"Error: Invalid path '{path}'"
    
    # Check if file exists
    if not os.path.exists(abs_path):
        return f"Error: File '{path}' does not exist"
    
    # Check if it's a file (not directory)
    if not os.path.isfile(abs_path):
        return f"Error: '{path}' is not a file"
    
    # Check file size (limit to 1MB)
    file_size = os.path.getsize(abs_path)
    if file_size > 1024 * 1024:  # 1MB
        return f"Error: File too large ({file_size} bytes). Maximum 1MB."
    
    try:
        # Try to read as text
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Truncate if too long (for LLM context)
        if len(content) > 10000:
            content = content[:10000] + "\n... (content truncated)"
        
        return content
        
    except UnicodeDecodeError:
        # If not text file, return base64 encoded
        try:
            with open(abs_path, 'rb') as f:
                content = base64.b64encode(f.read()).decode('utf-8')
            return f"[Binary file, base64 encoded]\n{content[:1000]}..."
        except Exception as e:
            return f"Error reading binary file: {str(e)}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

# Tool definitions for OpenAI function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path. Use this to discover available documentation in the wiki.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki', '.')",
                        "default": "."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file. Use this to read documentation files from the wiki.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to file from project root (e.g., 'wiki/git-workflow.md')"
                    }
                },
                "required": ["path"]
            }
        }
    }
]

# System prompt for the documentation agent
SYSTEM_PROMPT = """You are a documentation agent. Your task is to answer questions using the project wiki.

Available tools:
- list_files(path): Discover wiki files and directories
- read_file(path): Read wiki file contents

Follow this process:
1. First, use list_files("wiki") to see what documentation is available
2. Read relevant files with read_file() to find answers
3. Look for specific sections within files that answer the question
4. When you find the answer, include the source reference (file path and section if applicable)
5. If you can't find the answer, explore more files

Rules:
- Always check the wiki first before answering
- Include the source of your information (file path + section anchor if possible)
- Be concise but informative
- If you're unsure, be honest about what you found

Format source as: path/to/file.md#section (e.g., wiki/git-workflow.md#resolving-merge-conflicts)
"""

def execute_tool(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool and return the result"""
    tool_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])
    
    log_debug(f"Executing tool: {tool_name} with args: {arguments}")
    
    if tool_name == "list_files":
        path = arguments.get("path", ".")
        result = list_files(path)
    elif tool_name == "read_file":
        path = arguments["path"]
        result = read_file(path)
    else:
        result = f"Error: Unknown tool '{tool_name}'"
    
    # Record tool call
    tool_calls_history.append({
        "tool": tool_name,
        "args": arguments,
        "result": result
    })
    
    return {
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "name": tool_name,
        "content": result
    }

async def call_llm_with_tools(current_messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Call LLM with tool support"""
    if not API_KEY:
        log_error("LLM_API_KEY not set in .env.agent.secret")
        return None
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": current_messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    url = f"{API_BASE}/chat/completions"
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            log_debug(f"Sending request to {url}")
            log_debug(f"Model: {MODEL}")
            
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except httpx.TimeoutException:
            log_error(f"Request timed out after {TIMEOUT} seconds")
            return None
        except httpx.HTTPStatusError as e:
            log_error(f"HTTP error: {e.response.status_code}")
            log_error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            log_error(f"Unexpected error: {str(e)}")
            return None

def extract_source_from_messages() -> str:
    """Try to extract source from conversation history"""
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            content = msg["content"]
            if "wiki/" in content and ".md" in content:
                lines = content.split('\n')
                for line in lines:
                    if "wiki/" in line and ".md" in line:
                        parts = line.split()
                        for part in parts:
                            if part.startswith("wiki/") and ".md" in part:
                                return part.strip('.,:;()[]')
    return "wiki/unknown.md"

async def run_agentic_loop(question: str) -> Optional[Dict[str, Any]]:
    """Run the main agentic loop with tool calling"""
    
    global messages, tool_calls_history
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    tool_calls_history = []
    
    tool_call_count = 0
    
    while tool_call_count < MAX_TOOL_CALLS:
        response = await call_llm_with_tools(messages)
        if not response:
            return None
        
        assistant_message = response["choices"][0]["message"]
        messages.append(assistant_message)
        
        if "tool_calls" in assistant_message and assistant_message["tool_calls"]:
            tool_call_count += len(assistant_message["tool_calls"])
            log_debug(f"Tool calls received ({tool_call_count}/{MAX_TOOL_CALLS})")
            
            for tool_call in assistant_message["tool_calls"]:
                tool_result = execute_tool(tool_call)
                messages.append(tool_result)
        else:
            answer = assistant_message.get("content", "")
            source = extract_source_from_messages()
            
            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_history
            }
    
    log_debug(f"Max tool calls ({MAX_TOOL_CALLS}) reached")
    
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            return {
                "answer": msg["content"],
                "source": extract_source_from_messages(),
                "tool_calls": tool_calls_history
            }
    
    return {
        "answer": "I couldn't find a definitive answer after searching the documentation.",
        "source": "wiki/unknown.md",
        "tool_calls": tool_calls_history
    }

async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        log_error("Usage: uv run agent.py \"your question here\"")
        sys.exit(1)
    
    question = sys.argv[1]
    log_debug(f"Question: {question}")
    
    result = await run_agentic_loop(question)
    
    if result:
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)
    else:
        log_error("Failed to get response from LLM")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
