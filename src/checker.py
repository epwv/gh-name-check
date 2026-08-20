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

baseDir = Path(__file__).parent.parent
cfgPath = baseDir / "config" / "config.json"

def setup():
    print(Fore.CYAN + "\nfirst time setup")
    token = input("token (optional): ").strip()
    proxyPath = input("proxy file (optional): ").strip()
    delay = input("delay in seconds (default 0.5): ").strip()
    try:
        delay = float(delay) if delay else 0.5
    except ValueError:
        delay = 0.5
    if delay < 0:
        delay = 0.5
    cfg = {"token": token, "delay": delay, "proxies": proxyPath}
    cfgPath.parent.mkdir(parents=True, exist_ok=True)
    cfgPath.write_text(json.dumps(cfg, indent=2))
    print(Fore.GREEN + "saved. rerun the script.")
    sys.exit(0)

if not cfgPath.exists():
    setup()

cfg = json.loads(cfgPath.read_text())
token = cfg.get("token", "") or os.environ.get("GITHUB_TOKEN", "")

listDir = baseDir / "lists"
confirmedDir = baseDir / "confirmed"
listDir.mkdir(exist_ok=True)
confirmedDir.mkdir(exist_ok=True)

inputFiles = [
    listDir / "3_letter_usernames.txt",
    listDir / "4_letter_usernames.txt",
]
outputFile = confirmedDir / "available_confirmed.txt"

for f in inputFiles:
    f.touch(exist_ok=True)
outputFile.touch(exist_ok=True)

proxyPath = cfg.get("proxies", "")
proxyFile = Path(proxyPath).expanduser() if proxyPath else baseDir / "proxies.txt"

signupUrl = "https://github.com/signup_check_new/username"
hiddenCharsRe = re.compile(r"[\u00ad\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff\u00a0]")
concurrentLimit = 50
concurrentLimitNoProxy = 10
limitRetries = 3
requestTimeout = 15
userAgents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; rv:121.0) Gecko/20100101 Firefox/121.0",
]

def clean(s):
    return hiddenCharsRe.sub("", s).strip()

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
    for f in inputFiles:
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
    for l in outputFile.read_text().splitlines():
        l = l.strip()
        if l and not l.startswith("#"):
            done.add(clean(l))
    if done:
        before = len(good)
        good = [u for u in good if u not in done]
        print(f"{before - len(good)} already confirmed")
    return good

def getProxies():
    if not proxyFile.exists():
        return []
    raw = proxyFile.read_text().strip()
    return [l.strip() for l in raw.splitlines() if l.strip()]

def nextBatch():
    num = 0
    for l in outputFile.read_text().splitlines():
        m = re.match(r"# Batch (\d+)", l)
        if m:
            n = int(m.group(1))
            if n > num:
                num = n
    return num + 1

async def checkSignup(sess, name, sem, proxy=None):
    async with sem:
        k = {
            "params": {"suggest_usernames": "true", "value": name},
            "headers": {"User-Agent": random.choice(userAgents)},
            "timeout": aiohttp.ClientTimeout(total=requestTimeout),
        }
        if proxy:
            k["proxy"] = proxy
        try:
            async with sess.get(signupUrl, **k) as r:
                if r.status == 200:
                    return True
                if r.status == 422:
                    return False
                if r.status in (429, 403):
                    return "limit"
                return None
        except Exception:
            return None

async def checkApi(sess, name, sem, token, proxy=None):
    async with sem:
        h = {"User-Agent": random.choice(userAgents)}
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
        except Exception:
            return None

async def checkUsername(sess, name, token, sem, proxies, delay):
    await asyncio.sleep(delay)
    p = random.choice(proxies) if proxies else None
    if token:
        r = await checkApi(sess, name, sem, token, p)
        if r is not None and r != "limit":
            return name, r, "api"
    backoff = 5
    for attempt in range(limitRetries):
        r = await checkSignup(sess, name, sem, p)
        if r is not None and r != "limit":
            return name, r, "signup"
        if r != "limit":
            break
        if attempt < limitRetries - 1:
            await asyncio.sleep(backoff)
            backoff *= 2
    return name, None, "fail"

def printProgress(done, total, avail, taken, unk, start):
    el = time.monotonic() - start
    rps = done / el if el > 0 else 0
    eta = f"{(total - done) / rps:.0f}s" if rps > 0 else "?"
    sys.stdout.write(
        f"\r  {Fore.CYAN}{done}/{total}  {rps:.1f}/s  "
        f"{Fore.GREEN}{len(avail)} avail  {Fore.RED}{taken} taken  "
        f"{Fore.YELLOW}{len(unk)} unk  {Fore.CYAN}eta {eta}{Style.RESET_ALL}   "
    )
    sys.stdout.flush()

def writeAvailable(name, method, output):
    print(Fore.GREEN + f"\n  {name} ({method})")
    with open(output, "a") as f:
        f.write(name + "\n")

def writeBatchHeader(output, bn):
    with open(output, "a") as f:
        f.write(f"\n# Batch {bn} - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

def run():
    names = load()
    if not names:
        print(Fore.YELLOW + "nothing to do")
        return
    proxies = getProxies()
    if token:
        print(Fore.CYAN + "token loaded")
    if proxies:
        ans = input(f"{len(proxies)} proxies, use? [y/N]: ").strip().lower() == "y"
        if not ans:
            proxies = []
    total = len(names)
    sem = asyncio.Semaphore(concurrentLimit if proxies else concurrentLimitNoProxy)

    async def go():
        conn = aiohttp.TCPConnector(limit=0)
        timeout = aiohttp.ClientTimeout(total=requestTimeout + 5)
        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as sess:
            tasks = [checkUsername(sess, u, token, sem, proxies, 0) for u in names]
            avail = []
            taken = 0
            unk = []
            done = 0
            start = time.monotonic()
            retry = []
            hdr = False
            bn = nextBatch()
            try:
                for coro in asyncio.as_completed(tasks):
                    name, res, method = await coro
                    done += 1
                    if res is True:
                        if not hdr:
                            writeBatchHeader(outputFile, bn)
                            hdr = True
                        avail.append(name)
                        writeAvailable(name, method, outputFile)
                    elif res is False:
                        taken += 1
                    else:
                        if method == "fail":
                            retry.append(name)
                        unk.append((name, method))
                    printProgress(done, total, avail, taken, unk, start)

                if retry:
                    print(Fore.YELLOW + f"\n  retry {len(retry)}")
                    tasks2 = [checkUsername(sess, u, token, sem, proxies, 1.0) for u in retry]
                    retry = []
                    for coro in asyncio.as_completed(tasks2):
                        name, res, method = await coro
                        done += 1
                        if res is True:
                            avail.append(name)
                            writeAvailable(name, method, outputFile)
                        elif res is False:
                            taken += 1
                        else:
                            unk.append((name, method))
                        printProgress(done, total, avail, taken, unk, start)
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
