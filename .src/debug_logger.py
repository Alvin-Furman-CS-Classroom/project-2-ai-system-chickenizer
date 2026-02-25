"""Shared debug logger for project modules.

Any module can get a file-based logger that writes to debug_reports/<entry_point>.txt.
Log file is named after the script that was run (or the test file under pytest),
so all modules logging in the same run write to the same debug report.

Usage:
    In any module (prefer passing __name__ so log lines are labeled by module):
        from kb_logger import get_debug_logger
        _logger = get_debug_logger(__name__)
        # or
        _logger = get_debug_logger("my_module")

    Set KB_LOG_LEVEL: DEBUG | INFO | WARNING | ERROR (default: INFO)

    This file was generated with the help of the Cursor agent and modified to fit the needs of the project.
"""

import logging
import os
import sys
from pathlib import Path

# This file's directory and project root (parent of .src), from __file__
_THIS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _THIS_DIR.parent


def _detect_test_file():
    """If running under pytest, return test file name for log file (e.g. test_module1_kb_debug)."""
    # Pytest sets PYTEST_CURRENT_TEST to e.g. "unit_tests/test_module1_kb.py::TestClass::test_method"
    pytest_test = os.getenv("PYTEST_CURRENT_TEST", "")
    if pytest_test:
        part = pytest_test.split("::")[0]
        if part and "test_" in Path(part).stem:
            return f"{Path(part).stem}_debug"
    # Fallback: look at script args (e.g. pytest unit_tests/test_module1_kb.py)
    if "pytest" in sys.modules and sys.argv:
        for arg in sys.argv:
            if "test_" in arg and arg.endswith(".py"):
                return f"{Path(arg).stem}_debug"
    return None


def _log_file_path(logger_name: str) -> Path:
    """Path to the debug report file for this run (same for all loggers in a run)."""
    test_file = _detect_test_file()
    if test_file:
        log_filename = f"{test_file}.txt"
    elif sys.argv and sys.argv[0] and sys.argv[0] != "-c":
        log_filename = f"{Path(sys.argv[0]).stem}.txt"
    else:
        log_filename = f"{logger_name}.txt"
    debug_reports_dir = _PROJECT_ROOT / "debug_reports"
    debug_reports_dir.mkdir(exist_ok=True)
    return debug_reports_dir / log_filename


def get_debug_logger(name=None):
    """Get a file-based logger for any module.

    Logs go to debug_reports/<entry_script>.txt (or test_*_debug.txt under pytest).
    Multiple modules can call this; each gets a logger with its own name, and all
    write to the same debug report for the current run.

    Args:
        name: Logger name (shows in log lines). Pass __name__ from your module.
              If None, uses "app".

    Returns:
        logging.Logger configured with a FileHandler to the run's debug report.
    """
    logger_name = name if name is not None else "app"
    logger = logging.getLogger(logger_name)

    if not logger.handlers:
        log_level = os.getenv("KB_LOG_LEVEL", "INFO").upper()
        level = getattr(logging, log_level, logging.INFO)
        logger.setLevel(level)

        log_path = _log_file_path(logger_name)
        handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.info("Logger initialized; writing to %s", str(log_path))

    return logger
