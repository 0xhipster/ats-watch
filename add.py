"""
Bulk company adder.

Hand-editing companies.json is how you break companies.json. This reads a
plain text file of companies, merges them in, dedupes, and validates the
result before writing anything.

USAGE
-----
1. Make a file called new.txt in this folder. One company per line.
   Either of these formats works:

       Peak XV Portfolio Co, peakxvco.com, saas
       stripe.com

   If you give only a domain, the name is derived from it and sector is
   left blank. Blank lines and lines starting with # are ignored.

2. Run:

       python3 add.py

   Nothing is written unless every check passes. Then run discover.py.

Safety: the original file is copied to companies.json.bak before any write,
and the merged result is re-parsed and validated before it replaces the
original. If anything fails, companies.json is left untouched.
"""

import json
import os
import shutil
import sys

CONFIG = "companies.json"
INPUT = "new.txt"
BACKUP = "companies.json.bak"


def normalise_domain(raw):
    """Strip scheme, www, path, and trailing slash. Return bare domain."""
    d = raw.strip().lower()
    for prefix in ("https://", "http://"):
        if d.startswith(prefix):
            d = d[len(prefix):]
    if d.startswith("www."):
        d = d[4:]
    d = d.split("/")[0].split("?")[0].strip()
    return d


def name_from_domain(domain):
    stem = domain.split(".")[0]
    return stem.replace("-", " ").replace("_", " ").title()


def parse_line(line):
    """Return (name, domain, sector) or None if the line is not usable."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    parts = [p.strip() for p in line.split(",")]
    if len(parts) >= 2:
        name = parts[0]
        domain = normalise_domain(parts[1])
        sector = parts[2] if len(parts) >= 3 and parts[2] else ""
    else:
        domain = normalise_domain(parts[0])
        name = name_from_domain(domain)
        sector = ""

    if not domain or "." not in domain:
        print(f"  ! skipping unusable line: {line!r}")
        return None
    return name, domain, sector


def main():
    if not os.path.exists(INPUT):
        sys.exit(f"No {INPUT} found. Create it with one company per line, then re-run.")
    if not os.path.exists(CONFIG):
        sys.exit(f"No {CONFIG} found. Are you in the atswatch folder?")

    with open(CONFIG) as f:
        existing = json.load(f)
    if not isinstance(existing, list):
        sys.exit(f"{CONFIG} is not a JSON list. Refusing to touch it.")

    seen_domains = {c.get("domain", "").lower() for c in existing}
    seen_names = {c.get("name", "").lower().replace(" ", "") for c in existing}

    added, dupes, bad = [], [], 0
    batch_domains = set()

    with open(INPUT, encoding="utf-8") as f:
        for line in f:
            parsed = parse_line(line)
            if not parsed:
                if line.strip() and not line.strip().startswith("#"):
                    bad += 1
                continue
            name, domain, sector = parsed

            if domain in seen_domains or name.lower().replace(" ", "") in seen_names:
                dupes.append(f"{name} ({domain})")
                continue
            if domain in batch_domains:
                dupes.append(f"{name} ({domain}) [duplicate within new.txt]")
                continue

            batch_domains.add(domain)
            entry = {"name": name, "domain": domain}
            if sector:
                entry["sector"] = sector
            added.append(entry)

    print(f"\nread {INPUT}")
    print(f"  new       : {len(added)}")
    print(f"  duplicates: {len(dupes)}")
    print(f"  unusable  : {bad}")

    if dupes:
        print("\nskipped as already present:")
        for d in dupes:
            print(f"  - {d}")

    if not added:
        print("\nNothing new to add. companies.json unchanged.")
        return

    print("\nwill add:")
    for e in added:
        print(f"  + {e['name']:<26} {e['domain']}")

    merged = existing + added

    # Validate BEFORE touching the real file.
    doms = [c.get("domain") for c in merged]
    if len(doms) != len(set(doms)):
        sys.exit("ABORT: merge produced duplicate domains. companies.json unchanged.")
    if not all(c.get("name") and c.get("domain") for c in merged):
        sys.exit("ABORT: merge produced an entry missing name or domain. Unchanged.")
    try:
        json.loads(json.dumps(merged))
    except (TypeError, ValueError) as e:
        sys.exit(f"ABORT: merged data is not valid JSON ({e}). Unchanged.")

    shutil.copy2(CONFIG, BACKUP)
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
        f.write("\n")

    # Read it back and confirm it parses, so a truncated write cannot pass silently.
    with open(CONFIG) as f:
        check = json.load(f)
    print(f"\nwrote {CONFIG}: {len(existing)} -> {len(check)} companies")
    print(f"backup saved to {BACKUP}")
    print("\nNext: python3 discover.py     (resolves the new ones only)")
    print("Then: python3 verify.py       (confirms they are real boards)")


if __name__ == "__main__":
    main()
