# ats-watch

Polls public ATS posting endpoints for new roles matching a fixed profile, and
alerts on Telegram. No API keys, no paid services, no database. State lives in
this repo.

Covered platforms with public JSON APIs: Greenhouse, Lever, Ashby, Workable,
SmartRecruiters. Detected but not polled: Darwinbox, Keka, Zoho Recruit,
PyjamaHR, Recruitee. Those have no documented public JSON endpoint and are
flagged as `unsupported:<platform>` for manual checking.

## Setup

### 1. Local check, 5 minutes

```bash
git clone <your-repo> && cd ats-watch
python3 discover.py
```

This resolves each company domain to an ATS and slug. Nothing is hardcoded, so
a wrong or dead domain simply prints `no public board found` and is skipped.
Expect roughly half the seed list to resolve on the first pass. That is normal.

Then check the filter output before wiring up alerts:

```bash
python3 watch.py --dry-run
```

Read every match and every miss. If it is returning 40 roles, `title_include`
is too broad. If it is returning zero, `title_exclude` is eating them. Tune
`filters.json` and re-run until the output is roles you would actually open.
Do this before step 2. It is the only step that needs judgment.

### 2. Telegram bot, 3 minutes

1. Message `@BotFather` on Telegram, send `/newbot`, copy the token.
2. Send any message to your new bot.
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `chat.id`.

Add both as repo secrets under Settings, Secrets and variables, Actions:
`TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`.

### 3. Seed the state

Run the `watch` workflow manually with `seed: true`. This records every
currently open role as already seen, so your first real run alerts only on
genuinely new postings instead of dumping 200 existing ones at you.

### 4. Let it run

The `watch` workflow polls every 30 minutes. The `discover` workflow re-runs
the prober weekly to pick up companies you have added.

## Adding companies

Append name, domain and sector to `companies.json`. Leave `ats` and `slug` out.
The prober fills them in. Feed it your funding-news pipeline weekly, since a
company that just raised is about to open roles.

## Triage

Each run writes `digest.md` with the new batch. Paste it into Claude alongside
your resume for fit scoring and a first-pass outreach angle, rather than paying
for an API to do it automatically.

## Known limitations

- GitHub delays scheduled workflows under load. Real cadence is closer to 30 to
  60 minutes than exactly 30.
- Scheduled workflows are disabled after 60 days of repo inactivity. The state
  commits from each run keep this from triggering.
- Some Lever and SmartRecruiters customers disable their public endpoint. Those
  companies will resolve but return nothing.
- ATS response shapes change occasionally. If one platform goes silent while
  others keep working, check the normalizer in `ats.py` first.
