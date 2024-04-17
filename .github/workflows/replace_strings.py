# script.py
import json
import os
import re
import sys


def replace_in_file(file_path, replacements):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    for old, new in replacements.items():
        content = re.sub(r"\b" + re.escape(old) + r"\b", new, content)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)


def main(base_path):
    replacements_str = os.getenv("REPLACEMENTS")
    if not replacements_str:
        raise ValueError("REPLACEMENTS environment variable is not set")
    replacements = json.loads(replacements_str)

    for root, dirs, files in os.walk(base_path):
        for filename in files:
            if filename.endswith(".json"):
                replace_in_file(os.path.join(root, filename), replacements)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("No base path provided")
    base_path = sys.argv[1]
    main(base_path)
