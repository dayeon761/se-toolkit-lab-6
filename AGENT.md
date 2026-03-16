# Agent Documentation

## Overview
This is a simple CLI agent that answers questions using an LLM via OpenRouter API. It serves as the foundation for more complex agents in subsequent tasks.

## LLM Provider
- **Provider**: OpenRouter (https://openrouter.ai)
- **Model**: `google/gemma-3-12b-it:free`
- **Why**: 
  - Works from Russia without VPN
  - 1000 free requests per day
  - Supports OpenAI-compatible API
  - Good balance of speed and quality

## Configuration
The agent reads configuration from `.env.agent.secret` file in the project root:
LLM_API_KEY=your-api-key-here
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=google/gemma-3-12b-it:free

text

## Requirements
- Python 3.8+
- Dependencies: `httpx`, `python-dotenv`

Install dependencies:
```bash
uv add httpx python-dotenv
Usage
Run the agent with a question as the first argument:

bash
uv run agent.py "Your question here"
Examples
Basic question:

bash
uv run agent.py "What does REST stand for?"
Output:

json
{"answer": "REST stands for Representational State Transfer, an architectural style for designing networked applications.", "tool_calls": []}
Technical question:

bash
uv run agent.py "Explain Python decorators"
Output:

json
{"answer": "Python decorators are functions that modify the behavior of other functions...", "tool_calls": []}
Output Format
The agent outputs a single JSON line to stdout with the following structure:

json
{
  "answer": "string - the LLM's response to the question",
  "tool_calls": []  // empty array for Task 1
}
Rules
Only valid JSON goes to stdout

All debug/progress information goes to stderr

Required fields: answer (string) and tool_calls (array)

Response time must be under 60 seconds

Error Handling
Exit code 0: Success, valid JSON output

Exit code 1: Failure (missing input, API errors, timeout)

Error scenarios:

No question provided

Missing or invalid API key

API timeout (>55 seconds)

Network errors

Invalid API response

All errors are printed to stderr with [ERROR] prefix.

Implementation Details
Architecture
Configuration Loading: Uses python-dotenv to load environment variables

Input Processing: Reads question from command line arguments

API Communication: Async HTTP client with 55-second timeout

Response Parsing: Extracts answer from OpenAI-compatible response format

Output Formatting: JSON serialization with required fields

Code Structure
main(): Entry point, handles command line arguments

call_llm(): Async function to communicate with LLM API

log_error(): Helper function for stderr output

Testing
Run the regression test:

bash
python3 tests/test_agent.py
The test verifies:

Valid JSON output with required fields

Proper error handling for missing questions

Non-empty answers

Troubleshooting
Common Issues
"LLM_API_KEY not set"

Ensure .env.agent.secret exists and contains valid API key

Timeout errors

Check internet connection

Try with shorter questions

Increase timeout in code if needed

Invalid JSON output

Check for debug messages leaking to stdout

Ensure no print statements in main code path

API errors

Verify API key is valid

Check OpenRouter service status

Ensure model name is correct

## Task 2: Documentation Agent with Tool Calling

### New Features
- **Tool Calling**: Agent can now use tools to interact with the file system
- **Agentic Loop**: Automatically calls tools and processes results until answer is found
- **Source Tracking**: Output includes source file reference

### Available Tools

#### 1. `list_files(path)`
- Lists files and directories at specified path
- Used to discover wiki documentation
- Example: `list_files("wiki")`

#### 2. `read_file(path)`
- Reads contents of a file
- Used to read wiki documentation
- Example: `read_file("wiki/git-workflow.md")`

### Security Features
- Path traversal protection (blocks `..`)
- Files outside project root are inaccessible
- File size limits (1MB max)

### Agentic Loop
1. Send question + tool definitions to LLM
2. If LLM requests tools → execute them, add results to conversation
3. Repeat up to 10 times
4. When LLM gives final answer → output JSON with answer, source, and tool_calls

### Output Format
```json
{
  "answer": "The answer to your question",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    }
  ]
}

Usage Examples
bash
# Ask about merge conflicts
uv run agent.py "How do you resolve a merge conflict?"

# Explore wiki
uv run agent.py "What documentation is available?"
Testing
Run the Task 2 tests:

bash
python3 tests/test_agent_task2.py

Version History
Task 1: Basic question-answering agent with JSON output
