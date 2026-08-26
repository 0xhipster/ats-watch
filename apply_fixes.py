import json

path = 'companies.json'
d = json.load(open(path))

fixes = {
    "BharatPe":  ("darwinbox", "https://bharatpe.darwinbox.in/ms/candidatev2/main/careers/allJobs"),
    "MobiKwik":  ("darwinbox", "https://mobikwik.darwinbox.in/ms/candidatev2/main/careers/home"),
    "ClearTax":  ("darwinbox", "https://clear.darwinbox.in/ms/candidatev2/main/careers/allJobs"),
}

applied = []
for c in d:
    if c["name"] in fixes:
        platform, url = fixes[c["name"]]
        c["board_platform"] = platform
        c["board_url"] = url
        applied.append(c["name"])
    if c["name"] == "Finova Capital":
        c["domain"] = "fplabs.tech"
        applied.append("Finova Capital (domain fix)")

json.dump(d, open(path, 'w'), indent=2)
with open(path, 'a') as f:
    f.write("\n")

print("applied:", applied)
doms = [c["domain"] for c in d]
assert len(doms) == len(set(doms)), "DUPLICATE DOMAIN — did not expect this"
print("total companies:", len(d))
