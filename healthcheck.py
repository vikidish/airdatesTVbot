#!/usr/bin/env python3
"""Healthcheck script for Docker container."""

import sys

# Skip DB check during import
import builtins
builtins.SKIP_DB_CHECK = 1

from config import config


def main() -> int:
    """Check database health. Returns 0 if healthy, 1 otherwise."""
    if config.check_db_health():
        return 0
    print("Database health check failed", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
