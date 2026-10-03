#!/usr/bin/env python
import os
import sys
from pathlib import Path


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    if os.environ["DJANGO_SETTINGS_MODULE"] == "config.settings.local":
        import environ

        environ.Env.read_env(Path(__file__).resolve().parent / ".env")
    if len(sys.argv) > 1 and sys.argv[1] == "runserver":
        has_address = any(arg for arg in sys.argv[2:] if not arg.startswith("-"))
        if not has_address:
            port = os.environ.get("PORT", "8001")
            sys.argv.append(f"127.0.0.1:{port}")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
