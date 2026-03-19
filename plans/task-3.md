# Task 3: The System Agent - Implementation Plan

## Overview

Add `query_api` tool to the existing documentation agent, enabling it to interact with the deployed backend service.

## Tool Design: `query_api`

### Parameters

- `method` (string): HTTP method (GET, POST, PUT, DELETE)
- `path` (string): API endpoint path (e.g., "/items/", "/analytics/scores?lab=lab-01")
- `body` (string, optional): JSON request body for POST requests

### Returns

JSON string with:
- `status_code`: HTTP status code
- `body`: Response body (parsed JSON or text)
- `headers`: Response headers (optional)
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

**Important additions:**
- Read each file only ONCE to avoid infinite loops
- Limit exploration to 2-3 relevant files
- Provide best answer even if not perfect

## Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Backend base URL | Optional, defaults to localhost |

## Implementation Steps

### 1. Environment Setup ✓

- Load `LMS_API_KEY` from `.env.docker.secret`
- Load `AGENT_API_BASE_URL` with default `http://localhost:42002`

### 2. Tool Schema Definition ✓

Added to `TOOLS` list in `agent.py`:

```python
{
    "type": "function",
    "function": {
        "name": "query_api",
        "description": "Send HTTP request to the backend API. Use this to get live data from the running system.",
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
                    "description": "API endpoint path (e.g., '/items/', '/analytics/scores?lab=lab-01')"
                },
                "body": {
                    "type": "string",
                    "description": "Optional JSON request body for POST or PUT requests"
                }
            },
            "required": ["method", "path"]
        }
    }
}
```

### 3. Tool Implementation ✓

```python
def query_api(method: str, path: str, body: Optional[str] = None) -> str:
    """Call the backend API with authentication"""
    base_url = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')
    url = f"{base_url}{path}"
    headers = {
        "Authorization": f"Bearer {os.getenv('LMS_API_KEY')}",
        "Content-Type": "application/json"
    }

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=json.loads(body) if body else None
            )
            return json.dumps({
                "status_code": response.status_code,
                "body": response.json() if response.content else None,
                "headers": dict(response.headers)
            })
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "status_code": 500,
            "body": None
        })
```

### 4. Update Agentic Loop ✓

- Added `query_api` to tool execution mapping in `execute_tool()`
- Enhanced `extract_source_from_messages()` to detect API references
- Updated system prompt with clear tool selection guidance

### 5. Testing Strategy ✓

Two new regression tests in `tests/test_agent_task3.py`:

1. **System fact question**: "What framework does the backend use?" → expects `read_file`
2. **Data question**: "How many items are in the database?" → expects `query_api`
3. **API error handling**: "What happens without auth?" → expects 401/403
4. **Combined tools**: "Why does endpoint crash?" → expects both tools

## Benchmark Iteration Plan

1. Run `uv run run_eval.py` to see initial failures
2. Fix questions one by one:
   - Improve tool descriptions if LLM doesn't call correct tool
   - Fix tool implementations if they return errors
   - Adjust system prompt for better reasoning
3. Re-run benchmark after each fix
4. Document lessons learned

## Initial Benchmark Run

**Note**: Full benchmark testing is limited by OpenRouter free tier rate limits (50 requests/day, then requires adding credits for 1000 free requests/day).

### Tested Individually:

| Question Type | Status | Notes |
|---------------|--------|-------|
| Item count (`query_api`) | ✅ Works | Returns 44 items correctly |
| Framework (`read_file`) | ✅ Should work | Reads `backend/app/main.py` |
| Branch protection (`read_file`) | ⏳ Needs testing | Wiki lookup in `github.md` |
| API error (401) | ⏳ Needs testing | Requires auth test |
| Debug (completion-rate) | ⏳ Needs testing | ZeroDivisionError bug |

### Model Selection

After testing multiple free models:

- `google/gemma-3-12b-it:free` — No tool calling support (404)
- `meta-llama/llama-3-70b-instruct:free` — No tool calling support (404)
- `mistralai/mistral-small-3.1-24b-instruct:free` — Rate limited (429)
- `nvidia/nemotron-3-super-120b-a12b:free` — ✅ **Selected** (full tool support)

### Configuration

```python
TIMEOUT = 60  # seconds per LLM request
MAX_TOOL_CALLS = 8  # prevent infinite loops
MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
```

## Security Considerations

- `LMS_API_KEY` never logged or exposed in output
- Path validation prevents directory traversal
- Timeout for API calls (60 seconds)
- Error handling for malformed responses
- File size limits (1MB) for `read_file`

## Final Deliverables

- [x] `plans/task-3.md` with plan and benchmark results
- [x] Updated `agent.py` with `query_api` tool
- [x] Updated `AGENT.md` with documentation (200+ words)
- [x] 2+ regression tests in `tests/test_agent_task3.py`
- [ ] `run_eval.py` passes all 10 questions (blocked by rate limits)
- [ ] Autochecker bot benchmark pass

## Lessons Learned

1. **Tool descriptions are critical**: The LLM needs explicit, detailed descriptions to choose the right tool.

2. **Environment variable separation**: `LMS_API_KEY` (backend) and `LLM_API_KEY` (LLM provider) serve different purposes and must be kept separate.

3. **Free model limitations**: 
   - Rate limits (50 req/day on OpenRouter)
   - Slower response times (10-30s per request)
   - Not all models support tool calling

4. **Loop prevention**: Must explicitly instruct the LLM to not read the same file twice, otherwise it can get stuck.

5. **Source extraction**: Parsing sources from conversation history is more reliable than asking the LLM to format them.

6. **Benchmark-driven development**: Test, identify failure mode, fix, repeat. Don't guess.

## Next Steps

1. Wait for OpenRouter rate limit reset (daily)
2. Run full `run_eval.py` benchmark
3. Fix any failing questions
4. Submit to autochecker bot for final evaluation
5. Complete git workflow: issue, branch, PR, partner review, merge
