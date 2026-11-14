"""Ask the demo a question from the command line.

    python scripts/ask.py "Which sailings go from Singapore to Rotterdam next week?"
    python scripts/ask.py --llm MODEL "..."     (optional, needs a local Ollama)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ssa import data, engine, llm  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--llm", metavar="MODEL", help="parse with a local Ollama model")
    ap.add_argument("--json", action="store_true", help="print the full result with evidence")
    a = ap.parse_args()
    parts, name = None, "rule"
    if a.llm:
        parts, name = llm.parse_with_ollama(a.question, data.meta()["as_of"], a.llm)
    res = engine.answer(a.question, parts=parts, parser_name=name)
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        print(res["text"], "\n\n[" + res["notice"] + "]", sep="")


if __name__ == "__main__":
    main()
