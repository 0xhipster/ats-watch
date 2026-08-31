import json
import ats

d = json.load(open('companies.json'))

# Nurix AI: discover.py matched "greenhouse/nurix", but that is Nurix
# Therapeutics, a San Francisco biopharma company - completely unrelated,
# just sharing a name. Confirmed via web search: every job on that board is
# pharma/biotech (Preclinical Pharmacology, Medicinal Chemistry, etc).
# The REAL Nurix AI (Accel-backed conversational AI, India) was personally
# verified in-browser today at nurix.keka.com/careers with real roles
# including Marketing Manager and Growth Intern. Fixing the collision.
for c in d:
    if c['name'] == 'Nurix AI':
        c['ats'] = None
        c['slug'] = None
        c['method'] = None
        c['board_platform'] = 'keka'
        c['board_url'] = 'https://nurix.keka.com/careers/'
        print('Fixed Nurix AI: removed wrong Greenhouse match, added verified Keka board')

# Scimplify and Venwiz: discover.py's careers-page tracer found these on Keka
# directly. Both were also personally verified in-browser today as real,
# active companies.
for c in d:
    if c['name'] == 'Scimplify':
        c['board_platform'] = 'keka'
        c['board_url'] = 'https://scimplify.keka.com/careers'
        print('Confirmed Scimplify board URL saved')
    if c['name'] == 'Venwiz':
        c['board_platform'] = 'keka'
        c['board_url'] = 'https://venwiztechnologies.keka.com/careers'
        print('Confirmed Venwiz board URL saved')

json.dump(d, open('companies.json', 'w'), indent=2)
with open('companies.json', 'a') as f:
    f.write('\n')
print('\nSaved companies.json.')

# Verify Supabase's Ashby match right away, same discipline as everything else.
print('\nVerifying Supabase (ashby/supabase)...')
jobs = ats.fetch_jobs('ashby', 'supabase', 'Supabase')
print(f'{len(jobs)} roles found:')
for j in jobs[:5]:
    print(f'   - {j["title"]} | {j["location"]}')
