import sys

if sys.version_info < (3, 10):
    raise SystemExit("CornerBrief needs Python 3.10 or newer. Recreate .venv with a newer Python.")
