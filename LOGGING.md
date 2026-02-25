# Debug Logging

## Overview

Debug logging is provided by **`debug_logger.py`** in `.src/`. Any module (e.g. `module1_kb`, `engine`) can use it. Logs are written to **text files** in `debug_reports/`, named after the script that was run or the test file under pytest.

## Log File Location

- **Folder:** `debug_reports/`
- **Filename:**
  - Normal run: `<script_name>.txt` (e.g. `python .src/module1_kb.py` → `module1_kb.txt`, `python main.py` → `main.txt`)
  - Pytest: `test_<testfile>_debug.txt` (e.g. `pytest unit_tests/test_module1_kb.py` → `test_module1_kb_debug.txt`)
- **Mode:** Append — new runs add to the existing file

## Quick Start

### Enable Debug Logging

**Windows PowerShell:**
```powershell
$env:KB_LOG_LEVEL="DEBUG"
python **file_name**
```

**Windows CMD:**
```cmd
set KB_LOG_LEVEL=DEBUG
python **file_name**
```

**Linux/Mac:**
```bash
export KB_LOG_LEVEL=DEBUG
python **file_name**
```

After running, check `debug_reports/<script_name>.txt` (or `debug_reports/test_*_debug.txt` when using pytest).

### Log Levels

- **DEBUG**: Most verbose — all operations, iterations, and detailed state
- **INFO**: Default — important operations and results (used so the report file has useful content)
- **WARNING**: Only warnings and errors (conflicts, failures)
- **ERROR**: Only errors

## What Gets Logged

### KnowledgeBase Operations

1. **Initialization**: When a KB is created
2. **tell()**: When clauses are added to the KB
   - Number of clauses being added
   - Content of each clause
   - Total clause count after addition
3. **ask()**: When checking entailment
   - Query being checked
   - Result (entails or does not entail)
4. **rebuild_kb()**: When the internal KB structure is rebuilt
   - Number of clauses in the rebuilt KB
5. **validate_kb()**: When checking satisfiability
   - Whether KB is satisfiable
   - Conflict reports if unsatisfiable

### Conflict Detection

- **Direct contradictions**: When p and ~p are both in KB
- **Chain contradictions**: When logical chains lead to contradictions
- **Minimal conflict detection**: Iterative removal process to find conflicting clauses

### Inference Operations

1. **forward_chain()**: Forward chaining inference
   - Starting facts
   - Each iteration and rules checked
   - New facts derived
   - Final results
2. **backward_chain()**: Backward chaining inference
   - Query being proven
   - Rules being tried
   - Antecedents being proven
   - Final proof path
3. **resolve()**: Resolution inference
   - Clauses being resolved
   - Complementary literals found
   - Resolution results

### Error Handling

- **Type errors**: Invalid input types are logged before raising exceptions
- **Validation failures**: When operations fail

## Example Output

Logs are written to `debug_reports/<script>.txt`. Example with DEBUG level:

```
2025-02-19 10:30:15 - module1_kb - DEBUG - Initialized KnowledgeBase with empty KB
2025-02-19 10:30:15 - module1_kb - DEBUG - tell(): Adding 2 clause(s) to KB
2025-02-19 10:30:15 - module1_kb - DEBUG -   Clause 1: p
2025-02-19 10:30:15 - module1_kb - DEBUG -   Clause 2: (p -> q)
2025-02-19 10:30:15 - module1_kb - DEBUG - KB now has 2 total clause(s)
2025-02-19 10:30:15 - module1_kb - DEBUG - rebuild_kb(): Rebuilt KB with 2 clause(s)
2025-02-19 10:30:15 - module1_kb - DEBUG - ask(): Checking if KB entails query: q
2025-02-19 10:30:15 - module1_kb - DEBUG -   KB has 2 clause(s)
2025-02-19 10:30:15 - module1_kb - INFO - ask(): KB entails query: q
```

### With INFO Level:

```
2025-02-19 10:30:15 - module1_kb - INFO - ask(): KB entails query: q
2025-02-19 10:30:15 - module1_kb - INFO - validate_kb(): KB is satisfiable (no conflicts)
```

### With WARNING Level:

```
2025-02-19 10:30:15 - module1_kb - WARNING - validate_kb(): KB is unsatisfiable (conflicts detected)
2025-02-19 10:30:15 - module1_kb - WARNING - validate_kb(): Conflict report: Direct contradiction: p, ~p
```

## Usage in Tests

When you run pytest, the logger writes to `debug_reports/test_<testfile>_debug.txt` automatically (e.g. `test_module1_kb_debug.txt`). No code changes needed in the test file.

To increase verbosity:

```powershell
$env:KB_LOG_LEVEL="DEBUG"
pytest unit_tests/test_module1_kb.py -v
```

Then open `debug_reports/test_module1_kb_debug.txt`.

## Usage in Production

Default level is **INFO**. For quieter production runs, set `KB_LOG_LEVEL=WARNING` so only warnings and errors are logged.

## Using the Logger in Other Modules

Any module can use the shared logger:

```python
from debug_logger import get_debug_logger
_logger = get_debug_logger(__name__)  # or get_debug_logger("my_module")
_logger.info("Something happened")
```

`module1_kb` uses `get_debug_logger("module1_kb")`; when it’s imported by another script, logs still go to that script’s debug report (e.g. `main.txt`).

## Customization

Logging is configured in **`.src/debug_logger.py`**. You can change the default level or format there (e.g. default level, formatter pattern, date format).

## Benefits

1. **Debugging**: Quickly identify where operations fail or behave unexpectedly
2. **Understanding**: See the step-by-step process of inference operations
3. **Performance**: Track how many iterations or operations are performed
4. **Conflict Analysis**: Understand why KBs become unsatisfiable
5. **Development**: Verify that your code is working as expected during development

## Notes

- Logging uses Python’s standard library — no extra dependencies
- Log output goes to `debug_reports/<script_name>.txt` or `debug_reports/test_*_debug.txt` (not the console)
- The `debug_reports/` folder is created automatically
- Log files are appended on each run (not overwritten)
- Each logger has a name (e.g. `module1_kb`) shown in each log line for filtering
- If `debug_logger.py` can’t be loaded, `module1_kb` falls back to a no-op logger so the app still runs
