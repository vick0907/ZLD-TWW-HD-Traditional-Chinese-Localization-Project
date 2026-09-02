"""Apply hand-reviewed per-message corrections to the converted MSBT tree.

The OpenCC pass in convert_text.py fixes script and vocabulary but cannot fix
meaning. Corrections that need a human decision live in text/overrides.json and
are applied here, after conversion, so they survive a full rebuild.

An entry either rewrites the whole message with "new" (display form as produced
by msbt.to_display, control codes as {XXXX} / {0E:...} tokens) or patches a
fragment of it with "find"/"replace", which is safer for small wording fixes.
A "find" must match exactly once unless the entry sets "all": true.
Either way the control codes must survive unchanged - the message box relies on
them - unless the entry opts out with "codes": "changed".
"""
import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msbt  # noqa: E402

CODE = re.compile(r"\{(?:[0-9A-F]{4}|0E:[^{}]*)\}")


def find_msbt(root):
    out = {}
    for dirpath, _, files in os.walk(root):
        for name in files:
            if name.endswith(".msbt"):
                out[name] = os.path.join(dirpath, name)
    return out


def index_tree(root):
    """Map "<stem>#<label>" (or "<stem>#idx<n>") -> (path, message index)."""
    keys = {}
    for name, path in find_msbt(root).items():
        stem = os.path.splitext(name)[0]
        data = open(path, "rb").read()
        messages, _ = msbt.read(data)
        labels = msbt.read_labels(data) or {}
        for i in range(len(messages)):
            label = labels.get(i)
            keys[f"{stem}#{label}" if label else f"{stem}#idx{i}"] = (path, i)
    return keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="tree of converted MSBTs, edited in place")
    ap.add_argument("overrides")
    ap.add_argument("--report", default="out/overrides_report.json")
    args = ap.parse_args()

    entries = json.load(open(args.overrides, encoding="utf-8"))
    keys = index_tree(args.root)

    edits = collections.defaultdict(dict)
    applied, skipped, errors = 0, [], []
    for entry in entries:
        key = entry["key"]
        if key not in keys:
            errors.append(f"{key}: no such message in {args.root}")
            continue
        path, index = keys[key]
        current = edits[path].get(
            index, msbt.to_display(msbt.read(open(path, "rb").read())[0][index]))
        if "old" in entry and entry["old"] != current:
            errors.append(f"{key}: 'old' no longer matches the tree - re-review it")
            continue
        if "new" in entry:
            new = entry["new"]
        elif not entry.get("all") and current.count(entry["find"]) != 1:
            errors.append(f"{key}: 'find' matches {current.count(entry['find'])} "
                          "times, expected exactly one")
            continue
        else:
            new = current.replace(entry["find"], entry["replace"])
        if new == current:
            skipped.append(key)
            continue
        if entry.get("codes") != "changed":
            before, after = CODE.findall(current), CODE.findall(new)
            if collections.Counter(before) != collections.Counter(after):
                errors.append(f"{key}: control codes differ from the original")
                continue
        edits[path][index] = new
        applied += 1

    for path, changes in edits.items():
        if not changes:
            continue
        data = open(path, "rb").read()
        messages, _ = msbt.read(data)
        for index, new in changes.items():
            messages[index] = msbt.from_display(new)
        with open(path, "wb") as f:
            f.write(msbt.write(data, messages))

    report = {
        "overrides": len(entries),
        "applied": applied,
        "already_matching": skipped,
        "errors": errors,
    }
    os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"applied {applied} of {len(entries)} overrides "
          f"({len(skipped)} already matched)")
    for line in errors:
        print("ERROR", line)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
