"""Harvest official Chinese terminology from Zelda Wiki's translation data.

The Wind Waker never had a Chinese release, but the series terms it shares with
the games that did (Breath of the Wild, Tears of the Kingdom, Echoes of Wisdom,
Link's Awakening, Skyward Sword HD...) do have official Traditional Chinese
names from Nintendo. Zelda Wiki keeps those in machine-readable Data: pages, one
{{Nomenclature/Store}} block per term, with a zhT (Traditional) and zhS
(Simplified) field.

This downloads those pages, caches the raw wikitext under work/zeldawiki/, and
writes a glossary of English term -> official Chinese renderings. Content on
Zelda Wiki is under the GNU Free Documentation License.
"""
import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request

API = "https://zeldawiki.wiki/w/api.php"
USER_AGENT = "tww-zhtw-glossary/1.0 (fan translation terminology check)"
# Zelda games that shipped with an official Chinese localisation.
DEFAULT_GAMES = ["BotW", "TotK", "EoW", "CoH", "LANS", "SSHD", "AoC", "AoI", "SSBU"]

STORE = "{{Nomenclature/Store|"


def api(params):
    params = dict(params, format="json", formatversion="2")
    url = f"{API}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def list_pages():
    pages, params = [], {
        "action": "query", "list": "allpages", "apnamespace": "10004",
        "apprefix": "Translations/", "aplimit": "500",
    }
    while True:
        data = api(params)
        pages += [p["title"] for p in data["query"]["allpages"]]
        if "continue" not in data:
            return pages
        params.update(data["continue"])


def fetch_page(title, cache_dir, delay):
    safe = title.replace("/", "__").replace(":", "_")
    path = os.path.join(cache_dir, safe + ".wiki")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()
    time.sleep(delay)
    data = api({"action": "query", "prop": "revisions", "rvprop": "content",
                "rvslots": "main", "titles": title})
    page = data["query"]["pages"][0]
    text = page.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("content", "")
    os.makedirs(cache_dir, exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
    return text


def split_args(body):
    """Split template arguments on top-level pipes."""
    args, depth, start = [], 0, 0
    i = 0
    while i < len(body):
        pair = body[i:i + 2]
        if pair in ("{{", "[["):
            depth += 1
            i += 2
            continue
        if pair in ("}}", "]]"):
            depth -= 1
            i += 2
            continue
        if body[i] == "|" and depth == 0:
            args.append(body[start:i])
            start = i + 1
        i += 1
    args.append(body[start:])
    return args


def iter_stores(text):
    pos = 0
    while True:
        start = text.find(STORE, pos)
        if start == -1:
            return
        i = start + 2
        depth = 1
        while i < len(text) and depth:
            if text[i:i + 2] == "{{":
                depth += 1
                i += 2
            elif text[i:i + 2] == "}}":
                depth -= 1
                i += 2
            else:
                i += 1
        yield split_args(text[start + 2:i - 2])
        pos = i


UNWRAP = [
    (re.compile(r"\{\{(?:Romanize|Ruby)\|([^|{}]*)\|[^{}]*\}\}"), r"\1"),
    (re.compile(r"\{\{Color[^|{}]*\|[^|{}]*\|([^{}]*)\}\}"), r"\1"),
    (re.compile(r"\[\[[^\]|]*\|([^\]]*)\]\]"), r"\1"),
    (re.compile(r"\[\[([^\]]*)\]\]"), r"\1"),
]
DROP = re.compile(r"\{\{[^{}]*\}\}|<[^<>]*>|'{2,}")


def clean(value):
    for _ in range(4):
        for pattern, repl in UNWRAP:
            value = pattern.sub(repl, value)
    return [part.strip() for part in DROP.sub("\n", value).split("\n") if part.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", nargs="*", default=DEFAULT_GAMES,
                    help='games to harvest, or "all"')
    ap.add_argument("--cache", default="work/zeldawiki")
    ap.add_argument("--out", default="text/glossary_official.json")
    ap.add_argument("--delay", type=float, default=0.4)
    args = ap.parse_args()

    titles = list_pages()
    if args.games != ["all"]:
        wanted = {f"Data:Translations/{g}" for g in args.games}
        titles = [t for t in titles if t.rsplit("/", 3)[0] in wanted or
                  any(t == w or t.startswith(w + "/") for w in wanted)]
    print(f"{len(titles)} translation pages")

    terms = {}
    for n, title in enumerate(titles, 1):
        text = fetch_page(title, args.cache, args.delay)
        for fields in iter_stores(text):
            if len(fields) < 3:
                continue
            game, name = fields[1].strip(), fields[2].strip()
            if not name:
                continue
            entry = terms.setdefault(name, {"zhT": {}, "zhS": {}})
            for field in fields[3:]:
                key, _, value = field.partition("=")
                key = key.strip()
                if key in ("zhT", "zhS"):
                    for rendering in clean(value):
                        entry[key].setdefault(rendering, []).append(game)
        print(f"  [{n}/{len(titles)}] {title}")

    terms = {k: v for k, v in terms.items() if v["zhT"] or v["zhS"]}
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(terms, f, ensure_ascii=False, indent=1, sort_keys=True)
    traditional = sum(1 for v in terms.values() if v["zhT"])
    print(f"{len(terms)} terms with an official Chinese name "
          f"({traditional} with Traditional) -> {args.out}")


if __name__ == "__main__":
    main()
