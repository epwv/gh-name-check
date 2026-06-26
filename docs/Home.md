# gh-name-check

github username availability checker & generator. hits github's signup endpoint directly — no api token required.

## table of contents

- [overview](#overview)
- [installation](#installation)
- [configuration](#configuration)
- [checkerpy](#checkerpy)
- [generatorpy](#generatorpy)
- [how the endpoint works](#how-the-endpoint-works)
- [proxy setup](#proxy-setup)
- [rate limiting](#rate-limiting)
- [output files](#output-files)
- [file structure](#file-structure)
- [tips](#tips)
- [limitations](#limitations)
- [faq](#faq)
- [troubleshooting](#troubleshooting)

## overview

two python scripts:

- **checkerpy** — batch-checks existing username lists. turbo async using aiohttp. reads from `lists/`, writes available names to `confirmed/`.
- **generatorpy** — creates random usernames and checks them immediately. configurable patterns. saves available names to `lists/`.

both scripts use the same undocumented github signup endpoint that the website uses during account creation.

## installation

```bash
git clone https://github.com/epwv/gh-name-check.git
cd gh-name-check
pip install aiohttp colorama
```

python 3.7+. no api keys required.

## configuration

first run launches an interactive setup wizard. or edit `config/configjson` directly:

```json
{
  "token": "",
  "delay": 0.5,
  "proxies": ""
}
```

- **token** — github personal access token. optional. only used as api fallback.
- **delay** — seconds between requests in the generator.
- **proxies** — path to proxy list. leave empty for `proxiestxt` in root.

## checkerpy

### how it works

1. reads all usernames from `lists/3_letter_usernamestxt` and `lists/4_letter_usernamestxt`
2. validates each username (length max 39 no leading/trailing hyphens no invalid chars)
3. filters out already-confirmed names from `confirmed/available_confirmedtxt`
4. fires up to 50 concurrent requests using asyncio + aiohttp
5. picks a random proxy from the list for each request
6. writes available names to `confirmed/available_confirmedtxt`

### features

- live progress counter (done/total, rps, available/taken/unknown counts, eta)
- rate limit handling (429/403 detection with 5s backoff and retry)
- api fallback when token is configured
- batch numbering with timestamps in output
- retry pass for unknown results
- graceful ctrl+c with final summary
- proxy confirmation prompt on startup

### running

```bash
python src/checkerpy
```

## generatorpy

### how it works

1. shows a menu (3-letter 4-letter both adjust delay quit)
2. generates random strings using lowercase letters and digits
3. checks each one via the signup endpoint
4. displays green (available) red (taken) yellow (unknown)
5. appends available names to the appropriate list file
6. runs until you stop it

### menu options

- **3** — generate 3-character names writes to `lists/3_letter_usernamestxt`
- **4** — generate 4-character names writes to `lists/4_letter_usernamestxt`
- **b** — generate both 3 and 4 character names simultaneously
- **a** — adjust delay between requests (saved to config)
- **q** — quit

### running

```bash
python src/generatorpy
```

uses a `seen` set to avoid regenerating the same username in a session.

## how the endpoint works

```
GET https://githubcom/signup_check_new/username
    ?suggest_usernames=true
    &value={username}
```

- **200** = available
- **422** = taken
- **429/403** = rate limited

no authentication required. this is the same endpoint github.com uses during signup. the token is optional and only used as a fallback.

## proxy setup

create `proxiestxt` with one proxy per line:

```
http://1234:3128
http://5678:8080
socks5://9101112:1080
```

the checker picks a random proxy for each request. no proxies bundled. without proxies you will get rate-limited quickly.

## rate limiting

signs: 429/403 responses, all names showing unknown.

- **checker** — waits 5s then retries once
- **generator** — waits 10s then retries once

to avoid: use a large proxy pool, increase delay in generator, run during off-peak hours.

## output files

- `confirmed/available_confirmedtxt` — checker output with batch headers and timestamps
- `lists/3_letter_usernamestxt` — 3-character names (read by checker written by generator)
- `lists/4_letter_usernamestxt` — 4-character names (same pattern)

## tips

- use generator to build initial lists then feed them into the checker for batch verification
- the checker is faster since it uses concurrent requests
- run the checker periodically to keep confirmed list fresh
- names showing unknown might still be available — try manually or retry later
- 3-letter and 4-letter names are rare. expect mostly taken.

## limitations

- false positives / false negatives happen. the endpoint lies sometimes.
- without proxies you will get rate-limited within seconds.
- endpoint may change or disappear at any time.
- generator only does random letter+number combos. no custom patterns.
- everything is flat text files. no database.
- no auto-register functionality.

## faq

**q: do i need a github token?**
a: no. completely optional. both scripts work fine without it.

**q: why are all names showing as unknown?**
a: rate-limited. add proxies or increase delay.

**q: why does it say available but github says taken?**
a: false positive. the endpoint lies. try again later.

**q: can i snipe names with this?**
a: no. this only checks availability. no auto-register.

## troubleshooting

**configjson not found** — run any script for interactive setup.

**module not found** — `pip install aiohttp colorama`

**permission denied** — check write permissions in the project directory.

**connection errors** — check internet connection and proxy validity.

**generator finds nothing** — 3/4-letter names are extremely rare. let it run longer.
