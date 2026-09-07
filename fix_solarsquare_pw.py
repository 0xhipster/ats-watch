import json

d = json.load(open('companies.json'))
by_name = {c['name']: c for c in d}

fixes = {
    'SolarSquare':    ('keka', 'https://solarsquare.keka.com/careers'),
    'Physics Wallah': ('darwinbox', 'https://pwhr.darwinbox.in/ms/candidate/a62d7a6e288992/careers/others'),
}

for name, (platform, url) in fixes.items():
    if name in by_name:
        by_name[name]['board_platform'] = platform
        by_name[name]['board_url'] = url
        print(f'Applied {name}: {platform} -> {url}')
    else:
        print(f'! {name} not found in companies.json')

json.dump(d, open('companies.json', 'w'), indent=2)
with open('companies.json', 'a') as f:
    f.write('\n')
print('\nSaved companies.json.')
