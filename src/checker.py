import asyncio
import json
import os
import re
import sys
import time
import random
from datetime import datetime
from pathlib import Path
import aiohttp
from colorama import init, Fore, Style

init(autoreset=True)

DIR = Path(__file__).parent.parent
CFG_PATH = DIR / "config" / "config.json"

def setup():
    print(Fore.CYAN + "\nfirst time setup")
    token = input("token (optional): ").strip()
    proxy_path = input("proxy file (optional): ").strip()
    delay = input("delay in seconds (default 0.5): ").strip()
    try:
        delay = float(delay) if delay else 0.5
    except:
        delay = 0.5
    if delay < 0:
        delay = 0.5
    cfg = {"token": token, "delay": delay, "proxies": proxy_path}
    CFG_PATH.write_text(json.dumps(cfg, indent=2))
    print(Fore.GREEN + "saved. rerun the script.")
    sys.exit(0)

if not CFG_PATH.exists():
    setup()

cfg = json.loads(CFG_PATH.read_text())
TOKEN = cfg.get("token", "") or os.environ.get("GITHUB_TOKEN", "")

LDIR = DIR / "lists"
CDIR = DIR / "confirmed"
LDIR.mkdir(exist_ok=True)
CDIR.mkdir(exist_ok=True)

INPUTS = [
    LDIR / "3_letter_usernames.txt",
    LDIR / "4_letter_usernames.txt",
]
OUTPUT = CDIR / "available_confirmed.txt"

for f in INPUTS:
    f.touch(exist_ok=True)
OUTPUT.touch(exist_ok=True)

PROX_PATH = cfg.get("proxies", "")
PROX_FILE = Path(PROX_PATH).expanduser() if PROX_PATH else DIR / "proxies.txt"

SIGNUP = "https://github.com/signup_check_new/username"
HIDDEN = re.compile(r"[\u00ad\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff\u00a0]")
CONCURRENT = 50
TIMEOUT = 15
UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; rv:121.0) Gecko/20100101 Firefox/121.0",
]

def clean(s):
    return HIDDEN.sub("", s).strip()

def valid(u):
    if not u:
        return False, "empty"
    if len(u) > 39:
        return False, "too long"
    if u[0] == "-" or u[-1] == "-":
        return False, "hyphen edge"
    if "--" in u:
        return False, "double hyphen"
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9-]*", u):
        return False, "bad chars"
    return True, "ok"

def load():
    lines = []
    for f in INPUTS:
        lines += f.read_text().splitlines()
    lines = [l for l in lines if l.strip()]
    good = []
    bad = []
    for u in (clean(l) for l in lines):
        ok, why = valid(u)
        if ok:
            good.append(u)
        else:
            bad.append((u, why))
    if bad:
        print(Fore.YELLOW + f"{len(bad)} bad names")
        for u, w in bad:
            print(f"  {Fore.RED}{u!r} {w}")
    done = set()
    for l in OUTPUT.read_text().splitlines():
        l = l.strip()
        if l and not l.startswith("#"):
            done.add(clean(l))
    if done:
        before = len(good)
        good = [u for u in good if u not in done]
        print(f"{before - len(good)} already confirmed")
    return good

def getprox():
    if not PROX_FILE.exists():
        return []
    raw = PROX_FILE.read_text().strip()
    return [l.strip() for l in raw.splitlines() if l.strip()]

def nextbatch():
    num = 0
    for l in OUTPUT.read_text().splitlines():
        m = re.match(r"# Batch (\d+)", l)
        if m:
            n = int(m.group(1))
            if n > num:
                num = n
    return num + 1

async def chk(sess, name, sem, proxy=None):
    async with sem:
        k = {
            "params": {"suggest_usernames": "true", "value": name},
            "headers": {"User-Agent": random.choice(UAS)},
            "timeout": aiohttp.ClientTimeout(total=TIMEOUT),
        }
        if proxy:
            k["proxy"] = proxy
        try:
            async with sess.get(SIGNUP, **k) as r:
                if r.status == 200:
                    return True
                if r.status == 422:
                    return False
                if r.status in (429, 403):
                    return "limit"
                return None
        except:
            return None

async def apichk(sess, name, sem, token, proxy=None):
    async with sem:
        h = {"User-Agent": random.choice(UAS)}
        if token:
            h["Authorization"] = f"Bearer {token}"
        k = {
            "headers": h,
            "timeout": aiohttp.ClientTimeout(total=10),
        }
        if proxy:
            k["proxy"] = proxy
        try:
            async with sess.get(
                f"https://api.github.com/users/{name}", **k
            ) as r:
                if r.status == 404:
                    return True
                if r.status == 200:
                    return False
                if r.status in (429, 403):
                    return "limit"
                return None
        except:
            return None

async def check(sess, name, token, sem, prox, delay):
    await asyncio.sleep(delay)
    p = random.choice(prox) if prox else None
    if token:
        r = await apichk(sess, name, sem, token, p)
        if r is not None and r != "limit":
            return name, r, "api"
    r = await chk(sess, name, sem, p)
    if r is not None and r != "limit":
        return name, r, "signup"
    if r == "limit":
        await asyncio.sleep(5)
        r = await chk(sess, name, sem, p)
        if r is not None and r != "limit":
            return name, r, "signup"
    return name, None, "fail"

def progress(done, total, avail, taken, unk, start):
    el = time.monotonic() - start
    rps = done / el if el > 0 else 0
    eta = f"{(total - done) / rps:.0f}s" if rps > 0 else "?"
    sys.stdout.write(
        f"\r  {Fore.CYAN}{done}/{total}  {rps:.1f}/s  "
        f"{Fore.GREEN}{len(avail)} avail  {Fore.RED}{taken} taken  "
        f"{Fore.YELLOW}{len(unk)} unk  {Fore.CYAN}eta {eta}{Style.RESET_ALL}   "
    )
    sys.stdout.flush()

def writeavail(name, method, bn, output):
    print(Fore.GREEN + f"\n  {name} ({method})")
    with open(output, "a") as f:
        f.write(name + "\n")

def batchhdr(output, bn):
    with open(output, "a") as f:
        f.write(f"\n# Batch {bn} - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

def run():
    names = load()
    if not names:
        print("nothing to do")
        return
    prox = getprox()
    if TOKEN:
        print(Fore.CYAN + "token loaded")
    if prox:
        ans = input(f"{len(prox)} proxies, use? [y/N]: ").strip().lower() == "y"
        if not ans:
            prox = []
    total = len(names)
    sem = asyncio.Semaphore(CONCURRENT)

    async def go():
        conn = aiohttp.TCPConnector(limit=0)
        timeout = aiohttp.ClientTimeout(total=TIMEOUT + 5)
        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as sess:
            tasks = [check(sess, u, TOKEN, sem, prox, 0) for u in names]
            avail = []
            taken = 0
            unk = []
            done = 0
            start = time.monotonic()
            retry = []
            hdr = False
            bn = nextbatch()
            try:
                for coro in asyncio.as_completed(tasks):
                    name, res, method = await coro
                    done += 1
                    if res is True:
                        if not hdr:
                            batchhdr(OUTPUT, bn)
                            hdr = True
                        avail.append(name)
                        writeavail(name, method, bn, OUTPUT)
                    elif res is False:
                        taken += 1
                    else:
                        if method == "fail":
                            retry.append(name)
                        unk.append((name, method))
                    progress(done, total, avail, taken, unk, start)

                if retry:
                    print(Fore.YELLOW + f"\n  retry {len(retry)}")
                    tasks2 = [check(sess, u, TOKEN, sem, prox, 1.0) for u in retry]
                    retry = []
                    for coro in asyncio.as_completed(tasks2):
                        name, res, method = await coro
                        done += 1
                        if res is True:
                            avail.append(name)
                            writeavail(name, method, bn, OUTPUT)
                        elif res is False:
                            taken += 1
                        else:
                            unk.append((name, method))
                        progress(done, total, avail, taken, unk, start)
            except KeyboardInterrupt:
                pass
            el = time.monotonic() - start
            print(
                f"\n  {Fore.CYAN}done {done} in {el:.0f}s ({done/el:.1f}/s)  "
                f"{Fore.GREEN}{len(avail)} avail  {Fore.RED}{taken} taken  "
                f"{Fore.YELLOW}{len(unk)} unk{Style.RESET_ALL}"
            )
            if unk:
                print(Fore.YELLOW + "  unknowns:")
                for u, m in unk:
                    print(f"    {Fore.RED}{u} ({m})")

    asyncio.run(go())

print(Fore.CYAN + "github username checker")
print()
run()
