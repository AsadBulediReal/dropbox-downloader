# Rule: Never Break Working Code

## Core Directives

1. **Zero Regressions**:
   - NEVER break, alter, degrade, or remove existing working functionality, UI controls, or user flows.
   - Do not disable, deactivate, or hide any existing options, buttons, checkboxes, or controls unless explicitly requested by the user.

2. **Preserve Working State**:
   - All changes or new features must integrate seamlessly with existing code without disturbing working behaviors.
   - Ensure UI controls (such as Select All, Deselect All, Expand All, Collapse All, etc.) remain properly enabled and responsive across all states (loading, loaded, idle).

3. **Thorough Verification**:
   - Always run automated checks, syntax verification, and regressions tests on modified files.
   - Verify that all existing features continue to work exactly as expected before completing any task.

4. **Preserve Code Integrity**:
   - Maintain all existing comments, docstrings, type annotations, and error handling.
