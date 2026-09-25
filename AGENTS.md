# Agent Rules

## Never Break Working Code & Strict Edit Scope

1. **Explicit Permission Required for Code Changes**:
   - NEVER modify, rewrite, refactor, add to, or remove existing working code unless explicitly instructed by the user (e.g., asked to fix a specific bug, implement a specific feature, or perform a direct task).
   - If existing code is working and is outside the scope of the user's request, leave it completely untouched.

2. **Strictly Scope-Bound Modifications**:
   - Only edit the exact lines, functions, or files strictly required to fulfill the user's explicit instructions.
   - Do NOT perform unsolicited refactoring, code cleanup, style formatting changes, structural rewrites, or unrequested additions.

3. **Zero Regressions**:
   - NEVER break, alter, degrade, or remove existing working functionality, UI controls, or user flows.
   - Do not disable, deactivate, or hide any existing options, buttons, checkboxes, or controls unless explicitly requested by the user.

4. **Preserve Working State**:
   - All changes or new features must integrate seamlessly with existing code without disturbing working behaviors.
   - Ensure UI controls (such as Select All, Deselect All, Expand All, Collapse All, etc.) remain properly enabled and responsive across all states (loading, loaded, idle).

5. **Thorough Verification**:
   - Always run automated checks, syntax verification, and regression tests on modified files.
   - Verify that all existing features continue to work exactly as expected before completing any task.

6. **Preserve Code Integrity**:
   - Maintain all existing comments, docstrings, type annotations, and error handling.
