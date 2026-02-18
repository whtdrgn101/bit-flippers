"""Thin wrapper so asset generation can be invoked via `uv run generate-assets`."""
import runpy
import os
import sys


def main():
    script = os.path.join(
        os.path.dirname(__file__), os.pardir, os.pardir, "tools", "generate_assets.py"
    )
    script = os.path.normpath(script)
    # runpy executes the script as __main__
    sys.argv = [script]
    runpy.run_path(script, run_name="__main__")
