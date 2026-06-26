# gh-name-check

username checker & generator that hits github's signup endpoint directly. no api token needed.

## scripts

**checker.py** — batch-checks usernames from text files. turbo async using aiohttp.
- reads from `lists/`, writes available names to `confirmed/`
- tracks progress with live counter
- random proxy rotation
- handles 429/403 with 5-10s backoff retry
- ctrl+c prints a summary

**generator.py** — generates random usernames and checks them on the fly.
- configurable patterns (default: letter + 4 numbers)
- saves available names to `lists/`
- adjustable delay (menu option `a`)
- ctrl+c prints a summary

## first run

both scripts launch interactive setup if `config/config.json` doesnt exist:
- github token (optional, api fallback)
- delay between requests (generator only)
- path to proxy list

## how it works

```
GET /signup_check_new/username?suggest_usernames=true&value=<username>
```

- 200 = available
- 422 = taken

## proxy setup

proxies go in `proxies.txt`, one per line. no proxies bundled.
the checker cycles through them randomly.

## limitations

- false positives / false negatives happen
- no proxy = instant rate limit
- endpoint might change at any time
