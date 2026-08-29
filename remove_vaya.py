import json

d = json.load(open('companies.json'))
before = len(d)

d = [c for c in d if c.get('name') != 'Vaya']

after = len(d)
json.dump(d, open('companies.json', 'w'), indent=2)
with open('companies.json', 'a') as f:
    f.write('\n')

print(f"removed Vaya: {before} -> {after} companies")
