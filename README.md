# gh-name-check

[![github](https://img.shields.io/badge/-github-000000?logo=github&labelColor=000000&style=for-the-badge)](https://github.com/epwv/gh-name-check)
[![python](https://img.shields.io/badge/-python-3776AB?logo=python&labelColor=000000&style=for-the-badge)](https://github.com/epwv/gh-name-check)

includes generated username lists (`lists/`) and confirmed available names (`confirmed/`).

this code is bad, buggy, and slightly vibecoded. it works (sometimes).
original by **Kai Zhao**, butchered and extended by **epwv** with minor help from **opencode** (yes opencode, who on earth uses that, am i right?).

you need your own proxies. find free ones or use your own.

## Clone & Run

```bash
git clone https://github.com/epwv/gh-name-check.git
cd gh-name-check
python src/checker.py
python src/generator.py
```

first run walks you through setup interactively. or edit `config/config.json` directly:
- `token` — github personal access token (optional, for api fallback)
- `delay` — seconds between requests in generator
- `proxies` — path to proxy list (leave empty to use `proxies.txt` in root)

## Structure

```
github-checker/
├── src/
│   ├── checker.py          batch checker
│   └── generator.py        username generator & verifier
├── config/
│   └── config.json         settings (token, delay, proxies)
├── lists/
│   ├── 3_letter_usernames.txt
│   ├── 4_letter_usernames.txt
│   └── avaliable2usernames.txt
├── confirmed/
│   └── avaliable_confirmed.txt
├── proxies.txt             your proxy list (one per line)
└── README.md
```

both hit `/signup_check_new/username` — no api token needed. token is optional fallback.

the checker can always be wrong. false positives and false negatives happen. dont trust it blindly.
