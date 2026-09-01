import json

d = json.load(open('companies.json'))

# Genuinely unresolved: no ats AND no board_url. This excludes companies that
# verify.py's table shows as "unresolved" only because they have board_url
# set without a matching "ats" field (a display gap in verify.py, not a real
# gap in coverage).
truly_unresolved = [c for c in d if not c.get('ats') and not c.get('board_url')]

print(f"total companies: {len(d)}")
print(f"genuinely unresolved (no ats, no board_url): {len(truly_unresolved)}")
print()
for c in truly_unresolved:
    print(f"{c['name']:<28} {c['domain']:<30} sector={c.get('sector','?')}")
