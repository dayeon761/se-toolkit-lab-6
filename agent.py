#!/usr/bin/env python3
"""
System Agent with Tool Calling
Task 3: The System Agent - Can read wiki, source code, and query the backend API
"""

import os
import sys
import json
import httpx
from dotenv import load_dotenv
import asyncio
from typing import Dict, Any, List, Optional
import base64

# Load environment variables from both files
load_dotenv('.env.agent.secret')
load_dotenv('.env.docker.secret', override=False)

# Configuration - use Groq if available and working, otherwise OpenRouter
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
USE_GROQ = False

if GROQ_API_KEY and len(GROQ_API_KEY) > 10:
    # Use Groq API (faster, free tier available)
    API_KEY = GROQ_API_KEY
    API_BASE = 'https://api.groq.com/openai/v1'
    MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-70b-versatile')
    TIMEOUT = 30
    USE_GROQ = True
else:
    # Fallback to OpenRouter
    API_KEY = os.getenv('LLM_API_KEY')
    API_BASE = os.getenv('LLM_API_BASE', 'https://openrouter.ai/api/v1')
    MODEL = os.getenv('LLM_MODEL', 'meta-llama/llama-3-8b-instruct:free')
    TIMEOUT = 60

MAX_TOOL_CALLS = 12

# Backend API configuration
LMS_API_KEY = os.getenv('LMS_API_KEY')
AGENT_API_BASE_URL = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')

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
    Tool for LLM to read documentation files or source code
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

def query_api(method: str, path: str, body: Optional[str] = None) -> str:
    """
    Call the backend API with authentication
    Tool for LLM to get live data from the system
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        path: API endpoint path (e.g., '/items/', '/analytics/scores?lab=lab-01')
        body: Optional JSON request body for POST/PUT requests
    
    Returns:
        JSON string with status_code, body, and error if any
    """
    log_debug(f"query_api called: {method} {path}")
    
    if not LMS_API_KEY:
        log_error("LMS_API_KEY not set in environment")
        return json.dumps({
            "error": "LMS_API_KEY not configured",
            "status_code": 500,
            "body": None
        })
    
    # Build full URL
    base_url = AGENT_API_BASE_URL.rstrip('/')
    full_url = f"{base_url}{path}"
    
    headers = {
        "Authorization": f"Bearer {LMS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Parse body if provided
        json_body = None
        if body:
            json_body = json.loads(body)
        
        # Make the request synchronously (httpx supports async but we keep it simple)
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.request(
                method=method.upper(),
                url=full_url,
                headers=headers,
                json=json_body
            )
            
            # Try to parse response as JSON
            try:
                response_body = response.json()
            except json.JSONDecodeError:
                response_body = response.text
            
            return json.dumps({
                "status_code": response.status_code,
                "body": response_body,
                "headers": dict(response.headers)
            })
            
    except httpx.TimeoutException:
        log_error(f"API request timed out after {TIMEOUT} seconds")
        return json.dumps({
            "error": f"Request timed out after {TIMEOUT} seconds",
            "status_code": 504,
            "body": None
        })
    except httpx.HTTPError as e:
        log_error(f"HTTP error: {str(e)}")
        return json.dumps({
            "error": str(e),
            "status_code": getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500,
            "body": None
        })
    except json.JSONDecodeError as e:
        log_error(f"Invalid JSON body: {str(e)}")
        return json.dumps({
            "error": f"Invalid JSON body: {str(e)}",
            "status_code": 400,
            "body": None
        })
    except Exception as e:
        log_error(f"Unexpected error in query_api: {str(e)}")
        return json.dumps({
            "error": str(e),
            "status_code": 500,
            "body": None
        })

# Tool definitions for OpenAI function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path. Use this to discover available documentation in the wiki or explore the project structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki', '.', 'backend/app')",
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
            "description": "Read contents of a file. Use this to read wiki documentation, source code files, or configuration files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to file from project root (e.g., 'wiki/git-workflow.md', 'backend/app/main.py', 'docker-compose.yml')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Send HTTP request to the backend API. Use this to get live data from the running system (e.g., item count, analytics, scores). For authentication, automatically uses LMS_API_KEY. Use GET for reading data, POST for creating, PUT for updating, DELETE for removing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                        "description": "HTTP method to use"
                    },
                    "path": {
                        "type": "string",
                        "description": "API endpoint path (e.g., '/items/', '/analytics/scores?lab=lab-01', '/analytics/completion-rate?lab=lab-99')"
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body for POST or PUT requests (e.g., '{\"title\": \"New Item\"}')"
                    }
                },
                "required": ["method", "path"]
            }
        }
    }
]

# System prompt for the system agent
SYSTEM_PROMPT = """You are a system agent that can answer questions about this project using multiple tools.

Available tools:
- list_files(path): Discover files and directories in the project
- read_file(path): Read file contents (wiki docs, source code, configs)
- query_api(method, path, body): Send HTTP requests to the backend API for live data

How to choose the right tool:

1. **Documentation questions** (wiki how-tos, git workflow, SSH setup, branch protection):
   - Use list_files("wiki") to explore available wiki files
   - Use read_file() to read specific wiki files
   - IMPORTANT: Read each file ONCE. If you don't find the answer after reading 2-3 relevant files, summarize what you found.
   - Look for section headers within files (e.g., "### Protect a branch")
   - For "how to" questions, look for numbered steps in the file

2. **System facts** (framework, ports, architecture, code structure):
   - Use read_file() on source code (backend/app/*.py, docker-compose.yml, etc.)
   - Look for imports, configurations, router definitions

3. **Live data questions** (item count, scores, analytics, completion rates):
   - Use query_api("GET", "/items/") to get all items
   - Use query_api("GET", "/analytics/scores?lab=lab-01") for analytics
   - Use query_api("GET", "/analytics/completion-rate?lab=lab-01") for completion rate

4. **Debug questions** (why does endpoint crash, what's the bug):
   - First use query_api() to see the error response
   - Then use read_file() on the relevant source code to find the bug
   - Look for division by zero, None handling, missing checks

5. **Authentication questions** (what happens without auth):
   - Use query_api() WITHOUT the Authorization header to test
   - Note: by default query_api includes auth, so you may need to mention this limitation

Rules:
- Include the source of your information (file path for code, or mention "API response")
- Be concise but informative
- For API calls, include the status code and relevant data from the response
- DO NOT read the same file more than once - keep track of what you've already read
- If you've read 3+ files without finding the answer, provide your best answer based on what you found
- If stuck, try a different approach (e.g., search a different directory)
- ALWAYS provide an answer, even if incomplete - never return null or empty

Format source as:
- For wiki: wiki/file.md#section (e.g., wiki/github.md#protect-a-branch)
- For code: path/to/file.py
- For API: api:endpoint (e.g., api:/items/)

Examples:
- "How many items?" → query_api("GET", "/items/") → count the array
- "What framework?" → read_file("backend/app/main.py") → look for FastAPI import
- "How to protect branch?" → read_file("wiki/github.md") → find "Protect a branch" section → list the steps
- "Why does /analytics/completion-rate crash?" → query_api to see error, then read_file("backend/app/routers/analytics.py") to find the bug

IMPORTANT: Always return a non-empty answer. If you found information, summarize it. If not found, say so clearly.
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
    elif tool_name == "query_api":
        method = arguments.get("method", "GET")
        path = arguments["path"]
        body = arguments.get("body")
        result = query_api(method, path, body)
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
            # Check for wiki references
            if "wiki/" in content and ".md" in content:
                lines = content.split('\n')
                for line in lines:
                    if "wiki/" in line and ".md" in line:
                        parts = line.split()
                        for part in parts:
                            if part.startswith("wiki/") and ".md" in part:
                                return part.strip('.,:;()[]')
            # Check for code file references
            if ".py" in content or ".yml" in content or "docker" in content.lower():
                # Look for file paths
                import re
                matches = re.findall(r'\b(backend/[\w/.]+\.py|docker-compose\.yml|Dockerfile)\b', content)
                if matches:
                    return matches[0]
            # Check for API references
            if "api:" in content.lower() or "/items" in content or "/analytics" in content:
                return "api:live_data"
    return ""

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

    # Return the last assistant message
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            return {
                "answer": msg["content"],
                "source": extract_source_from_messages(),
                "tool_calls": tool_calls_history
            }

    return {
        "answer": "I couldn't find a definitive answer after searching the documentation.",
        "source": "",
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
