# Task 3: The System Agent - Implementation Plan

## Overview
Add `query_api` tool to the existing documentation agent, enabling it to interact with the deployed backend service.

## Initial Benchmark Run
First run of `uv run run_eval.py` will show current failures. Will update this section after first run.

## Tool Design: `query_api`

### Parameters
- `method` (string): HTTP method (GET, POST, etc.)
- `path` (string): API endpoint path (e.g., "/items/", "/analytics/scores")
- `body` (string, optional): JSON request body for POST requests

### Returns
JSON string with:
- `status_code`: HTTP status code
- `body`: Response body
- `error`: Error message if any

### Authentication
- Use `LMS_API_KEY` from environment variables
- Add as `Authorization: Bearer {LMS_API_KEY}` header
- Read from `.env.docker.secret` locally, injected by autochecker

### Base URL
- Read from `AGENT_API_BASE_URL` environment variable
- Default to `http://localhost:42002` for local development

## System Prompt Updates
Add instructions for when to use each tool:

1. **Documentation questions** → use `list_files` + `read_file`
2. **System facts** (framework, ports, status codes) → use `read_file` on source code
3. **Live data questions** (item count, analytics) → use `query_api`
4. **Debug questions** → use `query_api` + `read_file` combination

## Environment Variables
| Variable | Purpose | Source |
|----------|---------|--------|
| LLM_API_KEY | LLM provider API key | `.env.agent.secret` |
| LLM_API_BASE | LLM API endpoint | `.env.agent.secret` |
| LLM_MODEL | Model name | `.env.agent.secret` |
| LMS_API_KEY | Backend API auth | `.env.docker.secret` |
| AGENT_API_BASE_URL | Backend base URL | Optional, defaults to localhost |

## Implementation Steps

### 1. Environment Setup
- Load `LMS_API_KEY` from environment
- Load `AGENT_API_BASE_URL` with default

### 2. Tool Schema Definition
Add to `TOOLS` list in `agent.py`:
```python
{
    "type": "function",
    "function": {
        "name": "query_api",
        "description": "Send HTTP request to the backend API. Use this to get live data from the system.",
        "parameters": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE"],
                    "description": "HTTP method"
                },
                "path": {
                    "type": "string",
                    "description": "API endpoint path (e.g., '/items/', '/analytics/scores?lab=lab-05')"
                },
                "body": {
                    "type": "string",
                    "description": "Optional JSON request body for POST requests"
                }
            },
            "required": ["method", "path"]
        }
    }
}
3. Tool Implementation
python
def query_api(method: str, path: str, body: str = None) -> str:
    """Call the backend API"""
    base_url = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')
    url = f"{base_url}{path}"
    headers = {
        "Authorization": f"Bearer {os.getenv('LMS_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.request(method, url, headers=headers, json=json.loads(body) if body else None)
        return json.dumps({
            "status_code": response.status_code,
            "body": response.text
        })
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "status_code": 500,
            "body": None
        })
4. Update Agentic Loop
Add query_api to tool execution mapping

Ensure proper error handling

5. Testing Strategy
Two new regression tests:

System fact question: "What framework does the backend use?" → expects read_file

Data question: "How many items are in the database?" → expects query_api

Benchmark Iteration Plan
Run uv run run_eval.py to see initial failures

Fix questions one by one:

Improve tool descriptions if LLM doesn't call correct tool

Fix tool implementations if they return errors

Adjust system prompt for better reasoning

Re-run benchmark after each fix

Document lessons learned

Security Considerations
LMS_API_KEY never logged or exposed

Validate paths to prevent injection

Timeout for API calls (10 seconds)

Error handling for malformed responses

Final Deliverables
plans/task-3.md with plan and benchmark results

Updated agent.py with query_api tool

Updated AGENT.md with documentation

2 new regression tests

run_eval.py passes all 10 questions
