#!/usr/bin/env python3
"""
Regression test for agent.py
"""

import subprocess
import json
import sys

def test_agent_basic():
    """Test that agent.py returns valid JSON with answer and tool_calls"""
    
    # Run agent with a simple question using uv run
    result = subprocess.run(
        ["uv", "run", "agent.py", "What is 2+2?"],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    # Print debug info
    print(f"Exit code: {result.returncode}", file=sys.stderr)
    print(f"STDOUT: {result.stdout}", file=sys.stderr)
    print(f"STDERR: {result.stderr}", file=sys.stderr)
    
    # Check exit code
    assert result.returncode == 0, f"Agent failed with exit code {result.returncode}"
    
    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        print(f"Invalid JSON output: {result.stdout}", file=sys.stderr)
        print(f"Stderr: {result.stderr}", file=sys.stderr)
        raise
    
    # Check required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "tool_calls should be a list"
    
    # Check that answer is not empty
    assert output["answer"], "Answer should not be empty"
    
    print("✓ Test passed: agent.py returns valid JSON with required fields")

def test_agent_no_question():
    """Test that agent.py handles missing question gracefully"""
    
    result = subprocess.run(
        ["uv", "run", "agent.py"],
        capture_output=True,
        text=True
    )
    
    # Should exit with error
    assert result.returncode != 0, "Agent should fail with no question"
    assert result.stderr, "Should print error to stderr"
    print("✓ Test passed: agent.py handles missing question correctly")

if __name__ == "__main__":
    test_agent_basic()
    test_agent_no_question()
    print("All tests passed!")
