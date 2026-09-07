import json

d = json.load(open('companies.json'))

updated = False
for c in d:
    if c['name'] == 'Scapia':
        c['board_platform'] = 'freshteam'
        c['board_url'] = 'https://scapia.freshteam.com/jobs'
        updated = True
        print('Updated Scapia entry:', c)

if not updated:
    print('WARNING: no company named "Scapia" found in companies.json')
else:
    json.dump(d, open('companies.json', 'w'), indent=2)
    with open('companies.json', 'a') as f:
        f.write('\n')
    print('Saved companies.json.')
