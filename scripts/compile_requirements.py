"""Compile the runtime lock, retaining a portable path for the compatibility wheel."""
import os
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
env = dict(os.environ, CUSTOM_COMPILE_COMMAND="python scripts/compile_requirements.py")
subprocess.run([
    sys.executable, "-m", "piptools", "compile", "--strip-extras",
    "--no-emit-index-url", "--output-file=requirements-production.txt",
    *sys.argv[1:], "requirements-production.in",
], cwd=root, env=env, check=True)
lock = root / "requirements-production.txt"
content = re.sub(r"^djoser @ file:.*$", "./vendor/djoser-2.3.4-py3-none-any.whl", lock.read_text(), flags=re.MULTILINE)
if "file:///" in content:
    raise ValueError("Unexpected absolute file URL in dependency lock")
lock.write_text(content, encoding="utf-8")
