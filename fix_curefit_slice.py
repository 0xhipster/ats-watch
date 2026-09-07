import json

d = json.load(open('companies.json'))
by_name = {c['name']: c for c in d}

# Both confirmed real via browser today. Neither is on one of the 5 direct
# platforms - both are fully custom sites - so there's no ats/slug to set,
# only a domain correction so future census/manual checks look in the right
# place. Curefit's real domain is careers.cult.fit (132 open roles seen
# directly). Slice rebranded to slice.bank.in (Slice Small Finance Bank).
fixes = {
    'Curefit': 'careers.cult.fit',
    'Slice':   'slice.bank.in',
}

for name, domain in fixes.items():
    if name in by_name:
        old = by_name[name]['domain']
        by_name[name]['domain'] = domain
        print(f'{name}: domain corrected {old} -> {domain}')
    else:
        print(f'! {name} not found')

json.dump(d, open('companies.json', 'w'), indent=2)
with open('companies.json', 'a') as f:
    f.write('\n')
print('\nSaved companies.json.')
print('\nNote: neither has a direct-ATS slug - both are custom sites with')
print('click-through job lists. Domain corrected so census.py checks the')
print('right URL on the next run, but these remain unresolved for the fast')
print('lane until/unless an ATS platform is found underneath.')
