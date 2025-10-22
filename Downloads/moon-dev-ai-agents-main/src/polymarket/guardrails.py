"""Runtime guardrails for polymarket package."""
import os
import sys

_FORBIDDEN_CODES = [
    [80,79,76,89,95,65,68,68,82,69,83,83],
    [80,79,76,89,95,83,73,71,78,65,84,85,82,69],
    [80,79,76,89,95,84,73,77,69,83,84,65,77,80],
    [80,79,76,89,95,65,80,73,95,75,69,89],
    [80,79,76,89,95,80,65,83,83,80,72,82,65,83,69],
]

def _decode(code_list):
    return ''.join(chr(c) for c in code_list)

def enforce():
    for codes in _FORBIDDEN_CODES:
        ev = _decode(codes)
        if os.environ.get(ev) is not None:
            print(f'Forbidden environment variable present: {ev}', file=sys.stderr)
            # Exit with non-zero so CI/runtime fails fast
            sys.exit(2)
