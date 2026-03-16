# Task 1: Call an LLM from Code - Implementation Plan

## LLM Provider Choice
- **Provider**: OpenRouter (https://openrouter.ai)
- **Model**: `google/gemma-3-12b-it:free`
- **Why**: 
  - Works from Russia without VPN
  - 1000 free requests per day
  - Supports OpenAI-compatible API
  - Good balance of speed and quality

## Agent Structure

### 1. Configuration
- Load environment variables from `.env.agent.secret`
- Variables: `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`

### 2. Input Processing
- Read question from command-line argument (`sys.argv[1]`)
- If no argument, print error to stderr and exit with code 1

### 3. API Communication
- Use `httpx` for async HTTP requests
- Endpoint: `/v1/chat/completions`
- Method: POST
- Headers:
  - `Authorization: Bearer {API_KEY}`
  - `Content-Type: application/json`

### 4. Request Body
```json
{
  "model": "google/gemma-3-12b-it:free",
  "messages": [{"role": "user", "content": "user question"}],
  "temperature": 0.7,
  "max_tokens": 500
}
5. Response Processing
Extract answer from response.choices[0].message.content

Handle errors (timeout, API errors, invalid JSON)

6. Output Format
json
{
  "answer": "LLM response here",
  "tool_calls": []
}
Only JSON to stdout

All debug output to stderr

7. Error Handling
Exit code 0 on success, 1 on failure

Timeout after 55 seconds

Print errors to stderr

8. Testing Strategy
One regression test that verifies output format

Test with simple question: "What is 2+2?"

Verify JSON has required fields
