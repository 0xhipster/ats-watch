import json
import ats

# Apply the confirmed real Lever slug for FamApp (jobs.lever.co/fampay),
# found manually earlier today. Their old brand name was "FamPay", which is
# why the slug doesn't match the current famapp.in domain.
d = json.load(open('companies.json'))

updated = False
for c in d:
    if c['name'] == 'FamApp':
        c['ats'] = 'lever'
        c['slug'] = 'fampay'
        c['method'] = 'manual-verified'
        updated = True
        print('Updated FamApp entry:', c)

if not updated:
    print('WARNING: no company named "FamApp" found in companies.json — nothing changed.')
else:
    json.dump(d, open('companies.json', 'w'), indent=2)
    with open('companies.json', 'a') as f:
        f.write('\n')
    print('Saved companies.json.')

    # Verify it's real before you trust it.
    print('\nVerifying live board...')
    jobs = ats.fetch_jobs('lever', 'fampay', 'FamApp')
    print(f'{len(jobs)} roles found on jobs.lever.co/fampay:')
    for j in jobs[:8]:
        print(' -', j['title'])
