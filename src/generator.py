import asyncio
import json
import random
import sys
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
delay = cfg.get("delay", 0.5)

listDir = baseDir / "lists"
threeLetterFile = listDir / "3_letter_usernames.txt"
fourLetterFile = listDir / "4_letter_usernames.txt"
charset = "abcdefghijklmnopqrstuvwxyz0123456789"
signupUrl = "https://github.com/signup_check_new/username"
limitRetries = 3

userAgents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/604.1",
]

seen = set()
found = 0
checked = 0

def genName(n):
    while True:
        u = "".join(random.choices(charset, k=n))
        if u not in seen:
            seen.add(u)
            return u

async def checkSignup(sess, name):
    try:
        async with sess.get(
            signupUrl,
            params={"suggest_usernames": "true", "value": name},
            headers={"User-Agent": random.choice(userAgents)},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status == 200:
                return True
            if r.status == 422:
                return False
            if r.status in (429, 403):
                return "limit"
            return None
    except Exception:
        return None

async def checkApi(sess, name, token):
    h = {"User-Agent": random.choice(userAgents)}
    if token:
        h["Authorization"] = f"Bearer {token}"
    try:
        async with sess.get(
            f"https://api.github.com/users/{name}",
            headers=h,
            timeout=aiohttp.ClientTimeout(total=10),
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

def statusColor(r):
    if r is True:
        return Fore.GREEN
    if r is False:
        return Fore.RED
    return Fore.YELLOW

async def work(n, out, token):
    global found, checked
    async with aiohttp.ClientSession() as sess:
        while True:
            name = genName(n)
            r = await checkSignup(sess, name)
            if r is None:
                r = await checkApi(sess, name, token)
            backoff = 10
            for attempt in range(limitRetries):
                if r != "limit":
                    break
                await asyncio.sleep(backoff)
                r = await checkSignup(sess, name)
                if r is None:
                    r = await checkApi(sess, name, token)
                backoff *= 2
            checked += 1
            if r is True:
                found += 1
                with open(out, "a") as f:
                    f.write(name + "\n")
            sys.stdout.write(
                f"{statusColor(r)}{name}"
                f"  ({found} found, {checked} checked){Style.RESET_ALL}\n"
            )
            sys.stdout.flush()
            await asyncio.sleep(delay)

async def main():
    global delay, found, checked
    while True:
        print(Fore.CYAN + "\ngithub username generator")
        print("  3  three-letter")
        print("  4  four-letter")
        print("  b  both")
        print(f"  a  adjust delay (current: {delay}s)")
        print("  q  quit")
        c = input("  [3/4/b/a/q]: ").strip().lower()

        if c == "q":
            break
        if c == "a":
            try:
                val = float(input("  delay: ").strip())
                if val < 0:
                    val = 0.5
                cfg["delay"] = val
                delay = val
                cfgPath.write_text(json.dumps(cfg, indent=2))
                print(Fore.GREEN + f"  delay set to {val}s")
            except ValueError:
                print(Fore.RED + "  invalid delay value")
            continue
        if c not in ("3", "4", "b"):
            print(Fore.RED + "  invalid option")
            continue

        listDir.mkdir(exist_ok=True)
        found = 0
        checked = 0
        token = cfg.get("token", "")

        if c == "b":
            threeLetterFile.touch(exist_ok=True)
            fourLetterFile.touch(exist_ok=True)
            print(f"  3 -> {threeLetterFile}\n  4 -> {fourLetterFile}\n")
            ws = [
                asyncio.create_task(work(3, threeLetterFile, token)),
                asyncio.create_task(work(4, fourLetterFile, token)),
            ]
        elif c == "4":
            fourLetterFile.touch(exist_ok=True)
            print(f"  4 -> {fourLetterFile}\n")
            ws = [asyncio.create_task(work(4, fourLetterFile, token))]
        else:
            threeLetterFile.touch(exist_ok=True)
            print(f"  3 -> {threeLetterFile}\n")
            ws = [asyncio.create_task(work(3, threeLetterFile, token))]

        try:
            await asyncio.gather(*ws)
        except KeyboardInterrupt:
            for w in ws:
                w.cancel()
            await asyncio.wait(ws)
        print(Fore.CYAN + f"\nstopped  {found} found, {checked} checked")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
