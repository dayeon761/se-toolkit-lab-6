# Agent Documentation

## Overview
This is a simple CLI agent that answers questions using an LLM via OpenAI-compatible API. It serves as the foundation for more complex agents in subsequent tasks.

## LLM Provider
- **Provider**: OpenRouter (https://openrouter.ai)
- **Model**: `qwen/qwen3-coder:free`
- **Why**: 
  - Works from Russia without VPN
  - 1000 free requests per day
  - Supports OpenAI-compatible API
  - Good performance for coding tasks

## Configuration
The agent reads configuration from `.env.agent.secret` file in the project root:
LLM_API_KEY=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
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=qwen/qwen3-coder:free

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
  "tool_calls": []  // empty array for Task 1, will contain tool calls in later tasks
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

log_debug()/log_error(): Helper functions for stderr output

Testing
Run the regression tests:

bash
python tests/test_agent.py
Tests verify:

Valid JSON output with required fields

Proper error handling for missing questions

Non-empty answers

Future Improvements (Tasks 2-3)
Add tool calling support

Implement system agent with domain knowledge

Add documentation agent capabilities

Enhance prompt engineering

Add more comprehensive tests

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

Version History
Task 1: Basic question-answering agent with JSON output

Task 2: Will add tool calling capabilities

Task 3: Will implement specialized agents
