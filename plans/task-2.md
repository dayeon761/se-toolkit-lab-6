# Task 2: The Documentation Agent - Implementation Plan

## Overview
Extend the agent from Task 1 to support tool calling, enabling it to read files and list directories in the project wiki.

## Tool Definitions

### 1. `list_files`
- **Purpose**: List all files and directories at a given path
- **Parameters**: 
  - `path` (string): Relative path from project root (e.g., "wiki", ".")
- **Returns**: Newline-separated string of entries
- **Security**: Prevent path traversal (no `..` allowed)
- **Implementation**: Use `os.listdir()` with path validation

### 2. `read_file`
- **Purpose**: Read contents of a specific file
- **Parameters**:
  - `path` (string): Relative path from project root (e.g., "wiki/git-workflow.md")
- **Returns**: File contents as string, or error message if file doesn't exist
- **Security**: Validate path is within project directory

## Agentic Loop Design
loop up to 10 times:

Send conversation history + tool definitions to LLM

Parse LLM response

If tool_calls present:

Execute each tool

Append results as tool messages

Continue loop

If text response (no tool_calls):

This is final answer

Extract source from context

Exit loop

text

## System Prompt Strategy
You are a documentation agent. Your task is to answer questions using the project wiki.

Available tools:

list_files(path): Discover wiki files

read_file(path): Read wiki file contents

Rules:

First, use list_files("wiki") to see available documentation

Read relevant files with read_file()

Find the section that answers the question

Include the source reference (file path + section anchor)

If unsure, explore more files

Provide clear, concise answers based on the wiki

text

## Source Extraction
- Track which file was read that contained the answer
- Include section anchor if possible (e.g., `#resolving-merge-conflicts`)
- Format: `wiki/filename.md#section`

## Output Format
```json
{
  "answer": "The answer text",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "file1.md\nfile2.md"},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "file contents..."}
  ]
}
Security Implementation
Normalize paths with os.path.abspath()

Check that resolved path starts with project root

Reject any path containing ..

Handle both files and directories safely

Testing Strategy
Test 1: "How do you resolve a merge conflict?"

Expect read_file in tool_calls

Source should reference wiki/git-workflow.md

Test 2: "What files are in the wiki?"

Expect list_files in tool_calls

Verify tool_calls array is populated

Implementation Steps
Create tool functions with security validation

Define tool schemas for OpenAI function calling

Implement agentic loop with message history

Add source tracking

Update system prompt

Create tests

Update documentation
