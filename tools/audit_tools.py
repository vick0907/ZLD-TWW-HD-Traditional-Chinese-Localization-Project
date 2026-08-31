"""Classify tools/*.py by whether build.ps1 reaches them, directly or via imports."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")

names = {f[:-3] for f in os.listdir(TOOLS) if f.endswith(".py")}

imports = {}
for n in sorted(names):
    src = open(os.path.join(TOOLS, n + ".py"), encoding="utf-8").read()
    found = set()
    for m in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z_][\w]*)", src, re.M):
        if m.group(1) in names:
            found.add(m.group(1))
    imports[n] = found

entry = set(re.findall(r"tools\\(\w+)\.py", open(os.path.join(ROOT, "build.ps1"), encoding="utf-8-sig").read()))

reachable, stack = set(), list(entry)
while stack:
    n = stack.pop()
    if n in reachable:
        continue
    reachable.add(n)
    stack += list(imports.get(n, ()))

print(f"build.ps1 invokes ({len(entry)}):")
for n in sorted(entry):
    print(f"    {n}.py")
print(f"\npulled in as imports ({len(reachable - entry)}):")
for n in sorted(reachable - entry):
    print(f"    {n}.py")
print(f"\nnot reachable from build.ps1 ({len(names - reachable)}):")
for n in sorted(names - reachable):
    users = sorted(k for k, v in imports.items() if n in v)
    note = f"   (imported by {', '.join(users)})" if users else ""
    print(f"    {n}.py{note}")
