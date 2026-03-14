# Task 1: Call an LLM from Code - Implementation Plan

## LLM Provider Choice
- **Provider**: OpenRouter
- **Model**: `qwen/qwen3-coder:free`
- **Why**: Works from Russia without VPN, 1000 free requests per day, supports OpenAI-compatible API

## Agent Structure
1. **Configuration**:
   - Load environment variables from `.env.agent.secret`
   - Variables: `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`

2. **Input Processing**:
   - Read question from command-line argument (`sys.argv[1]`)
   - If no argument, print error to stderr and exit with code 1

3. **LLM Communication**:
   - Use `httpx` or `requests` to call OpenAI-compatible API
   - Endpoint: `/v1/chat/completions`
   - Method: POST
   - Headers: 
     - `Authorization: Bearer {API_KEY}`
     - `Content-Type: application/json`

4. **Request Body**:
   ```json
   {
     "model": "qwen/qwen3-coder:free",
     "messages": [
       {"role": "user", "content": "user question here"}
     ],
     "temperature": 0.7,
     "max_tokens": 500
   }
