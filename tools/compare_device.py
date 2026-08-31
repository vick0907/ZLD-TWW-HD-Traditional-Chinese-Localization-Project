"""Compare a local game dump against a listing pulled from an Android device.

Device listing is produced with:
    adb shell "cd '<game dir>' && find . -type f -exec stat -c '%s|%n' {} +"
"""
import argparse
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("local")
    ap.add_argument("listing")
    args = ap.parse_args()

    device = {}
    for line in open(args.listing, encoding="utf-8", errors="replace"):
        line = line.strip().replace("\\", "/")
        if "|" not in line:
            continue
        size, path = line.split("|", 1)
        device[path.removeprefix("./")] = int(size)

    local = {}
    for dirpath, _, files in os.walk(args.local):
        for name in files:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, args.local).replace(os.sep, "/")
            local[rel] = os.path.getsize(full)

    only_local = sorted(set(local) - set(device))
    only_device = sorted(set(device) - set(local))
    differ = sorted(p for p in set(local) & set(device) if local[p] != device[p])

    print(f"local {len(local)} files, device {len(device)} files")
    if only_local:
        print(f"\nmissing on device ({len(only_local)}):")
        for p in only_local:
            print(f"    {local[p]:>12,}  {p}")
    if only_device:
        print(f"\nextra on device ({len(only_device)}):")
        for p in only_device:
            print(f"    {device[p]:>12,}  {p}")
    print(f"\ndifferent size ({len(differ)}):")
    for p in differ:
        print(f"    {device[p]:>12,} -> {local[p]:>12,}  {p}")
    if not (only_local or only_device or differ):
        print("\nidentical")


if __name__ == "__main__":
    main()
