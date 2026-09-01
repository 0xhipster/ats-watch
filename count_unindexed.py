import json

d = json.load(open('companies.json'))

watched = [c for c in d if c.get('ats') and not str(c.get('ats')).startswith('unsupported')]
watched += [c for c in d if c.get('board_url') and c not in watched]

unresolved = [c for c in d if not c.get('ats') and not c.get('board_url')]

print(f"total companies in file      : {len(d)}")
print(f"actually watched (either lane): {len(watched)}")
print(f"NOT indexed / unresolved      : {len(unresolved)}")
print()
print("--- confirmed NOT-indexed list ---")
for c in sorted(unresolved, key=lambda x: x['name']):
    print(f"{c['name']:<28} {c['domain']:<30} sector={c.get('sector','?')}")
