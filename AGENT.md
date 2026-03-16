# Agent Documentation

## Overview
This is a system agent that answers questions using three types of tools:
1. **Wiki documentation** - via `list_files` and `read_file`
2. **Source code analysis** - via `read_file`
3. **Live API data** - via `query_api`

The agent uses an agentic loop to call tools, process results, and refine answers until it finds the information needed.

## Task 1: Basic LLM Agent
### Implementation
Simple CLI agent that calls OpenRouter API and returns JSON responses.

## Task 2: Documentation Agent
### New Features
- **Tool Calling**: Agent can use `list_files` and `read_file` to navigate the wiki
- **Agentic Loop**: Automatically calls tools and processes results
- **Source Tracking**: Output includes source file reference

### Available Tools (Task 2)

#### 1. `list_files(path)`
- Lists files and directories at specified path
- Used to discover wiki documentation
- Example: `list_files("wiki")`
- Security: Path traversal protection (blocks `..`)

#### 2. `read_file(path)`
- Reads contents of a file
- Used to read wiki documentation or source code
- Example: `read_file("wiki/git-workflow.md")`
- Security: Files outside project root are inaccessible, 1MB size limit

## Task 3: System Agent (Current)

### New Tool: `query_api`

The agent now can interact with the live backend API through the `query_api` tool.

#### Parameters
- `method` (string): HTTP method (GET, POST, PUT, DELETE)
- `path` (string): API endpoint path (e.g., "/items/", "/analytics/scores?lab=lab-05")
- `body` (string, optional): JSON request body for POST/PUT requests

#### Returns
JSON string with:
- `status_code`: HTTP status code
- `body`: Response body
- `headers`: Response headers
- `error`: Error message if any

#### Authentication
- Uses `LMS_API_KEY` from environment variables
- Sent as `Authorization: Bearer {LMS_API_KEY}` header
- Loaded from `.env.docker.secret`

#### Base URL
- Reads from `AGENT_API_BASE_URL` environment variable
- Defaults to `http://localhost:42002` for local development

### Agentic Loop Enhancement

The agent now follows an improved decision process:

1. **Documentation questions** → Use `list_files` + `read_file` on wiki
2. **System facts** (framework, ports, structure) → Use `read_file` on source code
3. **Live data questions** (item count, analytics) → Use `query_api`
4. **Debug questions** → Combine `query_api` (to see error) + `read_file` (to find bug)

### System Prompt Strategy
The system prompt explicitly guides the LLM to:
- Check wiki first for documentation
- Explore source code for implementation questions
- Use API for live data
- Combine tools for debugging
- Include source references when available

### Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for `query_api` auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Backend base URL (optional) | Defaults to `http://localhost:42002` |

**Important**: The autochecker injects its own values for all these variables. Never hardcode them.

### Output Format
```json
{
  "answer": "The answer to your question",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",  // Optional for system questions
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": [...]}"
    }
  ]
}
Benchmark Results
Initial Run
After implementing query_api, running uv run run_eval.py showed:

✅ Documentation questions (wiki lookup, SSH steps)

✅ System fact questions (framework identification)

✅ Simple data questions (item count)

❌ Debug questions requiring API error + code analysis

❌ Complex reasoning questions (request lifecycle)

Iterations and Improvements
Iteration 1: Tool Description Enhancement
Problem: Agent wasn't using query_api for data questions consistently.
Fix: Enhanced tool description to explicitly mention "live data" and "item count".

Iteration 2: Error Handling
Problem: Agent crashed when API returned non-JSON responses.
Fix: Added robust error handling in query_api tool.

Iteration 3: Debug Flow
Problem: Agent couldn't connect API errors to source code bugs.
Fix: Updated system prompt to encourage two-step debugging: API call → read relevant code.

Iteration 4: Source Extraction
Problem: Source field was empty for code questions.
Fix: Enhanced extract_source_from_messages() to detect both wiki and code paths.

Final Benchmark Score
After iterations, the agent passes all 10 local questions in run_eval.py:

text
✓ [1/10] According to the project wiki, what steps are needed to protect a branch?
✓ [2/10] What Python web framework does this project use?
✓ [3/10] How many items are in the database?
✓ [4/10] Query the /analytics/completion-rate endpoint for lab-99...
✓ [5/10] What HTTP status code for /items/ without auth?
✓ [6/10] Explain the error in /analytics/completion-rate for lab-99
✓ [7/10] Debug /analytics/top-learners crash
✓ [8/10] Explain HTTP request lifecycle
✓ [9/10] How does ETL ensure idempotency?
✓ [10/10] Compare API error handling strategies

10/10 passed
Testing
Task 1 Test
bash
python3 tests/test_agent.py
Tests basic LLM calling and JSON output format.

Task 2 Tests
bash
python3 tests/test_agent_task2.py
Tests:

list_files tool usage for wiki discovery

read_file tool usage for documentation

Path security

Tool call structure

Task 3 Tests
bash
python3 tests/test_agent_task3.py
Tests:

System fact questions (framework) → expects read_file

Data questions (item count) → expects query_api

API error handling → expects status code detection

Usage Examples
Documentation Question
bash
uv run agent.py "How do you resolve a merge conflict?"
Output includes wiki source and file reading.

System Fact Question
bash
uv run agent.py "What framework does the backend use?"
Output includes source code path and framework name.

Live Data Question
bash
uv run agent.py "How many items are in the database?"
Output includes count from API and query_api tool calls.

Debug Question
bash
uv run agent.py "Why does /analytics/top-learners crash for some labs?"
Output combines API error diagnosis with code analysis.

Lessons Learned
Tool descriptions matter: The LLM needs clear, specific descriptions to choose the right tool.

Error handling is critical: API calls can fail in many ways; the agent must handle gracefully.

System prompt engineering: Explicit instructions about when to use each tool improve accuracy.

Source tracking: Extracting sources from conversation context works better than relying on LLM to format them.

Authentication separation: Keeping LMS_API_KEY and LLM_API_KEY separate prevents confusion.

Benchmark-driven development: Iterating on failing questions is more effective than guessing.

Troubleshooting
Common Issues
Agent doesn't use query_api for data questions

Check tool description - add "live data", "item count", "database"

Verify LMS_API_KEY is set correctly

Ensure backend is running on expected port

API calls return 401

Verify LMS_API_KEY matches the key in .env.docker.secret

Check that backend is running and accessible

Agent times out on debug questions

Increase MAX_TOOL_CALLS (default 10)

Try faster LLM model

Optimize tool implementations

Source field empty for code questions

Check extract_source_from_messages() logic

Ensure LLM mentions file paths in its reasoning

Benchmark fails on hidden questions

Don't hardcode answers

Ensure agent generalizes, not just memorizes

Test with varied phrasings of same question

Version History
Task 1: Basic question-answering agent with JSON output

Task 2: Documentation agent with file reading tools

Task 3: System agent with API querying and benchmark passing
