"""Round-trip check: read every MSBT, rebuild it unchanged, compare bytes."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msbt  # noqa: E402


def main():
    root, report = sys.argv[1], sys.argv[2]
    ok = bad = 0
    lines = []
    total_msgs = 0
    chars = set()
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".msbt"):
                continue
            path = os.path.join(dirpath, name)
            data = open(path, "rb").read()
            try:
                messages, _ = msbt.read(data)
                rebuilt = msbt.write(data, messages)
            except Exception as e:
                bad += 1
                lines.append(f"FAIL  {name}: {e!r}")
                continue
            total_msgs += len(messages)
            for segs in messages:
                for kind, val in segs:
                    if kind == "t":
                        chars.update(val)
            if rebuilt == data:
                ok += 1
            else:
                bad += 1
                lines.append(f"DIFF  {name}: {len(data)} -> {len(rebuilt)}")
    lines.insert(0, f"identical={ok} mismatched={bad} messages={total_msgs} "
                    f"unique_text_chars={len(chars)}")
    cjk = sorted(c for c in chars if "\u4e00" <= c <= "\u9fff")
    lines.insert(1, f"CJK unified chars in text: {len(cjk)}")
    open(report, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines[:20]))


if __name__ == "__main__":
    main()
