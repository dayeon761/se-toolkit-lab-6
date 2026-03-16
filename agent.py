#!/usr/bin/env python3
"""
Simple LLM agent for Task 1
Calls OpenRouter API and returns JSON response
"""

import os
import sys
import json
import httpx
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv('.env.agent.secret')

# Configuration
API_KEY = os.getenv('LLM_API_KEY')
API_BASE = os.getenv('LLM_API_BASE', 'https://openrouter.ai/api/v1')
MODEL = os.getenv('LLM_MODEL', 'google/gemma-3-12b-it:free')
TIMEOUT = 55

def log_error(msg: str) -> None:
    """Print error messages to stderr"""
    print(f"[ERROR] {msg}", file=sys.stderr)

async def call_llm(question: str) -> dict | None:
    """Call LLM API and return response"""
    if not API_KEY:
        log_error("LLM_API_KEY not set in .env.agent.secret")
        return None
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": question}],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{API_BASE}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            answer = data['choices'][0]['message']['content']
            
            return {"answer": answer.strip(), "tool_calls": []}
            
        except httpx.TimeoutException:
            log_error(f"Request timed out after {TIMEOUT} seconds")
            return None
        except httpx.HTTPStatusError as e:
            log_error(f"HTTP error: {e.response.status_code}")
            log_error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            log_error(f"Error: {str(e)}")
            return None

async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        log_error("Usage: uv run agent.py \"your question here\"")
        sys.exit(1)
    
    question = sys.argv[1]
    
    result = await call_llm(question)
    
    if result:
        print(json.dumps(result))
        sys.exit(0)
    else:
        log_error("Failed to get response from LLM")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
