#!/usr/bin/env python3
"""
Regression test for Task 1 agent
"""

import subprocess
import json
import sys

def test_agent_basic():
    """Test that agent returns valid JSON with required fields"""
    
    result = subprocess.run(
        ["uv", "run", "agent.py", "What is 2+2?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent failed with code {result.returncode}"
    
    # Parse JSON
    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        print(f"Invalid JSON: {result.stdout}", file=sys.stderr)
        raise
    
    # Check required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "tool_calls must be list"
    assert output["answer"], "Answer should not be empty"
    
    print("✓ Test passed: Valid JSON with required fields")

def test_agent_no_question():
    """Test that agent handles missing question"""
    
    result = subprocess.run(
        ["uv", "run", "agent.py"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode != 0, "Should fail with no question"
    print("✓ Test passed: Handles missing question")

if __name__ == "__main__":
    test_agent_basic()
    test_agent_no_question()
    print("\nAll tests passed!")
