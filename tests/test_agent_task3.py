#!/usr/bin/env python3
"""
Regression tests for Task 3 - System Agent with query_api tool
"""

import subprocess
import json
import sys
import re

def test_system_fact_question():
    """Test that agent uses read_file for system framework question"""
    
    question = "What Python web framework does this project's backend use?"
    
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        timeout=120
    )
    
    print(f"\n[TEST] Question: {question}", file=sys.stderr)
    print(f"Exit code: {result.returncode}", file=sys.stderr)
    
    assert result.returncode == 0, f"Agent failed with exit code {result.returncode}"
    
    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {result.stdout}", file=sys.stderr)
        raise
    
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    
    # Should use read_file
    tool_names = [tc["tool"] for tc in output["tool_calls"]]
    assert "read_file" in tool_names, f"Expected read_file tool call, got {tool_names}"
    
    # Answer should mention FastAPI
    assert "fastapi" in output["answer"].lower(), f"Expected FastAPI in answer, got: {output['answer']}"
    
    print(f"✓ Test passed: Agent used read_file for system fact", file=sys.stderr)
    print(f"  Answer: {output['answer'][:100]}...", file=sys.stderr)

def test_data_question():
    """Test that agent uses query_api for data question"""
    
    question = "How many items are in the database?"
    
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        timeout=120
    )
    
    print(f"\n[TEST] Question: {question}", file=sys.stderr)
    print(f"Exit code: {result.returncode}", file=sys.stderr)
    
    assert result.returncode == 0, f"Agent failed with exit code {result.returncode}"
    
    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {result.stdout}", file=sys.stderr)
        raise
    
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    
    # Should use query_api
    tool_names = [tc["tool"] for tc in output["tool_calls"]]
    assert "query_api" in tool_names, f"Expected query_api tool call, got {tool_names}"
    
    # Answer should contain a number
    numbers = re.findall(r'\d+', output["answer"])
    assert numbers, f"Expected a number in answer, got: {output['answer']}"
    
    print(f"✓ Test passed: Agent used query_api for data question", file=sys.stderr)
    print(f"  Answer: {output['answer'][:100]}...", file=sys.stderr)

def test_api_error_handling():
    """Test that agent handles API errors gracefully"""
    
    question = "What happens when you request /items/ without authentication?"
    
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        timeout=120
    )
    
    print(f"\n[TEST] Question: {question}", file=sys.stderr)
    print(f"Exit code: {result.returncode}", file=sys.stderr)
    
    assert result.returncode == 0, f"Agent failed with exit code {result.returncode}"
    
    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {result.stdout}", file=sys.stderr)
        raise
    
    # Answer should mention 401 or 403
    answer_lower = output["answer"].lower()
    assert any(code in answer_lower for code in ["401", "403", "unauthorized", "forbidden"]), \
           f"Expected auth error in answer, got: {output['answer']}"
    
    print(f"✓ Test passed: Agent handles API errors", file=sys.stderr)

def test_combined_tools():
    """Test that agent can combine query_api and read_file for debugging"""
    
    question = "Why does /analytics/completion-rate crash for lab-99?"
    
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        timeout=120
    )
    
    print(f"\n[TEST] Question: {question}", file=sys.stderr)
    print(f"Exit code: {result.returncode}", file=sys.stderr)
    
    assert result.returncode == 0, f"Agent failed with exit code {result.returncode}"
    
    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {result.stdout}", file=sys.stderr)
        raise
    
    tool_names = [tc["tool"] for tc in output["tool_calls"]]
    
    # Should use both query_api and read_file
    assert "query_api" in tool_names, "Expected query_api for this question"
    assert "read_file" in tool_names, "Expected read_file to check source code"
    
    print(f"✓ Test passed: Agent combined query_api and read_file", file=sys.stderr)
    print(f"  Tools used: {tool_names}", file=sys.stderr)

if __name__ == "__main__":
    print("Running Task 3 tests...", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    
    tests = [
        test_system_fact_question,
        test_data_question,
        test_api_error_handling,
        test_combined_tools
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            print(f"\n▶ Running {test.__name__}...", file=sys.stderr)
            test()
            passed += 1
            print(f"  ✅ {test.__name__} passed", file=sys.stderr)
        except AssertionError as e:
            failed += 1
            print(f"  ❌ {test.__name__} failed: {e}", file=sys.stderr)
        except Exception as e:
            failed += 1
            print(f"  ❌ {test.__name__} error: {e}", file=sys.stderr)
    
    print("\n" + "=" * 50, file=sys.stderr)
    print(f"Tests completed: {passed} passed, {failed} failed", file=sys.stderr)
    
    if failed > 0:
        sys.exit(1)
    sys.exit(0)
