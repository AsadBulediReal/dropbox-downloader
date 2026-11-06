---
trigger: always_on
---

# Rule: Maximum 400 Lines of Code Per File

## Core Directives

1. **400-Line File Limit**:
   - No code file may exceed **400 lines** of code.
   - Always check line counts before and after creating or modifying files to ensure compliance.

2. **Modular Design for New & Growing Code**:
   - When writing new features or adding code that would cause a file to exceed 400 lines, split logic cleanly into focused, modular files (e.g., separate helpers, widgets, dialogs, workers, or handlers) so every file remains at or under 400 lines.
   - Do not refactor untouched existing files unless explicitly requested by the user or required to accommodate newly requested changes within the 400-line limit.

