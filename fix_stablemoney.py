import json
import ats

d = json.load(open('companies.json'))

updated = False
for c in d:
    if c['name'] == 'Stable Money':
        c['ats'] = 'lever'
        c['slug'] = 'stable-money1'
        c['method'] = 'manual-verified'
        updated = True
        print('Updated Stable Money entry:', c)

if not updated:
    print('WARNING: no company named "Stable Money" found in companies.json — nothing changed.')
else:
    json.dump(d, open('companies.json', 'w'), indent=2)
    with open('companies.json', 'a') as f:
        f.write('\n')
    print('Saved companies.json.')

    print('\nVerifying live board...')
    jobs = ats.fetch_jobs('lever', 'stable-money1', 'Stable Money')
    print(f'{len(jobs)} roles found on jobs.lever.co/stable-money1:')
    for j in jobs[:10]:
        print(' -', j['title'], '|', j['location'])
