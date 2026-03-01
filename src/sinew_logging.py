#!/usr/bin/env python3

"""
sinew_logging.py — Logging setup and print redirector for Sinew.

This module must be imported before any other Sinew module so that all
print() output is captured to the log file from the very start.
"""

import logging
import os
import sys
from datetime import datetime

# Silence noisy third-party loggers
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)


def setup_logging():
    """
    Set up logging to file only.
    Creates sinew.log in the base directory, overwriting previous session.
    Console output is handled separately by the print redirector.
    """
    # Determine base directory for log file
    try:
        from config import EXT_DIR
        log_dir = EXT_DIR
    except ImportError:
        log_dir = os.path.dirname(os.path.abspath(__file__))

    log_file = os.path.join(log_dir, "sinew.log")

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # File handler - overwrites each session (no rotation)
    try:
        file_handler = logging.FileHandler(
            log_file, mode='w', encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not create log file: {e}")

    # Note: No console handler - the LoggingPrintRedirector handles console output
    # Adding a console handler here would cause duplicate output

    return log_file


class LoggingPrintRedirector:
    """
    Redirects print() output to both console and log file.
    Intercepts sys.stdout to capture all print statements.
    """

    # Patterns to suppress from both console and log (verbose debug spam)
    SUPPRESS_PATTERNS = [
        "[PC] Species conversion:",
        "[SaveData] Species conversion:",
        "Species conversion:",
        # Parser per-Pokemon lines (e.g. "  1. #005 CHARMELEON Lv.18")
        "[Parser]   ",
        # Settings missing-file noise (file simply doesn't exist yet on first run)
        "[Settings] File not found:",
        # ROM match lines are logged twice per startup
        "[GameScreen] ROM match ",
        # Per-achievement detail during shiny/storage checks
        "[Achievements] Checking shiny achievement:",
        # ROMDetect per-file lines (summary 'ROM scan complete' is kept)
        "[ROMDetect] Extracted ",
        "[ROMDetect] Loaded ",
        "[ROMDetect] Hash match:",
        # Parser low-level internals (summary 'Game detected/Found N party' lines kept)
        "[Parser] Save slot:",
        "[Parser] Section 1 offset:",
        "[Parser] Parsing party with",
        "[Parser] Loaded:",
        "[pokemon.py] game_type=",
        "[pokemon.py] team_data_offset=",
        "[Money] game_type=",
        "[GameDetect] Using ROM header hint:",
        # Achievement check internals (aggregate summaries are kept)
        "[Achievements] check_sinew_achievements:",
        "[Achievements] Re-validating all unlocked",
        "[Achievements] All unlocked achievements are valid",
        "[Achievements] Legendaries in combined_pokedex",
        # Per-achievement evaluation trace (~30 lines per run; UNLOCKED lines are kept)
        "[Achievements]   Checking ",
        "[Achievements] Legendary check:",
        "[Achievements] Sevii check:",
        "[Achievements]   Checked ",
        # check_and_unlock diagnostic block (two summary lines above cover it)
        "[Achievements] check_and_unlock for ",
        "[Achievements]   dex_caught=",
        "[Achievements]   pc_pokemon=",
        "[Achievements]   owned_list has ",
        # Per-game intermediate lists (summary lines above them are kept)
        "[Achievements] LeafGreen PC Pokemon:",
        "[Achievements] FireRed PC Pokemon:",
        "[Achievements] LeafGreen owned_list:",
        "[Achievements] FireRed owned_list:",
        "[Achievements] LeafGreen Sevii prereqs:",
        "[Achievements] FireRed Sevii prereqs:",
        "[Achievements] LeafGreen has legendaries",
        "[Achievements] FireRed has legendaries",
        "[Achievements] First PC Pokemon keys:",
        # Per-game found-save / sinew-cache lines (logged at startup; redundant on pause)
        "[Achievements] Found save for ",
        "[Achievements] Sinew cache:",
        # mGBA verbose init lines (Core path: is kept, covers filename + full path)
        "[MgbaEmulator] Expected core:",
        # mGBA audio diagnostic blocks (init/thread-started/shutdown lines are kept)
        "[MgbaEmulator] ▶ Audio Status:",
        "[MgbaEmulator] ╔",
        "[MgbaEmulator] ║",
        "[MgbaEmulator] ╠",
        "[MgbaEmulator] ╚",
        "[MgbaEmulator] Audio thread: ",
        "[MgbaEmulator] Audio device info:",
        # Scaler offset / virtual-resolution lines (Hardware scaling: line is kept)
        "[Scaler] Scale: ",
        "[Scaler] Virtual resolution set to",
        # Controller non-event noise
        "[Controller] No active controller to refresh",
        # pygame startup chatter
        "pygame ",
        "Hello from the pygame community.",
        # Lifecycle noise (Applied settings: line is kept)
        "[Sinew] Reloaded controller config",
        "[Sinew] Reloaded settings from disk",
    ]

    def __init__(self, original_stdout, logger):
        self.original_stdout = original_stdout
        self.logger = logger
        self.buffer = ""

    def _should_suppress(self, line):
        """Check if a line should be suppressed from output."""
        for pattern in self.SUPPRESS_PATTERNS:
            if pattern in line:
                return True
        return False

    def write(self, text):
        """Buffer incoming text and emit each complete line to the logger, suppressing noisy patterns."""
        # Buffer text and process complete lines
        self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.strip():  # Only process non-empty lines
                # Skip verbose debug messages entirely
                if self._should_suppress(line):
                    continue
                # Write to original stdout (console)
                if self.original_stdout:
                    self.original_stdout.write(line + "\n")
                # Log to file
                self.logger.info(line.rstrip())

    def flush(self):
        """Flush any remaining buffered text to the logger and the original stdout stream."""
        if self.original_stdout:
            self.original_stdout.flush()
        # Flush any remaining buffer
        if self.buffer.strip():
            if not self._should_suppress(self.buffer):
                if self.original_stdout:
                    self.original_stdout.write(self.buffer)
                self.logger.info(self.buffer.rstrip())
            self.buffer = ""


def init_redirectors(version="1.3.6"):
    """
    Initialize logging and redirect sys.stdout / sys.stderr.

    Call this once at startup, before any other imports that print.
    Returns the path to the log file.
    Idempotent: safe to call multiple times.
    """
    # Already initialised — don't double-redirect or write a second banner
    if isinstance(sys.stdout, LoggingPrintRedirector):
        return getattr(sys.stdout, '_log_file_path', '')

    log_file_path = setup_logging()
    sinew_logger = logging.getLogger("sinew")

    # Redirect stdout
    original_stdout = sys.stdout
    sys.stdout = LoggingPrintRedirector(original_stdout, sinew_logger)
    sys.stdout._log_file_path = log_file_path

    # Redirect stderr
    original_stderr = sys.stderr
    stderr_logger = logging.getLogger("sinew.error")
    sys.stderr = LoggingPrintRedirector(original_stderr, stderr_logger)

    # Log startup banner
    sinew_logger.info("=" * 60)
    sinew_logger.info("Sinew %s", version)
    sinew_logger.info("Starting - %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    sinew_logger.info("Log file: %s", log_file_path)
    sinew_logger.info("Python: %s", sys.version)
    sinew_logger.info("Platform: %s", sys.platform)
    sinew_logger.info("=" * 60)

    return log_file_path
