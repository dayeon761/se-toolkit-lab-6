#!/usr/bin/env python3
"""
Regression tests for Task 2 - Documentation Agent with Tool Calling
"""

import subprocess
import json
import sys
import os

def test_list_files_tool():
    """Test that agent uses list_files tool to discover wiki files"""
    
    question = "What files are in the wiki?"
    
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    print(f"\n[TEST] Question: {question}", file=sys.stderr)
    print(f"Exit code: {result.returncode}", file=sys.stderr)
    
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
    assert "source" in output, "Missing 'source' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "tool_calls should be a list"
    
    # Check that tool_calls contains list_files
    tool_names = [tc["tool"] for tc in output["tool_calls"]]
    assert "list_files" in tool_names, "Expected list_files tool call"
    
    # Check source is a wiki file
    assert output["source"].startswith("wiki/"), f"Source should start with 'wiki/', got {output['source']}"
    
    print(f"✓ Test passed: Agent used list_files tool", file=sys.stderr)
    print(f"  Answer: {output['answer'][:100]}...", file=sys.stderr)
    print(f"  Source: {output['source']}", file=sys.stderr)

def test_read_file_tool():
    """Test that agent uses read_file tool to read specific wiki files"""
    
    question = "How do you resolve a merge conflict?"
    
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    print(f"\n[TEST] Question: {question}", file=sys.stderr)
    print(f"Exit code: {result.returncode}", file=sys.stderr)
    
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
    assert "source" in output, "Missing 'source' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    
    # Check that tool_calls contains read_file
    tool_names = [tc["tool"] for tc in output["tool_calls"]]
    assert "read_file" in tool_names, "Expected read_file tool call"
    
    # Check source references git-workflow.md
    assert "git-workflow.md" in output["source"], f"Expected git-workflow.md in source, got {output['source']}"
    
    # Check answer contains merge conflict information
    answer_lower = output["answer"].lower()
    keywords = ["merge", "conflict", "resolve", "branch"]
    found = any(keyword in answer_lower for keyword in keywords)
    assert found, f"Answer should mention merge conflicts, got: {output['answer']}"
    
    print(f"✓ Test passed: Agent used read_file tool", file=sys.stderr)
    print(f"  Answer: {output['answer'][:100]}...", file=sys.stderr)
    print(f"  Source: {output['source']}", file=sys.stderr)

def test_tool_calls_structure():
    """Test that tool_calls array has correct structure"""
    
    question = "What is in the wiki?"
    
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    # Parse output
    output = json.loads(result.stdout.strip())
    
    # Check each tool call has required fields
    for tc in output["tool_calls"]:
        assert "tool" in tc, "Tool call missing 'tool' field"
        assert "args" in tc, "Tool call missing 'args' field"
        assert "result" in tc, "Tool call missing 'result' field"
        assert isinstance(tc["args"], dict), "args should be a dictionary"
        assert isinstance(tc["result"], str), "result should be a string"
        
        # Check tool names are valid
        assert tc["tool"] in ["list_files", "read_file"], f"Invalid tool name: {tc['tool']}"
    
    print(f"✓ Test passed: Tool calls have correct structure", file=sys.stderr)

def test_path_security():
    """Test that agent cannot access files outside project root"""
    
    # Try to access file outside project
    question = "Read /etc/passwd"
    
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    output = json.loads(result.stdout.strip())
    
    # Check that any read_file attempts were blocked
    for tc in output["tool_calls"]:
        if tc["tool"] == "read_file":
            # If there was an attempt, it should have been blocked
            if "path" in tc["args"]:
                path = tc["args"]["path"]
                if ".." in path or path.startswith("/"):
                    # Tool should have returned error
                    assert "Error" in tc["result"] or "Invalid" in tc["result"], \
                           f"Path traversal should be blocked: {path}"
    
    print(f"✓ Test passed: Path security works", file=sys.stderr)

def test_max_tool_calls():
    """Test that agent respects maximum tool calls limit"""
    
    # This should trigger many tool calls
    question = "Explore the wiki thoroughly and tell me everything about git"
    
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        timeout=120  # Longer timeout for this test
    )
    
    output = json.loads(result.stdout.strip())
    
    # Check we didn't exceed max tool calls (should be handled by agent)
    assert len(output["tool_calls"]) <= 10, f"Too many tool calls: {len(output['tool_calls'])}"
    
    print(f"✓ Test passed: Agent respects max tool calls ({len(output['tool_calls'])} calls)", file=sys.stderr)

def test_source_format():
    """Test that source field has correct format"""
    
    question = "How do you resolve a merge conflict?"
    
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    output = json.loads(result.stdout.strip())
    
    # Check source format
    source = output["source"]
    assert source.startswith("wiki/"), "Source should start with wiki/"
    assert ".md" in source, "Source should reference a markdown file"
    
    # Could have section anchor
    if "#" in source:
        section = source.split("#")[1]
        assert section, "Section anchor should not be empty"
    
    print(f"✓ Test passed: Source format is correct: {source}", file=sys.stderr)

if __name__ == "__main__":
    print("Running Task 2 tests...", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    
    tests = [
        test_list_files_tool,
        test_read_file_tool,
        test_tool_calls_structure,
        test_path_security,
        test_max_tool_calls,
        test_source_format
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

