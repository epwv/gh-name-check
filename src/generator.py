import asyncio
import json
import random
import sys
from pathlib import Path
import aiohttp
from colorama import init, Fore, Style

init(autoreset=True)

DIR = Path(__file__).parent.parent
CFG_PATH = DIR / "config" / "config.json"

def setup():
    print(Fore.CYAN + "\n── first time setup ──\n")
    token = input("github token (optional, press enter to skip): ").strip()
    proxies = input("path to proxy file (optional, press enter for default proxies.txt): ").strip()
    delay = input("delay between requests in seconds (default 0.5): ").strip()
    try:
        delay = float(delay) if delay else 0.5
        if delay < 0:
            delay = 0.5
    except:
        delay = 0.5
    cfg = {
        "token": token,
        "delay": delay,
        "proxies": proxies,
    }
    CFG_PATH.write_text(json.dumps(cfg, indent=2))
    print(Fore.GREEN + "config.json saved. rerun the script.\n")
    sys.exit(0)

if not CFG_PATH.exists():
    setup()

cfg = json.loads(CFG_PATH.read_text())
TOKEN = cfg.get("token", "")
DELAY = cfg.get("delay", 0.5)

CH = "abcdefghijklmnopqrstuvwxyz0123456789"
SIGNUP = "https://github.com/signup_check_new/username"

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/604.1",
]

seen = set()
found = 0
checked = 0

def gen(n):
    while True:
        u = "".join(random.choices(CH, k=n))
        if u not in seen:
            seen.add(u)
            return u

async def chk(sess, name):
    ua = random.choice(UAS)
    try:
        async with sess.get(
            SIGNUP,
            params={"suggest_usernames": "true", "value": name},
            headers={"User-Agent": ua},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            if r.status == 200:
                return True
            if r.status == 422:
                return False
            if r.status in (429, 403):
                return "limit"
            return None
    except:
        return None

async def api(sess, name):
    ua = random.choice(UAS)
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": ua,
    }
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
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
    except:
        return None

async def work(n, out):
    global found, checked
    async with aiohttp.ClientSession() as sess:
        while True:
            name = gen(n)
            r = await chk(sess, name)
            if r is None:
                r = await api(sess, name)
            if r == "limit":
                await asyncio.sleep(10)
                r = await chk(sess, name)
                if r is None:
                    r = await api(sess, name)
            checked += 1
            if r is True:
                found += 1
                with open(out, "a") as f:
                    f.write(name + "\n")
                sys.stdout.write(
                    f"{Fore.GREEN}{name}  ({found} found, {checked} checked){Style.RESET_ALL}\n"
                )
            elif r is False:
                sys.stdout.write(
                    f"{Fore.RED}{name}  ({found} found, {checked} checked){Style.RESET_ALL}\n"
                )
            else:
                sys.stdout.write(
                    f"{Fore.YELLOW}{name}  ({found} found, {checked} checked){Style.RESET_ALL}\n"
                )
            sys.stdout.flush()
            await asyncio.sleep(DELAY)

async def main():
    global DELAY, TOKEN, found, checked
    while True:
        print(Fore.CYAN + "\ngithub username generator")
        print("  3  three-letter")
        print("  4  four-letter")
        print("  b  both")
        print(f"  a  adjust delay (current: {DELAY}s)")
        print("  q  quit")
        c = input("  [3/4/b/a/q]: ").strip().lower()

        if c == "q":
            break
        if c == "a":
            try:
                val = float(input("  delay in seconds: ").strip())
                if val < 0:
                    val = 0.5
                cfg["delay"] = val
                DELAY = val
                CFG_PATH.write_text(json.dumps(cfg, indent=2))
                print(Fore.GREEN + f"  delay set to {val}s")
            except:
                print(Fore.RED + "  invalid")
            continue
        if c not in ("3", "4", "b"):
            print(Fore.RED + "  invalid")
            continue

        t3 = DIR / "lists" / "3_letter_usernames.txt"
        t4 = DIR / "lists" / "4_letter_usernames.txt"
        (DIR / "lists").mkdir(exist_ok=True)
        found = 0
        checked = 0

        if c == "b":
            print(f"  3 -> {t3}\n  4 -> {t4}\n")
            t3.touch(exist_ok=True)
            t4.touch(exist_ok=True)
            ws = [
                asyncio.create_task(work(3, t3)),
                asyncio.create_task(work(4, t4)),
            ]
        elif c == "4":
            print(f"  4 -> {t4}\n")
            t4.touch(exist_ok=True)
            ws = [asyncio.create_task(work(4, t4))]
        else:
            print(f"  3 -> {t3}\n")
            t3.touch(exist_ok=True)
            ws = [asyncio.create_task(work(3, t3))]

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
