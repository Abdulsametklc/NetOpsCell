---
name: karpathy-guidelines
description: Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code to avoid overcomplication, make surgical changes, surface assumptions, and define verifiable success criteria.
license: MIT
---

# Karpathy Guidelines

Behavioral guidelines for working on code in this workspace, inspired by Andrej Karpathy's advice on avoiding common LLM coding pitfalls.

## 1. Think Before Coding

Do not assume. Surface tradeoffs and ambiguity.

Before implementing:
- State assumptions explicitly.
- If there are multiple interpretations, present them instead of silently choosing one.
- If a simpler approach exists, say so.
- If something is unclear, stop and ask for clarification.

## 2. Simplicity First

Prefer the minimum code that solves the current problem.

- Avoid speculative features.
- Avoid abstractions for one-off code.
- Avoid extra configuration or error handling that was not requested.
- If a 200-line solution could be 50 lines, simplify it.

## 3. Surgical Changes

Touch only what must change.

- Do not refactor unrelated code just because it is nearby.
- Match the existing style.
- Remove only the imports, variables, or functions made unused by your changes.
- Every changed line should trace directly to the request.

## 4. Goal-Driven Execution

Turn tasks into verifiable goals.

Examples:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step work, use a short plan like:
1. Implement the minimal change
2. Verify it with the relevant test or smoke check
3. Stop if the result does not satisfy the goal
