import json

d = json.load(open('companies.json'))

fixes = {
    "RapidCanvas": ("keka", "https://rapidcanvas.keka.com/careers/"),
    "OrbitShift":  ("zoho_recruit", "https://orbitshift.zohorecruit.in/jobs/Careers"),
}

applied = []
for c in d:
    if c['name'] in fixes:
        platform, url = fixes[c['name']]
        c['board_platform'] = platform
        c['board_url'] = url
        applied.append(c['name'])

json.dump(d, open('companies.json', 'w'), indent=2)
with open('companies.json', 'a') as f:
    f.write('\n')

print(f"applied: {applied}")
print("Saved companies.json.")
