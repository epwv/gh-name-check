# gh-name-check

A GitHub username availability checker and generator. It queries GitHub's signup endpoint directly — no API token required.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Configuration](#configuration)
- [checker.py](#checkerpy)
- [generator.py](#generatorpy)
- [How the Endpoint Works](#how-the-endpoint-works)
- [Proxy Setup](#proxy-setup)
- [Rate Limiting](#rate-limiting)
- [Output Files](#output-files)
- [File Structure](#file-structure)
- [Tips](#tips)
- [Limitations](#limitations)
- [FAQ](#faq)
- [Troubleshooting](#troubleshooting)

## Overview

Two Python scripts:

- **checker.py** — batch-checks existing username lists. Uses asyncio and aiohttp for concurrent requests. Reads from `lists/`, writes available names to `confirmed/`.
- **generator.py** — creates random usernames and checks them immediately. Configurable patterns. Saves available names to `lists/`.

Both scripts use the same undocumented GitHub signup endpoint that the website uses during account creation.

## Installation

```bash
git clone https://github.com/epwv/gh-name-check.git
cd gh-name-check
pip install aiohttp colorama
```

Python 3.7+. No API keys required.

## Configuration

The first run launches an interactive setup wizard. `config/config.json` can also be edited directly:

```json
{
  "token": "",
  "delay": 0.5,
  "proxies": ""
}
```

- **token** — GitHub personal access token. Optional, used only as an API fallback.
- **delay** — seconds between requests in the generator.
- **proxies** — path to the proxy list. Leave empty to default to `proxies.txt` in the project root.

## checker.py

### How it works

1. Reads all usernames from `lists/3_letter_usernames.txt` and `lists/4_letter_usernames.txt`
2. Validates each username (max length 39, no leading/trailing hyphens, no invalid characters)
3. Filters out already-confirmed names from `confirmed/available_confirmed.txt`
4. Fires up to 50 concurrent requests using asyncio and aiohttp
5. Picks a random proxy from the list for each request
6. Writes available names to `confirmed/available_confirmed.txt`

### Features

- Live progress counter (done/total, requests per second, available/taken/unknown counts, ETA)
- Rate limit handling (429/403 detection with exponential backoff, up to 3 retries)
- API fallback when a token is configured
- Batch numbering with timestamps in the output
- Retry pass for unknown results
- Graceful Ctrl+C handling with a final summary
- Proxy confirmation prompt on startup

### Running

```bash
python src/checker.py
```

## generator.py

### How it works

1. Shows a menu (3-letter, 4-letter, both, adjust delay, quit)
2. Generates random strings using lowercase letters and digits
3. Checks each one via the signup endpoint
4. Displays green (available), red (taken), or yellow (unknown)
5. Appends available names to the appropriate list file
6. Runs until stopped

### Menu options

- **3** — generate 3-character names, writes to `lists/3_letter_usernames.txt`
- **4** — generate 4-character names, writes to `lists/4_letter_usernames.txt`
- **b** — generate both 3- and 4-character names simultaneously
- **a** — adjust the delay between requests (saved to config)
- **q** — quit

### Running

```bash
python src/generator.py
```

Uses a `seen` set to avoid regenerating the same username within a session.

## How the Endpoint Works

```
GET https://github.com/signup_check_new/username
    ?suggest_usernames=true
    &value={username}
```

- **200** — available
- **422** — taken
- **429/403** — rate limited

No authentication required. This is the same endpoint github.com uses during signup. The token is optional and used only as a fallback.

## Proxy Setup

Create `proxies.txt` with one proxy per line:

```
http://1.2.3.4:3128
http://5.6.7.8:8080
socks5://9.10.11.12:1080
```

The checker picks a random proxy for each request. No proxies are bundled. Without proxies, expect to be rate-limited quickly.

## Rate Limiting

Signs: 429/403 responses, all names showing as unknown.

- **checker** — exponential backoff (5s, 10s, 20s), up to 3 retries, and runs at lower concurrency when no proxies are configured
- **generator** — exponential backoff (10s, 20s, 40s), up to 3 retries

To avoid it: use a larger proxy pool, increase the delay in the generator, or run during off-peak hours.

## Output Files

- `confirmed/available_confirmed.txt` — checker output with batch headers and timestamps
- `lists/3_letter_usernames.txt` — 3-character names (read by the checker, written by the generator)
- `lists/4_letter_usernames.txt` — 4-character names (same pattern)

## Tips

- Use the generator to build initial lists, then feed them into the checker for batch verification.
- The checker is faster since it uses concurrent requests.
- Run the checker periodically to keep the confirmed list fresh.
- Names showing as unknown might still be available — try manually or retry later.
- 3-letter and 4-letter names are rare; expect most to be taken.

## Limitations

- False positives and false negatives happen. The endpoint's behavior isn't guaranteed.
- Without proxies, expect rate limiting within seconds.
- The endpoint may change or disappear at any time.
- The generator only produces random letter+number combinations; no custom patterns.
- Everything is stored as flat text files, no database.
- No auto-registration functionality.

## FAQ

**Q: Do I need a GitHub token?**
A: No. It's entirely optional; both scripts work fine without one.

**Q: Why are all names showing as unknown?**
A: You're likely rate-limited. Add proxies or increase the delay.

**Q: Why does it say available but GitHub says taken?**
A: A false positive — the endpoint isn't always accurate. Try again later.

**Q: Can I use this to reserve names automatically?**
A: No. This only checks availability; it does not register accounts.

## Troubleshooting

**config.json not found** — run either script to trigger interactive setup.

**Module not found** — `pip install aiohttp colorama`

**Permission denied** — check write permissions in the project directory.

**Connection errors** — check your internet connection and proxy validity.

**Generator finds nothing** — 3- and 4-letter names are extremely rare; let it run longer.
