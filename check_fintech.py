import json

fintech_list = [
    'Ambak','Aptus Housing Finance','Bajaj Holdings','BankBazaar','BharatPe','Bright',
    'Citrus Payment','ClearTax','CoinSwitch','CRED','Cybrilla','Digit Insurance',
    'Drip Capital','Edelweiss','Equitas','FamApp','Finova Capital','Fintellix',
    'Five Star Business Finance','GoKwik','GoodScore','Groww','Happay','Hubble','ICRA',
    'Ignosis AI','India Shelter Finance','Jupiter','Khatabook','Manappuram',
    'Metropolitan Stock Exchange','MobiKwik','Neo Wealth','Nimbbl','OneAssist',
    'OneCard','Osfin','PayGlocal','Pine Labs','Plum','Polygon Labs','PowerUp Money',
    'Prayaan Capital','Prizm','ProgCap','Razorpay','Rupeek','Salaryse','Sarvagram',
    'Scapia','SKS Microfinance','smallcase','Stable Money','Star Health','Turtlemint',
    'Twid','Ujjivan','Yubi','Zamp','Zanskar','Zet',
]

legacy = {
    'Bajaj Holdings','Aptus Housing Finance','ICRA','Manappuram','Equitas',
    'Star Health','Ujjivan','SKS Microfinance','Edelweiss',
    'Metropolitan Stock Exchange','India Shelter Finance','Five Star Business Finance',
    'Citrus Payment','Prizm',
}

d = json.load(open('companies.json'))
by_name = {c['name'].lower(): c for c in d}

watched, strip, priority = [], [], []
for name in fintech_list:
    c = by_name.get(name.lower())
    is_watched = c and (
        (c.get('ats') and not str(c.get('ats')).startswith('unsupported'))
        or c.get('board_url')
    )
    if is_watched:
        watched.append(name)
    elif name in legacy:
        strip.append(name)
    else:
        priority.append(name)

print(f'ALREADY WATCHED: {len(watched)}')
for n in watched:
    print(' -', n)

print(f'\nLEGACY/STRIP: {len(strip)}')
for n in strip:
    print(' -', n)

print(f'\nPRIORITY LIST: {len(priority)}')
for n in priority:
    print(' -', n)
