import requests
import hashlib
import time
import random
import string
import json
import os
import struct
import qrcode
import sqlite3
import re
import urllib.parse
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class C:
    G = "\033[92m"
    R = "\033[91m"
    Y = "\033[93m"
    B = "\033[94m"
    M = "\033[95m"
    C = "\033[96m"
    W = "\033[97m"
    BOLD = "\033[1m"
    END = "\033[0m"

SCRIPT_NAME = "JUSTINE POGI"
BASE_URL = "https://io.playgame.zone"
SECRET_SIGN = "p&YCK^Ko0$!"
SECRET_KEY = "!1ha6N?4he5HaZb"

CAPSOLVER_KEY = "CAP-EEF0EEC7BD1344A55F7E7A7246BF213EF287D70F672B338158E68BAA28D15040"
SITE_KEY = "0x4AAAAAABvE6wH9brzCpDfh"
WITHDRAW_SITE_KEY = "0x4AAAAAABvE6lIyPtYqmihP"
WITHDRAW_PAGE = "https://vertical-activity.ptgaming.ph/turnstile.html?siteKey=0x4AAAAAABvE6lIyPtYqmihP&appearance=always&isNative=0&os=web"
PAGE_URL = "https://www.ptgaming.ph/"
FARM_URL = "http://localhost:7714/token"

ACCOUNTS_FILE = "accounts.txt"
DEPOT_FILE = "depo.txt"
TOKENS_FILE = "tokens.txt"
QR_FOLDER = "qr_images"
LOG_FILE = "justine_pogi.log"
CONFIG_FILE = "config.json"
PROXIES_FILE = "proxies.txt"
SESSIONS_DIR = "sessions"
CYPHER_DB = r"C:\Users\tekte\AppData\Local\CYPHER~1\phone_data.db"
RETOKEN_FILE = "retoken.txt"
INVITE_FILE = "invite.txt"

DEFAULT_CONFIG = {
    "delay_min": 2,
    "delay_max": 5,
    "max_retry": 3,
    "deposit_amount": 130,
    "activity_id": "280222680316235781",
    "third_game_id": "404",
}

def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] [{SCRIPT_NAME}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()

def is_invalid(val) -> bool:
    return val is None or val is False or val in ("", "null", "undefined", "false", "NaN")

def generate_sign_str(params: dict) -> str:
    def n(val):
        if is_invalid(val):
            return ""
        if not isinstance(val, (dict, list)):
            return str(val)
        if isinstance(val, list):
            return "||".join(n(x) for x in val if not is_invalid(x))
        parts = []
        for k in sorted(val.keys()):
            r = val[k]
            if is_invalid(r):
                continue
            s = n(r)
            if s:
                parts.append(s)
        return "||".join(parts)
    return n(params)

def make_sign(params: dict) -> str:
    return md5(generate_sign_str(params) + "||" + SECRET_SIGN + SECRET_KEY)

def generate_device_id(length=11) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

def generate_password(length=10) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

def normalize_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "").replace("+", "")
    if phone.startswith("63") and len(phone) >= 12:
        phone = "0" + phone[2:]
    if phone.startswith("9") and len(phone) == 10:
        phone = "0" + phone
    return phone

def phone_key(phone: str) -> str:
    """Canonical key for matching: always without leading 0."""
    p = normalize_phone(phone)
    return p[1:] if p.startswith("0") else p

def phone_no_zero(phone: str) -> str:
    return phone_key(phone)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def load_proxy():
    if not os.path.exists(PROXIES_FILE):
        return None
    with open(PROXIES_FILE, "r", encoding="utf-8") as f:
        lines = [x.strip() for x in f if x.strip() and not x.startswith("#")]
    if not lines:
        return None
    proxy = lines[0]
    if not proxy.startswith("http"):
        proxy = "http://" + proxy
    return {"http": proxy, "https": proxy}

def random_delay(cfg):
    time.sleep(random.uniform(cfg.get("delay_min", 2), cfg.get("delay_max", 5)))

def make_session(proxy=None):
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Origin": "https://www.ptgaming.ph",
        "Referer": "https://www.ptgaming.ph/",
    })
    if proxy:
        s.proxies.update(proxy)
    return s

def post_signed(session, path, body, extra_headers=None, max_retry=3):
    for attempt in range(1, max_retry + 1):
        ts = str(int(time.time()))
        terminal = "128"
        sign_params = dict(body)
        sign_params["terminal"] = terminal
        sign_params["ts"] = ts
        sign = make_sign(sign_params)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "ts": ts,
            "sign": sign,
            "terminal": terminal,
            "client-version": "2.10.3",
        }
        if extra_headers:
            headers.update(extra_headers)
        try:
            r = session.post(BASE_URL + path, data=body, headers=headers, timeout=20)
            return r
        except Exception:
            if attempt < max_retry:
                time.sleep(2)
    return None

def post_json(session, path, body, token, suid, device_id):
    headers = {
        "Content-Type": "application/json",
        "token": token,
        "dudd": device_id,
        "suid": suid,
        "terminal": "128",
        "client-version": "2.10.3",
    }
    return session.post(BASE_URL + path, json=body, headers=headers, timeout=15)

def capsolver_proxy_fields():
    proxy = load_proxy()
    if not proxy:
        return None
    parsed = urllib.parse.urlparse(proxy.get("http") or "")
    if not parsed.hostname or not parsed.port:
        return None
    fields = {
        "proxyType": "http",
        "proxyAddress": parsed.hostname,
        "proxyPort": parsed.port,
    }
    if parsed.username:
        fields["proxyLogin"] = urllib.parse.unquote(parsed.username)
    if parsed.password:
        fields["proxyPassword"] = urllib.parse.unquote(parsed.password)
    return fields

def get_cf_token_capsolver(site_key=None, page_url=None, use_proxy=False):
    site_key = site_key or SITE_KEY
    page_url = page_url or PAGE_URL
    task = {
        "type": "AntiTurnstileTaskProxyLess",
        "websiteURL": page_url,
        "websiteKey": site_key,
    }
    if use_proxy:
        fields = capsolver_proxy_fields()
        if fields:
            task = {
                "type": "AntiTurnstileTask",
                "websiteURL": page_url,
                "websiteKey": site_key,
            }
            task.update(fields)
    try:
        r = requests.post("https://api.capsolver.com/createTask", json={
            "clientKey": CAPSOLVER_KEY,
            "task": task,
        }, timeout=30)
        data = r.json()
        if data.get("errorId") != 0:
            print(f"  CapSolver error: {data.get('errorDescription')}")
            return None
        task_id = data["taskId"]
        for _ in range(30):
            time.sleep(2)
            r2 = requests.post("https://api.capsolver.com/getTaskResult", json={
                "clientKey": CAPSOLVER_KEY,
                "taskId": task_id,
            }, timeout=30)
            res = r2.json()
            if res.get("status") == "ready":
                print(f"  {C.G}CapSolver token{C.END}")
                return res["solution"]["token"]
            if res.get("errorId") != 0:
                print(f"  CapSolver failed: {res.get('errorDescription')}")
                return None
        print("  CapSolver timeout")
    except Exception as e:
        print(f"  CapSolver exception: {e}")
    return None

def get_cf_token(site_key=None, page_url=None):
    site_key = site_key or SITE_KEY
    page_url = page_url or PAGE_URL
    return get_cf_token_capsolver(site_key, page_url)

def get_bind_tokens():
    print("  CapSolver bind tokens...", flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        withdraw_job = pool.submit(get_cf_token_capsolver, WITHDRAW_SITE_KEY, PAGE_URL)
        main_job = pool.submit(get_cf_token_capsolver, SITE_KEY, PAGE_URL)
        return withdraw_job.result(), main_job.result()

def save_account(phone, password, token, user_id, device_id):
    line = f"{phone}|{password}|{token}|{user_id}|{device_id}|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    with open(ACCOUNTS_FILE, "a", encoding="utf-8") as f:
        f.write(line)

def save_token(phone, password, token, user_id, device_id):
    line = f"{phone}:{password}|{token}|{user_id}|{device_id}|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    with open(TOKENS_FILE, "a", encoding="utf-8") as f:
        f.write(line)

def save_session(phone, session, token, suid, device_id):
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    data = {
        "token": token,
        "suid": suid,
        "device_id": device_id,
        "cookies": requests.utils.dict_from_cookiejar(session.cookies),
    }
    path = os.path.join(SESSIONS_DIR, f"{phone}.json")
    with open(path, "w") as f:
        json.dump(data, f)

def load_session(phone):
    path = os.path.join(SESSIONS_DIR, f"{phone}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None

def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    accounts = []
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) >= 2:
                accounts.append({
                    "phone": parts[0],
                    "password": parts[1],
                    "token": parts[2] if len(parts) > 2 else "",
                    "user_id": parts[3] if len(parts) > 3 else "",
                    "device_id": parts[4] if len(parts) > 4 else generate_device_id(),
                })
    return accounts

def load_invite_accounts():
    if not os.path.exists(INVITE_FILE):
        return []
    accounts = []
    with open(INVITE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) >= 2:
                accounts.append({
                    "phone": parts[0],
                    "password": parts[1],
                    "token": parts[2] if len(parts) > 2 else "",
                    "device_id": parts[4] if len(parts) > 4 else generate_device_id(),
                })
    return accounts

def add_to_retoken(phone):
    phone = normalize_phone(phone)
    existing = set()
    if os.path.exists(RETOKEN_FILE):
        with open(RETOKEN_FILE, "r", encoding="utf-8") as f:
            existing = {normalize_phone(l.split("|")[0].split(":")[0].strip()) for l in f if l.strip()}
    if phone not in existing:
        with open(RETOKEN_FILE, "a", encoding="utf-8") as f:
            f.write(phone + "\n")
        print(f"  {C.Y}Added {phone} to retoken.txt{C.END}")

def remove_expired_from_accounts(phone):
    phone = normalize_phone(phone)
    if not os.path.exists(ACCOUNTS_FILE):
        return
    lines = []
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() and normalize_phone(line.split("|")[0]) != phone:
                lines.append(line)
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"  {C.Y}Removed expired token for {phone} from accounts.txt{C.END}")

def get_latest_otp(phone, after_timestamp=None, exclude_otp=None, max_age_seconds=45, wait_seconds=40):
    phone_short = phone.lstrip("0")
    start = time.time()
    seen = set()
    if exclude_otp:
        seen.add(exclude_otp)
    while time.time() - start < wait_seconds:
        try:
            conn = sqlite3.connect(CYPHER_DB)
            c = conn.cursor()
            c.execute("""
                SELECT body, timestamp_ms FROM messages
                WHERE (phone LIKE ? OR phone LIKE ?)
                AND body LIKE '%Verification Code%'
                ORDER BY timestamp_ms DESC LIMIT 5
            """, (f"%{phone_short}%", f"%0{phone_short}%"))
            rows = c.fetchall()
            conn.close()
            for body, ts in rows:
                if after_timestamp and ts < after_timestamp:
                    continue
                age = (time.time() * 1000 - ts) / 1000
                if age > max_age_seconds:
                    continue
                m = re.search(r"Verification Code:\s*(\d{4,8})", body)
                if m:
                    otp = m.group(1)
                    if otp not in seen:
                        print(f"  {C.G}Found OTP: {otp} (age {age:.1f}s){C.END}")
                        return otp
                    seen.add(otp)
        except Exception as e:
            print(f"  OTP read error: {e}")
        time.sleep(2)
    print(f"  {C.R}OTP timeout{C.END}")
    return None

def get_cypherlink_phones():
    try:
        conn = sqlite3.connect(CYPHER_DB)
        c = conn.cursor()
        c.execute("SELECT phone FROM phones WHERE phone NOT LIKE 'No SIM' AND phone != '' AND (status IS NULL OR status != 'Success')")
        phones = [r[0] for r in c.fetchall() if r[0]]
        conn.close()
        return phones
    except Exception:
        return []

def mark_cypherlink_status(phone, status="Success"):
    try:
        conn = sqlite3.connect(CYPHER_DB)
        c = conn.cursor()
        phone_short = phone.lstrip("0")
        c.execute("""
            UPDATE phones SET status = ?, status_ts = ?, updated_at = ?
            WHERE phone LIKE ?
        """, (status, int(time.time() * 1000), int(time.time() * 1000), f"%{phone_short}%"))
        conn.commit()
        conn.close()
    except Exception:
        pass

def claim_new_account_bonus(session, token, suid, device_id):
    body = {"task_type": None, "task_id": None, "bonus_id": None, "update_type": 94, "token": token}
    headers = {
        "Content-Type": "application/json",
        "token": token,
        "dudd": device_id,
        "suid": suid,
        "terminal": "128",
        "client-version": "2.10.3",
    }
    try:
        r = session.post(f"{BASE_URL}/api/task/claim", json=body, headers=headers, timeout=15)
        if r.json().get("code") == 200:
            print(f"  {C.G}20 bonus claimed{C.END}")
    except Exception:
        pass

def register_one(session, phone, password, device_id, shared_cf_token=None):
    print(f"  {C.C}Processing {phone}...{C.END}")
    phone = normalize_phone(phone)
    phone_short = phone_no_zero(phone)

    print(f"  {C.Y}Sending OTP to {phone}...{C.END}")
    body1 = {
        "phone": phone,
        "type": "2",
        "appPackageName": "com.playmate.playzone",
        "telephoneCode": "+63",
        "deviceId": device_id,
    }
    extra = {"dudd": device_id, "cf-scene": "COMMON_MANAGED"}
    r1 = post_signed(session, "/api/v2/sms/send/short/msg", body1, extra)
    try:
        data = r1.json()
        print(f"  Send OTP response: {data}")
        if data.get("code") == 1 and "limit" in str(data.get("msg", "")).lower():
            print(f"  {C.R}Rate limited, skipping{C.END}")
            return False
        if data.get("code") != 200:
            print(f"  {C.R}Send OTP failed: {data.get('msg')}{C.END}")
            return False
    except Exception as e:
        print(f"  {C.R}Send OTP error: {e}{C.END}")
        return False

    print(f"  {C.Y}Waiting for OTP...{C.END}")
    send_time = int(time.time() * 1000)
    otp1 = get_latest_otp(phone, after_timestamp=send_time - 2000, max_age_seconds=30, wait_seconds=45)
    if not otp1:
        otp1 = input(f"  {C.Y}>>> Enter FIRST OTP for {phone}: {C.END}").strip()
    if not otp1:
        return False
    print(f"  {C.G}Using OTP1 for {phone}: {otp1}{C.END}")

    print(f"  {C.Y}Registering account...{C.END}")
    body2 = {
        "appChannel": "h5",
        "appPackageName": "com.playmate.playzone",
        "deviceId": device_id,
        "deviceModel": "WEB",
        "deviceVersion": "WEB",
        "appVersion": "2.10.3",
        "sysTimezone": "null",
        "sysLanguage": "null",
        "source": "4",
        "isNative": "0",
        "telephoneCode": "+63",
        "registration_channel": "H5",
        "phone": phone,
        "verifyCode": otp1,
        "referral_code": "",
        "type": "2",
        "cf-scene": "COMMON_INVISABLE",
    }
    extra2 = {"dudd": device_id, "cf-scene": "COMMON_INVISABLE"}
    r2 = post_signed(session, "/api/v2/player/sign-in", body2, extra2)

    token = suid = None
    user_id = None
    try:
        data = r2.json()
        if data.get("code") == 200:
            token = data["data"]["token"]
            suid = data["data"]["user_info"].get("suid", "")
            user_id = data["data"]["user_info"]["user_id"]
            claim_new_account_bonus(session, token, suid, device_id)
        else:
            print(f"  {C.R}Register failed: {data.get('msg')}{C.END}")
            return False
    except Exception as e:
        print(f"  {C.R}Register error: {e}{C.END}")
        return False

    print(f"  {C.Y}Sending second OTP...{C.END}")
    body3 = {
        "phone": phone_short,
        "telephoneCode": "+63",
        "type": "22",
        "deviceId": device_id,
        "token": token,
    }
    extra3 = {"dudd": device_id, "suid": suid}
    send_time2 = int(time.time() * 1000)
    post_signed(session, "/api/v2/sms/send/short/msg", body3, extra3)

    print(f"  {C.Y}Waiting for second OTP for {phone}...{C.END}")
    otp2 = get_latest_otp(phone, after_timestamp=send_time2 - 2000, exclude_otp=otp1, max_age_seconds=30, wait_seconds=45)
    if not otp2:
        otp2 = input(f"  {C.Y}>>> Enter SECOND OTP for {phone}: {C.END}").strip()
    if not otp2:
        return False
    print(f"  {C.G}Using OTP2 for {phone}: {otp2}{C.END}")

    print(f"  {C.Y}Verifying second OTP...{C.END}")
    body4 = {
        "token": token,
        "phone": phone_short,
        "telephoneCode": "+63",
        "code": otp2,
        "type": "22",
    }
    r4 = post_signed(session, "/api/v2/sms/verify/short/msg/code", body4, {"dudd": device_id, "suid": suid})
    try:
        print(f"  Verify response: {r4.json()}")
    except Exception:
        print(f"  Verify raw: {r4.text[:200] if r4 else 'No response'}")

    print(f"  {C.Y}Getting cf-token...{C.END}")
    cf_token = shared_cf_token or get_cf_token()

    print(f"  {C.Y}Setting password...{C.END}")
    hashed_pw = md5(password)
    body5 = {
        "token": token,
        "phone": phone_short,
        "telephone_code": "+63",
        "upd_column": "password",
        "password": hashed_pw,
        "type": "22",
        "code": otp2,
    }
    extra5 = {"dudd": device_id, "suid": suid}
    if cf_token:
        extra5["cf-token"] = cf_token
        extra5["cf-scene"] = "COMMON_INVISABLE"
    print(f"  Set password payload: phone={phone_short}, type=22, code={otp2}")
    r5 = post_signed(session, "/api/v2/set/phone/passwd", body5, extra5)
    try:
        data5 = r5.json()
        print(f"  Set password response: {data5}")
        if data5.get("code") == 200:
            print(f"  {C.G}Account ready{C.END}")
            save_account(phone, password, token, user_id, device_id)
            save_session(phone, session, token, suid, device_id)
            mark_cypherlink_status(phone, "Success")
            return True
        print(f"  {C.R}Set password failed: {data5.get('msg')}{C.END}")
    except Exception as e:
        print(f"  {C.R}Set password error: {e}{C.END}")
    mark_cypherlink_status(phone, "Failed")
    return False

def login_with_security_check(session, phone, password, device_id, cfg, force_otp=False, existing_token=None, existing_suid=None):
    # Prefer saved token first
    if existing_token and not force_otp:
        # Quick validate by calling a light endpoint (balance or lobby)
        try:
            body = {"token": existing_token}
            extra = {"dudd": device_id, "suid": existing_suid or ""}
            r = post_signed(session, "/api/v2/jili/backhall", body, extra)
            if r and r.json().get("code") == 200:
                print(f"  {C.G}Using saved token for {phone}{C.END}")
                return existing_token, existing_suid or "", None
        except Exception:
            pass
        # Token dead, fall through to normal login

    hashed = md5(password)
    base_body = {
        "appChannel": "h5",
        "appPackageName": "com.playmate.playzone",
        "deviceId": device_id,
        "deviceModel": "WEB",
        "deviceVersion": "WEB",
        "appVersion": "2.10.3",
        "sysTimezone": "null",
        "sysLanguage": "null",
        "source": "4",
        "isNative": "0",
        "telephoneCode": "+63",
        "registration_channel": "H5",
        "phone": normalize_phone(phone),
        "cf-scene": "COMMON_INVISABLE",
    }
    extra = {"dudd": device_id, "cf-scene": "COMMON_INVISABLE"}

    body = dict(base_body)
    body["password"] = hashed
    r = post_signed(session, "/api/v2/player/sign-in", body, extra)

    try:
        data = r.json()
        code = data.get("code")

        if code == 200:
            token = data["data"]["token"]
            suid = data["data"]["user_info"].get("suid", "")
            uid = data["data"]["user_info"]["user_id"]
            save_account(phone, password, token, uid, device_id)
            save_token(phone, password, token, uid, device_id)
            save_session(phone, session, token, suid, device_id)
            return token, suid, uid

        if code in (102122, 102124) or force_otp:
            print(f"  {C.Y}OTP required for {phone}{C.END}")
            body_otp = {
                "phone": normalize_phone(phone),
                "telephoneCode": "+63",
                "type": "2",
                "deviceId": device_id,
                "appPackageName": "com.playmate.playzone",
            }
            send_time = int(time.time() * 1000)
            post_signed(session, "/api/v2/sms/send/short/msg", body_otp, {"dudd": device_id})
            otp = get_latest_otp(phone, after_timestamp=send_time - 3000, max_age_seconds=60, wait_seconds=40)
            if not otp:
                otp = input(f"{C.Y}>>> Enter OTP for {phone}: {C.END}").strip()
            if not otp:
                return None, None, None

            body_otp_login = dict(base_body)
            body_otp_login["verifyCode"] = otp
            body_otp_login["type"] = "2"
            body_otp_login["referral_code"] = ""

            r2 = post_signed(session, "/api/v2/player/sign-in", body_otp_login, extra)
            data2 = r2.json()
            if data2.get("code") == 200:
                token = data2["data"]["token"]
                suid = data2["data"]["user_info"].get("suid", "")
                uid = data2["data"]["user_info"]["user_id"]
                save_account(phone, password, token, uid, device_id)
                save_token(phone, password, token, uid, device_id)
                save_session(phone, session, token, suid, device_id)
                return token, suid, uid
            else:
                print(f"  {C.R}OTP login failed: {data2.get('msg')}{C.END}")
    except Exception as e:
        print(f"  Login error: {e}")
    return None, None, None

def deposit_and_save_qr(session, token, suid, device_id, amount, phone=None):
    body = {
        "token": token,
        "appPackageName": "com.playmate.playzone",
        "appVersion": "2.10.3",
        "amount": str(amount),
        "identifier": "mayaqrph",
        "config_id": "41",
        "amount_per": "10",
        "amount_num": str(amount // 10),
        "back_bonus": "50",
        "ratio_to_bonus": "1",
        "platform": "windows_1",
        "api_compat": "1",
    }
    extra = {"dudd": device_id, "suid": suid}
    print(f"  Deposit body token: {token[:20]}... suid: {suid[:15] if suid else 'empty'}")
    r = post_signed(session, "/api/v2/payment/balance-add", body, extra)
    try:
        print(f"  Deposit status: {r.status_code}")
        print(f"  Deposit raw: {r.text[:300]}")
        data = r.json()
        if data.get("code") == 200:
            qr = data["data"].get("qrcodeContent")
            order = data["data"].get("orderId", str(int(time.time())))
            if qr:
                os.makedirs(QR_FOLDER, exist_ok=True)
                path = f"{QR_FOLDER}/{order}.png"
                qrcode.make(qr).save(path)
                print(f"  {C.G}QR -> {path}{C.END}")
            else:
                print(f"  {C.Y}No qrcodeContent in response{C.END}")
            return data["data"]
        if data.get("code") == 400 and "Expired" in str(data.get("msg", "")):
            print(f"  {C.R}Token expired{C.END}")
            if phone:
                add_to_retoken(phone)
                remove_expired_from_accounts(phone)
        else:
            print(f"  {C.R}Deposit failed: {data.get('msg')}{C.END}")
    except Exception as e:
        print(f"  {C.R}Deposit error: {e}{C.END}")
    return None

def help_account(session, token, suid, device_id, share_token):
    body = {"token": token, "share_token": share_token}
    return post_json(session, "/bmp-treasure/v1/help", body, token, suid, device_id)

def check_chest_status(session, token, suid, device_id, activity_id, chest_level=1):
    """Return True if chest already claimed, False if claimable, None on error."""
    body = {"token": token, "helper_limit": 4, "leaderboard_limit": 10}
    r = post_json(session, "/bmp-treasure/v1/dashboard", body, token, suid, device_id)
    if r is None:
        return None
    try:
        data = r.json()
        if data.get("code") != 0:
            return None
        chests = (data.get("data") or {}).get("chest_list") or []
        for c in chests:
            if str(c.get("chest_level")) == str(chest_level):
                status = str(c.get("status") or c.get("claim_status") or "").lower()
                if "claimed" in status or status in ("2", "claimed", "done"):
                    return True
                progress = c.get("current_amount") or c.get("progress") or 0
                target = c.get("target_amount") or c.get("target") or 5000
                if int(progress) >= int(target):
                    return False  # full, claimable
                return False
        return False
    except Exception:
        return None
    body = {"token": token, "activity_id": activity_id, "chest_level": chest_level}
    return post_json(session, "/bmp-treasure/v1/claim", body, token, suid, device_id)

def list_cashback_ids(session, token, suid, device_id):
    """Fetch claimable cashback IDs from /api/v2/activity-cashback/fetch."""
    extra = {"dudd": device_id, "suid": suid}
    body = {"token": token}
    r = post_signed(session, "/api/v2/activity-cashback/fetch", body, extra)
    if r is None:
        return []
    try:
        data = r.json()
        if data.get("code") != 200:
            print(f"  {C.Y}fetch cashback code={data.get('code')} msg={data.get('msg')}{C.END}")
            return []
        items = data.get("data") or []
        candidates = []
        for it in items:
            if not isinstance(it, dict):
                continue
            cid = it.get("id")
            status = it.get("status")
            if cid is None:
                continue
            s = str(cid)
            # status 1 = claimable
            if status == 1 or status == "1":
                candidates.append(s)
                print(f"  {C.C}claimable id={s} cashback={it.get('cashback')} name={it.get('activity_name')}{C.END}")
        if not candidates:
            print(f"  {C.Y}no claimable cashback in fetch{C.END}")
        return candidates
    except Exception as e:
        print(f"  {C.R}fetch parse error: {e}{C.END}")
        return []


def claim_cashback(session, token, suid, device_id, cashback_id=None):
    extra = {"dudd": device_id, "suid": suid}

    discovered = list_cashback_ids(session, token, suid, device_id)
    ids_to_try = []
    for x in discovered:
        if x and str(x) not in ids_to_try:
            ids_to_try.append(str(x))
    # fallbacks only if nothing discovered
    if not ids_to_try and cashback_id:
        ids_to_try.append(str(cashback_id))

    last_fail = None
    for cid in ids_to_try:
        body = {"token": token, "activity_cashback_id": cid}
        r = post_signed(session, "/api/v2/activity-cashback/receive", body, extra)
        if r is None:
            last_fail = ("no response", None)
            continue
        try:
            data = r.json()
            code = data.get("code")
            if code == 200:
                amount = data.get("data", {}).get("cashback", 50)
                if amount is None:
                    amount = 50
                print(f"  {C.G}claimed cashback id={cid} amount={amount}{C.END}")
                return amount
            msg = data.get("msg") or data.get("message") or data
            last_fail = (code, msg)
            if code == 104002:
                continue
        except Exception as e:
            last_fail = (str(e), getattr(r, "text", "")[:200])
            continue

    if last_fail:
        print(f"  {C.Y}claim_cashback fail last code={last_fail[0]} msg={last_fail[1]}{C.END}")
    return None

def get_pp_wallet_balance(jsession):
    try:
        url = f"https://games.pragmaticplaylive.net/api/wallet/balance?JSESSIONID={urllib.parse.quote(jsession, safe='')}"
        r = requests.get(url, timeout=10, verify=False)
        data = r.json()
        return float(data.get("balance", 0))
    except Exception:
        return None

def get_balance(session, token, suid, device_id, phone=None):
    body = {"token": token}
    extra = {"dudd": device_id, "suid": suid}
    r = post_signed(session, "/api/v2/jili/backhall", body, extra)
    try:
        data = r.json()
        if data.get("code") == 200:
            coins = data.get("balance") or data.get("data", {}).get("balance", 0)
            pesos = coins / 100
            return f"{pesos:.2f} (coins: {coins})"
        if data.get("code") == 400 and "Expired" in str(data.get("msg", "")):
            print(f"  {C.R}Token expired{C.END}")
            if phone:
                add_to_retoken(phone)
                remove_expired_from_accounts(phone)
        else:
            print(f"  Balance response: {data}")
    except Exception as e:
        print(f"  Balance error: {e}")
    return None

def get_jsession_http(session, token, suid, device_id, game_id="404"):
    body = {"token": token, "third_game_id": str(game_id), "company_id": "10"}
    extra = {"dudd": device_id, "suid": suid, "CaType": "PragmaticPlay"}
    r = post_signed(session, "/api/v2/jili/login", body, extra)
    if not r:
        print(f"  {C.R}Game login request failed{C.END}")
        return None
    try:
        data = r.json()
    except Exception:
        print(f"  {C.R}Game login not JSON: {r.text[:200]}{C.END}")
        return None
    game_url = data.get("game_url") or ""
    if not game_url:
        print(f"  {C.R}No game_url{C.END}")
        return None

    browser = requests.Session()
    browser.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    })
    if session.proxies:
        browser.proxies.update(session.proxies)

    r1 = None
    for _try in range(3):
        try:
            r1 = browser.get(game_url, allow_redirects=True, timeout=25)
            break
        except Exception:
            time.sleep(1)
    if r1 is None:
        print(f"  {C.R}playGame failed{C.END}")
        return None
    html = r1.text or ""

    if "GameLaunch" not in html and "componentLaunchUrl" not in html:
        try:
            with open("debug_gameload.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  {C.Y}Saved debug_gameload.html (len={len(html)}){C.END}")
        except Exception:
            pass

    launch = None
    patterns = [
        r'componentLaunchUrl"\s*:\s*"(https:[^"\\]+)',
        r'componentLaunchUrl\\":\\"(https:[^"\\]+)',
        r'"componentLaunchUrl"\s*:\s*"(https:[^"]+)"',
        r"componentLaunchUrl['\"]?\s*[:=]\s*['\"]?(https:[^'\"\s]+)",
        r'(https://[^"\'\s]*GameLaunch[^"\'\s]*)',
        r'(https:\\/\\/[^"\'\s]*GameLaunch[^"\'\s]*)',
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            launch = m.group(1)
            break

    if not launch:
        m = re.search(r'(https[^"\'\s]*ppToken=[^"\'\s]+)', html)
        if m:
            launch = m.group(1)

    if not launch:
        snippet = html[:500].replace("\n", " ")
        print(f"  {C.R}GameLaunch not found. First 500: {snippet}{C.END}")
        return None

    launch = launch.replace("\\u0026", "&").replace("\\/", "/").replace("\\u003d", "=").replace("\\u003a", ":")

    r2 = None
    for _try in range(3):
        try:
            r2 = browser.get(launch, allow_redirects=False, timeout=25)
            break
        except Exception:
            time.sleep(1)
    if r2 is None:
        print(f"  {C.R}GameLaunch failed{C.END}")
        return None
    loc = r2.headers.get("Location") or r2.headers.get("location") or ""
    if not loc and r2.is_redirect:
        loc = r2.headers.get("location", "")
    js = re.search(r"JSESSIONID=([^&]+)", loc)
    table = re.search(r"table_id=([^&]+)", loc)
    ws = re.search(r"socket_server=([^&]+)", loc)
    if not js:
        print(f"  {C.R}No JSESSIONID. status={r2.status_code} loc={loc[:180]}{C.END}")
        return None
    jsession = urllib.parse.unquote(js.group(1))
    table_id = urllib.parse.unquote(table.group(1)) if table else "9j3eagurfwmml7z2"
    ws_base = urllib.parse.unquote(ws.group(1)) if ws else "wss://gs14.pragmaticplaylive.net/game"
    return {"jsession": jsession, "table_id": table_id, "ws": ws_base}

def get_pp_uid(jsession):
    url = f"https://games.pragmaticplaylive.net/api/config/preferences?JSESSIONID={urllib.parse.quote(jsession, safe='')}"
    try:
        r = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://client.pragmaticplaylive.net",
            "Referer": "https://client.pragmaticplaylive.net/",
        }, timeout=15)
        data = r.json()
        uid = data.get("userId") or data.get("user_id")
        nocomm = (data.get("params") or {}).get("isnocommission")
        if uid:
            return uid, nocomm
        print(f"  {C.Y}preferences no userId: {str(data)[:200]}{C.END}")
    except Exception as e:
        print(f"  {C.Y}preferences error: {e}{C.END}")
    return None, None

def wait_for_result(meta, timeout=90):
    try:
        import websocket
    except ImportError:
        return None
    jsession = meta["jsession"]
    table_id = meta["table_id"]
    ws_base = meta["ws"]
    token_enc = urllib.parse.quote(jsession, safe="")
    ws_url = f"{ws_base}?JSESSIONID={token_enc}&tableId={table_id}&type=json"
    headers = [
        "Origin: https://client.pragmaticplaylive.net",
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    ]
    try:
        ws = websocket.create_connection(ws_url, timeout=15, header=headers)
    except Exception as e:
        print(f"  {C.R}Result WS error: {e}{C.END}")
        return None
    print(f"  {C.Y}Waiting for round result...{C.END}")
    start = time.time()
    result = None
    while time.time() - start < timeout:
        try:
            ws.settimeout(5)
            msg = ws.recv()
        except Exception:
            continue
        if not isinstance(msg, str):
            continue
        if '"gameresult"' in msg:
            m = re.search(r'"result"\s*:\s*"(\w+)"', msg)
            if m:
                result = m.group(1).lower()
                print(f"  {C.G}Round result: {result}{C.END}")
                break
    ws.close()
    return result

def set_commission_mode(jsession):
    """Turn off No Commission so Banker is 0.95:1, not half-pay on 6."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://client.pragmaticplaylive.net",
        "Referer": "https://client.pragmaticplaylive.net/",
        "Content-Type": "application/json",
    }
    url = "https://games.pragmaticplaylive.net/api/ui/savePlayerConfigGeneric"
    try:
        r = requests.post(
            url,
            params={"JSESSIONID": jsession, "ck": str(int(time.time() * 1000))},
            json={"isnocommission": False},
            headers=headers,
            timeout=15,
            verify=False,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"  {C.R}No Commission toggle failed: {e}{C.END}")
        return False

def place_baccarat_bet(meta, amount, bet_type, phone):
    try:
        import websocket
    except ImportError:
        print(f"  {C.R}Install: pip install websocket-client{C.END}")
        return False
    jsession = meta["jsession"]
    table_id = meta["table_id"]
    ws_base = meta["ws"]
    set_commission_mode(jsession)
    u_id, nocomm = get_pp_uid(jsession)
    if not u_id:
        print(f"  {C.R}No uId, skip bet{C.END}")
        return False
    token_enc = urllib.parse.quote(jsession, safe="")
    ws_url = f"{ws_base}?JSESSIONID={token_enc}&tableId={table_id}&type=json"
    headers = [
        "Origin: https://client.pragmaticplaylive.net",
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
    ]
    try:
        ws = websocket.create_connection(ws_url, timeout=15, header=headers)
    except Exception as e:
        print(f"  {C.R}WS connect {phone}: {e}{C.END}")
        return False

    g_id = None
    timer_val = None
    told = False
    deadline = time.time() + 50
    while time.time() < deadline:
        try:
            ws.settimeout(5)
            msg = ws.recv()
        except Exception:
            continue
        if not isinstance(msg, str):
            continue
        if '"betsclosed"' in msg or '"gameresult"' in msg:
            g_id = None
            timer_val = None
            continue
        m_gid = re.search(r'"game"\s*:\s*\{[^}]*"id"\s*:\s*"(\d+)"', msg)
        if m_gid:
            g_id = m_gid.group(1)
        m_timer = re.search(r'"timer"\s*:\s*\{"id"\s*:\s*"(\d+)".*?"value"\s*:\s*"(-?\d+)"', msg)
        if m_timer:
            g_id = m_timer.group(1)
            timer_val = int(m_timer.group(2))
        if timer_val is not None and timer_val < 12 and not told:
            print(f"  {phone} waiting for next round")
            told = True
        if g_id and timer_val is not None and timer_val >= 12:
            break
    else:
        print(f"  {C.R}{phone} no betting window{C.END}")
        ws.close()
        return False

    ts = str(int(time.time() * 1000))
    side = "Blue" if str(bet_type) == "0" else "Red"
    bc = "0" if str(bet_type) == "0" else "1"
    fallback_bc = "11" if str(bet_type) == "0" else "10"
    bet_amt = int(amount)
    bet_xml = (
        f'<command channel="table-{table_id}">'
        f'<lpbet gm="baccarat_desktop" gId="{g_id}" uId="{u_id}" ck="{ts}"  >'
        f'<bet amt="{bet_amt}" bc="{bc}" ck="{ts}"/>'
        f"</lpbet></command>"
    )
    ws.send(bet_xml)
    confirmed = False
    locked = False
    retried = False
    start = time.time()
    while time.time() - start < 80:
        try:
            ws.settimeout(5)
            resp = ws.recv()
        except Exception:
            continue
        if not isinstance(resp, str):
            continue
        if '"betValidationError"' in resp:
            print(f"  {C.R}{phone} bet rejected{C.END}")
            if '"1057"' in resp and not locked and not retried:
                retried = True
                ts = str(int(time.time() * 1000))
                bet_xml = (
                    f'<command channel="table-{table_id}">'
                    f'<lpbet gm="baccarat_desktop" gId="{g_id}" uId="{u_id}" ck="{ts}"  >'
                    f'<bet amt="{bet_amt}" bc="{fallback_bc}" ck="{ts}"/>'
                    f"</lpbet></command>"
                )
                ws.send(bet_xml)
                continue
            confirmed = False
            break
        m_amt = re.search(r'"bets"\s*:\s*\{.*?"amount"\s*:\s*"(\d+)"', resp)
        if m_amt and not locked:
            print(f"  {phone} {side} {bet_amt} locked")
            locked = True
            confirmed = True
        if '"gameresult"' in resp:
            if locked:
                confirmed = True
                time.sleep(1)
                break
            confirmed = False
            break
    ws.close()
    if confirmed:
        meta["settled"] = True
    else:
        print(f"  {C.R}{phone} bet missed{C.END}")
    return confirmed

def run_register_mode(cfg):
    proxy = load_proxy()
    while True:
        phone = input(f"\n{C.C}Phone (0955...): {C.END}").strip()
        if not phone:
            break
        password = input(f"{C.C}Password (Enter = auto): {C.END}").strip() or generate_password()
        device_id = input(f"{C.C}deviceId (Enter = auto): {C.END}").strip() or generate_device_id()
        session = make_session(proxy)
        register_one(session, phone, password, device_id)
        if input(f"{C.Y}Register another? (y/n): {C.END}").strip().lower() not in ("y", "yes"):
            break

def run_cypherlink_register(cfg):
    try:
        target = int(input(f"{C.C}How many accounts total? {C.END}").strip() or "0")
        concurrent = int(input(f"{C.C}Concurrent (1-32): {C.END}").strip() or "1")
        concurrent = max(1, min(32, concurrent))
    except Exception:
        print(f"{C.R}Invalid input{C.END}")
        return
    if target <= 0:
        print(f"{C.R}Target must be > 0{C.END}")
        return

    password = input(f"{C.C}Password for all (Enter = auto): {C.END}").strip() or generate_password()
    proxy = load_proxy()
    done = 0
    attempted = set()

    print(f"\n{C.B}Target: {target} | Concurrent: {concurrent}{C.END}")
    print(f"{C.Y}Auto-detecting new SIMs...{C.END}\n")

    while done < target:
        phones = [p for p in get_cypherlink_phones() if p not in attempted]
        if not phones:
            print(f"{C.Y}Waiting for new SIMs... Done: {done}/{target}{C.END}")
            time.sleep(5)
            continue

        batch = phones[:concurrent]
        print(f"{C.C}Batch: {len(batch)} phones | Done: {done}/{target}{C.END}")
        shared_cf = get_cf_token()

        def worker(phone):
            attempted.add(phone)
            session = make_session(proxy)
            device_id = generate_device_id()
            success = register_one(session, phone, password, device_id, shared_cf_token=shared_cf)
            return phone, success

        with ThreadPoolExecutor(max_workers=concurrent) as ex:
            futures = [ex.submit(worker, p) for p in batch]
            for fut in as_completed(futures):
                phone, ok = fut.result()
                color = C.G if ok else C.R
                status = "OK" if ok else "FAIL"
                print(f"  {color}{phone} -> {status}{C.END}")
                if ok:
                    done += 1
                if done >= target:
                    break

        if done < target:
            time.sleep(3)

    print(f"\n{C.G}Finished. Created {done} accounts.{C.END}")

def check_one(phone, all_acc, proxy, cfg, retries=2):
    acc = all_acc.get(phone_key(phone))
    if not acc:
        print(f"  {C.R}No account data for {phone}{C.END}")
        return phone, 0.0
    sess = load_session(phone)
    existing_token = acc.get("token") or (sess.get("token") if sess else None)
    existing_suid = (sess.get("suid") if sess else "") or ""
    for attempt in range(retries + 1):
        session = make_session(proxy)
        token, suid, uid = login_with_security_check(
            session, phone, acc["password"], acc["device_id"], cfg,
            existing_token=existing_token, existing_suid=existing_suid
        )
        if token:
            claimed = claim_cashback(session, token, suid, acc["device_id"])
            if claimed is not None:
                print(f"  {C.G}{phone}: claim bonus {claimed}{C.END}")
            else:
                print(f"  {C.Y}{phone}: no bonus (see claim_cashback log above){C.END}")
            bal = get_balance(session, token, suid, acc["device_id"], phone=phone)
            pesos = parse_balance_pesos(bal)
            print(f"  {C.G}{phone}: balance {bal}{C.END}")
            return phone, pesos
        if attempt < retries:
            print(f"  {C.Y}{phone} retry {attempt + 1}...{C.END}")
            time.sleep(2)
            existing_token = None  # force fresh on retry
    print(f"  {C.R}{phone} login failed{C.END}")
    return phone, 0.0

def check_and_claim_all(cfg):
    print(f"""
{C.M}CHECK + CLAIM{C.END}
  {C.G}[2]{C.END} Paste phones
  {C.G}[3]{C.END} Load from accounts.txt
""")
    choice = input(f"{C.Y}Account source [2/3] (3): {C.END}").strip() or "3"
    phones = []
    if choice == "2":
        print(f"{C.C}Paste phones. Empty line to finish:{C.END}")
        while True:
            line = input().strip()
            if not line:
                break
            phones.append(phone_key(line.split("|")[0].split(":")[0]))
    else:
        phones = [phone_key(a["phone"]) for a in load_accounts()]

    if not phones:
        print(f"{C.R}No accounts{C.END}")
        return

    try:
        concurrent = int(input(f"{C.Y}Concurrent (1-32): {C.END}").strip() or "8")
        concurrent = max(1, min(32, concurrent))
    except Exception:
        concurrent = 8

    print(f"{C.G}{len(phones)} accounts ready | Concurrent: {concurrent}{C.END}")
    proxy = load_proxy()
    all_acc = {phone_key(a["phone"]): a for a in load_accounts()}
    total_pesos = 0.0

    with ThreadPoolExecutor(max_workers=concurrent) as ex:
        futs = [ex.submit(check_one, p, all_acc, proxy, cfg) for p in phones]
        for fut in as_completed(futs):
            phone, pesos = fut.result()
            total_pesos += pesos

    print(f"\n{C.B}Total estimated: PHP {total_pesos:.2f}{C.END}")

def mutual_invite(cfg):
    print(f"""
{C.M}MUTUAL INVITE{C.END}
  {C.G}[2]{C.END} Paste phones
  {C.G}[3]{C.END} Load from accounts.txt
""")
    choice = input(f"{C.Y}Account source [2/3] (3): {C.END}").strip() or "3"
    phones = []
    if choice == "2":
        print(f"{C.C}Paste phones. Empty line to finish:{C.END}")
        while True:
            line = input().strip()
            if not line:
                break
            phones.append(phone_key(line.split("|")[0].split(":")[0]))
    else:
        phones = [phone_key(a["phone"]) for a in load_accounts()]

    if len(phones) < 2:
        print(f"{C.R}Need 2+ accounts{C.END}")
        return

    try:
        concurrent = int(input(f"{C.Y}Concurrent (1-32): {C.END}").strip() or "4")
        concurrent = max(1, min(32, concurrent))
    except Exception:
        concurrent = 4

    print(f"{C.G}{len(phones)} accounts ready | Concurrent: {concurrent}{C.END}")
    proxy = load_proxy()
    all_acc = {phone_key(a["phone"]): a for a in load_accounts()}
    act_id = cfg.get("activity_id", "280222680316235781")
    print(f"{C.Y}Using activity_id: {act_id}{C.END}")

    def login_one(phone):
        acc = all_acc.get(phone)
        if not acc:
            print(f"  {C.R}No account data for {phone}{C.END}")
            return None
        session = make_session(proxy)
        sess = load_session(acc["phone"])
        existing_token = acc.get("token") or (sess.get("token") if sess else None)
        existing_suid = (sess.get("suid") if sess else "") or ""
        token, suid, uid = login_with_security_check(
            session, acc["phone"], acc["password"], acc["device_id"], cfg,
            existing_token=existing_token, existing_suid=existing_suid
        )
        if not token:
            print(f"  {C.R}Login failed {phone}{C.END}")
            return None
        print(f"  {C.G}Logged in {phone}{C.END}")
        return {
            "session": session, "token": token, "suid": suid,
            "device_id": acc["device_id"], "phone": phone,
        }

    sessions = []
    with ThreadPoolExecutor(max_workers=concurrent) as ex:
        futs = [ex.submit(login_one, p) for p in phones]
        for fut in as_completed(futs):
            res = fut.result()
            if res:
                sessions.append(res)

    if len(sessions) < 2:
        print(f"{C.R}Not enough logged-in{C.END}")
        return

    # Pair sequentially: 0-1, 2-3, ...
    pairs = []
    for i in range(0, len(sessions) - 1, 2):
        pairs.append((sessions[i], sessions[i + 1]))
    if len(sessions) % 2 == 1:
        print(f"  {C.Y}{sessions[-1]['phone']} left unpaired{C.END}")

    def do_pair(a, b):
        label_a = a["phone"]
        label_b = b["phone"]
        # Join
        for s in (a, b):
            rj = post_json(s["session"], "/bmp-treasure/v1/join", {
                "token": s["token"], "activity_id": act_id,
            }, s["token"], s["suid"], s["device_id"])
            try:
                print(f"  {s['phone']} join: {rj.json().get('code')} {rj.json().get('message')}")
            except Exception as e:
                print(f"  {s['phone']} join error: {e}")
        # Share
        shares = {}
        for s in (a, b):
            r = post_json(s["session"], "/bmp-treasure/v1/share", {
                "token": s["token"], "activity_id": act_id, "chest_level": 1, "channel": 6,
            }, s["token"], s["suid"], s["device_id"])
            try:
                data = r.json()
                tok = data.get("data", {}).get("share_token")
                shares[s["phone"]] = tok
                print(f"  {C.G}{s['phone']} share: {tok}{C.END}")
            except Exception as e:
                print(f"  {s['phone']} share error: {e}")
        # Cross help
        if shares.get(label_a):
            rh = help_account(b["session"], b["token"], b["suid"], b["device_id"], shares[label_a])
            try:
                print(f"  {label_b} help {label_a}: {rh.json()}")
            except Exception:
                print(f"  {label_b} help {label_a} raw: {getattr(rh, 'text', '')[:200]}")
        if shares.get(label_b):
            rh = help_account(a["session"], a["token"], a["suid"], a["device_id"], shares[label_b])
            try:
                print(f"  {label_a} help {label_b}: {rh.json()}")
            except Exception:
                print(f"  {label_a} help {label_b} raw: {getattr(rh, 'text', '')[:200]}")
        # Claim only if not already claimed
        for s in (a, b):
            already = check_chest_status(s["session"], s["token"], s["suid"], s["device_id"], act_id, 1)
            if already is True:
                print(f"  {C.Y}{s['phone']} chest already claimed, skip{C.END}")
                continue
            rc = claim_chest(s["session"], s["token"], s["suid"], s["device_id"], act_id, 1)
            try:
                print(f"  {s['phone']} claim: {rc.json()}")
            except Exception:
                print(f"  {s['phone']} claim raw: {getattr(rc, 'text', '')[:200]}")
        return True

    print(f"{C.Y}{len(pairs)} pairs{C.END}")
    with ThreadPoolExecutor(max_workers=concurrent) as ex:
        futs = [ex.submit(do_pair, a, b) for a, b in pairs]
        for fut in as_completed(futs):
            try:
                fut.result()
            except Exception as e:
                print(f"  {C.R}Pair error: {e}{C.END}")

    print(f"{C.G}Mutual invite + claim done{C.END}")

def run_deposit_mode(cfg):
    print(f"""
{C.M}DEPOSIT{C.END}
  {C.G}[2]{C.END} Paste accounts (phone or phone|pw)
  {C.G}[3]{C.END} Load from depo.txt
""")
    choice = input(f"{C.Y}Account source [2/3] (2): {C.END}").strip() or "2"
    to_deposit = []

    if choice == "2":
        print(f"{C.C}Paste phones (or phone|pw). Empty line to finish:{C.END}")
        lines = []
        while True:
            line = input().strip()
            if not line:
                break
            lines.append(line)
        fill_pass = input(f"{C.Y}Fill password (if needed) (): {C.END}").strip()
        for line in lines:
            if "|" in line:
                p, pw = line.split("|", 1)
                to_deposit.append((normalize_phone(p.strip()), pw.strip()))
            elif ":" in line:
                p, pw = line.split(":", 1)
                to_deposit.append((normalize_phone(p.strip()), pw.strip()))
            else:
                to_deposit.append((normalize_phone(line), fill_pass))
    else:
        if not os.path.exists(DEPOT_FILE):
            print(f"{C.R}depo.txt missing{C.END}")
            return
        with open(DEPOT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|")
                if len(parts) >= 2:
                    to_deposit.append((normalize_phone(parts[0]), parts[1]))
                elif ":" in line:
                    p, pw = line.split(":", 1)
                    to_deposit.append((normalize_phone(p.strip()), pw.strip()))

    if not to_deposit:
        print(f"{C.R}No accounts{C.END}")
        return

    print(f"{C.G}{len(to_deposit)} accounts ready{C.END}")
    proxy = load_proxy()
    all_acc = {phone_key(a["phone"]): a for a in load_accounts()}
    amount = cfg.get("deposit_amount", 130)

    for phone, password in to_deposit:
        acc = all_acc.get(phone_key(phone))
        session = make_session(proxy)
        print(f"{C.C}Deposit {phone}{C.END}")
        token = None
        suid = ""
        device_id = generate_device_id()
        if acc and acc.get("token"):
            token = acc["token"]
            device_id = acc.get("device_id", device_id)
            print(f"  {C.G}Using saved token{C.END}")
            sess = load_session(phone)
            if sess:
                suid = sess.get("suid", "")
                print(f"  {C.C}Loaded suid from session{C.END}")
            else:
                print(f"  {C.Y}No session file, suid empty{C.END}")
        else:
            pw = password or (acc["password"] if acc else "")
            if not pw:
                print(f"  {C.R}No password / token{C.END}")
                continue
            token, suid, uid = login_with_security_check(session, phone, pw, device_id, cfg)
        if token:
            deposit_and_save_qr(session, token, suid, device_id, amount, phone=phone)
        else:
            print(f"  {C.R}Deposit failed{C.END}")
        random_delay(cfg)

def run_relogin(cfg):
    print(f"""
{C.M}LOGIN{C.END}
  {C.G}[2]{C.END} Paste accounts (phone|password)
  {C.G}[3]{C.END} Load from .txt file
""")
    choice = input(f"{C.Y}Account source [2/3] (2): {C.END}").strip() or "2"
    accounts_to_login = []

    if choice == "2":
        print(f"{C.C}Paste accounts. Empty line to finish:{C.END}")
        lines = []
        while True:
            line = input().strip()
            if not line:
                break
            lines.append(line)
        fill_pass = input(f"{C.Y}Fill password (for accounts without password) (): {C.END}").strip()
        for line in lines:
            for sep in ["|", ",", ":"]:
                if sep in line:
                    p, pw = line.split(sep, 1)
                    accounts_to_login.append((normalize_phone(p.strip()), pw.strip()))
                    break
            else:
                accounts_to_login.append((normalize_phone(line), fill_pass))
    else:
        path = input(f"{C.Y}File path (retoken.txt): {C.END}").strip() or RETOKEN_FILE
        if not os.path.exists(path):
            print(f"{C.R}File not found{C.END}")
            return
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                for sep in ["|", ",", ":"]:
                    if sep in line:
                        p, pw = line.split(sep, 1)
                        accounts_to_login.append((normalize_phone(p.strip()), pw.strip()))
                        break
                else:
                    accounts_to_login.append((normalize_phone(line), ""))

    if not accounts_to_login:
        print(f"{C.R}No accounts{C.END}")
        return

    try:
        concurrent = int(input(f"{C.Y}Concurrent (1-32): {C.END}").strip() or "1")
        concurrent = max(1, min(32, concurrent))
    except Exception:
        concurrent = 1

    print(f"{C.G}{len(accounts_to_login)} accounts ready | Concurrent: {concurrent}{C.END}")
    proxy = load_proxy()
    all_acc = {phone_key(a["phone"]): a for a in load_accounts()}

    def worker(item):
        phone, password = item
        acc = all_acc.get(phone_key(phone))
        if not acc and not password:
            return phone, False, "No password"
        pw = password or acc["password"]
        device_id = acc["device_id"] if acc else generate_device_id()
        session = make_session(proxy)
        token, suid, uid = login_with_security_check(session, phone, pw, device_id, cfg, force_otp=True)
        if token:
            save_account(phone, pw, token, uid or "", device_id)
            return phone, True, "OK"
        return phone, False, "Failed"

    with ThreadPoolExecutor(max_workers=concurrent) as ex:
        futures = [ex.submit(worker, item) for item in accounts_to_login]
        for fut in as_completed(futures):
            phone, ok, msg = fut.result()
            color = C.G if ok else C.R
            print(f"  {color}{phone} -> {msg}{C.END}")

WINNER_FILE = "winner.txt"

def parse_balance_pesos(bal_str):
    if not bal_str:
        return 0.0
    try:
        return float(str(bal_str).split()[0])
    except Exception:
        return 0.0

def save_winner(phone, balance):
    line = f"{phone}|{balance:.2f}|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    with open(WINNER_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(f"  {C.G}Saved to winner.txt: {phone} = {balance:.2f}{C.END}")

def run_baccarat_crossbet(cfg):
    print(f"""
{C.M}BACCARAT CROSS-BET (game 404, HTTP session){C.END}
  {C.G}[2]{C.END} Paste phones (2 accounts)
  {C.G}[3]{C.END} Load from accounts.txt (first 2)
""")
    choice = input(f"{C.Y}Account source [2/3] (2): {C.END}").strip() or "2"
    phones = []

    if choice == "2":
        print(f"{C.C}Paste 2 phones (A then B). Empty line to finish:{C.END}")
        while True:
            line = input().strip()
            if not line:
                break
            phones.append(phone_key(line.split("|")[0].split(":")[0]))
    else:
        phones = [phone_key(a["phone"]) for a in load_accounts()[:2]]

    if len(phones) < 2:
        print(f"{C.R}Need 2 accounts{C.END}")
        return

    print(f"{C.G}Accounts: {phones[0]} (Blue) vs {phones[1]} (Red){C.END}")
    proxy = load_proxy()
    all_acc = {phone_key(a["phone"]): a for a in load_accounts()}
    sessions = []

    for phone in phones[:2]:
        acc = all_acc.get(phone_key(phone))
        if not acc:
            print(f"  {C.R}No account data for {phone}{C.END}")
            continue
        session = make_session(proxy)
        token, suid, uid = login_with_security_check(session, phone, acc["password"], acc["device_id"], cfg)
        if token:
            sessions.append({
                "session": session,
                "token": token,
                "suid": suid,
                "device_id": acc["device_id"],
                "phone": phone,
            })
            print(f"  {C.G}Logged in {phone}{C.END}")
        else:
            print(f"  {C.R}Login failed {phone}{C.END}")

    if len(sessions) < 2:
        print(f"{C.R}Not enough logged-in{C.END}")
        return

    a, b = sessions[0], sessions[1]
    bal_a = get_balance(a["session"], a["token"], a["suid"], a["device_id"], phone=a["phone"])
    bal_b = get_balance(b["session"], b["token"], b["suid"], b["device_id"], phone=b["phone"])
    print(f"  Balance A: {bal_a}")
    print(f"  Balance B: {bal_b}")

    try:
        amt_a = int(float(str(bal_a).split()[0])) if bal_a else 10
        amt_b = int(float(str(bal_b).split()[0])) if bal_b else 10
    except Exception:
        amt_a = amt_b = 10
    amt_a = max(10, amt_a)
    amt_b = max(10, amt_b)

    game_id = str(cfg.get("third_game_id", "404"))
    print(f"{C.Y}Ready: {a['phone']}={amt_a} Blue, {b['phone']}={amt_b} Red | game {game_id}{C.END}")

    meta_a = get_jsession_http(a["session"], a["token"], a["suid"], a["device_id"], game_id)
    meta_b = get_jsession_http(b["session"], b["token"], b["suid"], b["device_id"], game_id)

    if meta_a:
        place_baccarat_bet(meta_a, amt_a, "0", a["phone"])
    else:
        print(f"  {C.R}No session for A{C.END}")
    if meta_b:
        place_baccarat_bet(meta_b, amt_b, "1", b["phone"])
    else:
        print(f"  {C.R}No session for B{C.END}")

    result = None
    if not (meta_a and meta_a.get("settled")) and not (meta_b and meta_b.get("settled")):
        if meta_a:
            result = wait_for_result(meta_a)
        elif meta_b:
            result = wait_for_result(meta_b)

    if result:
        color = C.G if result == "player" else C.R if result == "banker" else C.Y
        side = "Blue" if result == "player" else "Red" if result == "banker" else "Tie"
        print(f"  {color}Winner: {side} ({result}){C.END}")
    else:
        print(f"  {C.Y}No result received{C.END}")

    print(f"  {C.C}Checking balances...{C.END}")
    bal_a2 = get_balance(a["session"], a["token"], a["suid"], a["device_id"], phone=a["phone"])
    bal_b2 = get_balance(b["session"], b["token"], b["suid"], b["device_id"], phone=b["phone"])
    print(f"  {C.G}Balance A: {bal_a2}{C.END}")
    print(f"  {C.G}Balance B: {bal_b2}{C.END}")

def login_one_account(phone, all_acc, proxy, cfg, max_bal):
    acc = all_acc.get(phone_key(phone))
    if not acc:
        print(f"  {C.R}{phone} not in accounts.txt{C.END}")
        return None
    token = suid = None
    session = None
    for _try in range(2):
        session = make_session(proxy)
        token, suid, uid = login_with_security_check(session, phone, acc["password"], acc["device_id"], cfg)
        if token:
            break
        time.sleep(1)
    if not token:
        print(f"  {C.R}{phone} login failed{C.END}")
        return None
    bal = get_balance(session, token, suid, acc["device_id"], phone=phone)
    pesos = parse_balance_pesos(bal)
    print(f"  {phone}: {pesos:.2f}")
    return {
        "session": session,
        "token": token,
        "suid": suid,
        "device_id": acc["device_id"],
        "phone": phone,
        "balance": pesos,
    }

def connect_one_game(acc, game_id):
    meta = None
    for _try in range(3):
        meta = get_jsession_http(acc["session"], acc["token"], acc["suid"], acc["device_id"], game_id)
        if meta:
            return acc["phone"], meta
        time.sleep(1)
    print(f"  {C.R}{acc['phone']} connect failed{C.END}")
    return acc["phone"], None

def bet_one(acc, meta, amount, side):
    if not meta:
        print(f"  {C.R}No session {acc['phone']}{C.END}")
        return acc["phone"], False
    ok = place_baccarat_bet(meta, amount, side, acc["phone"])
    return acc["phone"], ok

def run_baccarat_merge(cfg):
    print(f"""
{C.M}BACCARAT MERGE (multi-account, max balance){C.END}
  {C.G}[2]{C.END} Paste phones
  {C.G}[3]{C.END} Load from accounts.txt
""")
    choice = input(f"{C.Y}Account source [2/3] (3): {C.END}").strip() or "3"
    phones = []

    if choice == "2":
        print(f"{C.C}Paste phones. Empty line to finish:{C.END}")
        while True:
            line = input().strip()
            if not line:
                break
            phones.append(phone_key(line.split("|")[0].split(":")[0]))
    else:
        phones = [phone_key(a["phone"]) for a in load_accounts()]

    if len(phones) < 2:
        print(f"{C.R}Need at least 2 accounts{C.END}")
        return

    try:
        max_bal = float(input(f"{C.C}Max balance (stop & save): {C.END}").strip())
        max_diff = float(input(f"{C.C}Max difference for pairing: {C.END}").strip())
        workers = int(input(f"{C.C}Concurrent (1-32): {C.END}").strip() or "8")
        workers = max(1, min(32, workers))
    except Exception:
        print(f"{C.R}Invalid input{C.END}")
        return

    print(f"{C.G}Accounts: {len(phones)} | Max: {max_bal} | Diff: {max_diff} | Workers: {workers}{C.END}")
    proxy = load_proxy()
    all_acc = {phone_key(a["phone"]): a for a in load_accounts()}

    print(f"  {C.Y}Logging in...{C.END}")
    logged = {}
    active = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(login_one_account, p, all_acc, proxy, cfg, max_bal): p for p in phones}
        for fut in as_completed(futs):
            res = fut.result()
            if not res:
                continue
            logged[res["phone"]] = res
            if res["balance"] >= max_bal:
                save_winner(res["phone"], res["balance"])
            elif res["balance"] >= 10:
                active.append(res)

    def show_final():
        print(f"\n{C.M}Final balance{C.END}")
        for phone in phones:
            acc = logged.get(phone)
            if not acc:
                print(f"  {phone}: login failed")
                continue
            live = None
            if acc.get("jsession"):
                live = get_pp_wallet_balance(acc["jsession"])
            if live is None:
                text = get_balance(acc["session"], acc["token"], acc["suid"], acc["device_id"], phone=phone)
                pesos = parse_balance_pesos(text) if text else acc["balance"]
            else:
                pesos = live
                acc["balance"] = live
            print(f"  {phone}: {pesos:.2f}")

    if len(active) < 2:
        print(f"{C.Y}Not enough accounts to pair{C.END}")
        show_final()
        return

    game_id = str(cfg.get("third_game_id", "404"))
    round_num = 0

    while len(active) >= 2:
        active = [a for a in active if a["balance"] >= 10]
        if len(active) < 2:
            break
        round_num += 1
        pool = sorted(active, key=lambda x: (x["balance"], x["phone"]))
        pairs = []
        used = set()
        order = list(range(len(pool)))
        if len(pool) > 1:
            shift = (round_num - 1) % len(pool)
            order = order[shift:] + order[:shift]
        for i in order:
            if i in used:
                continue
            best = None
            best_d = None
            for j in order:
                if j == i or j in used:
                    continue
                d = abs(pool[i]["balance"] - pool[j]["balance"])
                if d <= max_diff and (best_d is None or d < best_d):
                    best, best_d = j, d
            if best is None:
                continue
            pairs.append((pool[i], pool[best]))
            used.add(i)
            used.add(best)
        for i, acc in enumerate(pool):
            if i not in used:
                print(f"  sit out {acc['phone']} (diff > {max_diff:.0f})")
        if not pairs:
            print(f"  {C.Y}No pairs within {max_diff:.0f}. Stop.{C.END}")
            break

        print(f"\n{C.M}=== ROUND {round_num} | {len(pairs)} pairs ==={C.END}")
        metas = {}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = []
            for a, b in pairs:
                futs.append(ex.submit(connect_one_game, a, game_id))
                futs.append(ex.submit(connect_one_game, b, game_id))
            for fut in as_completed(futs):
                phone, meta = fut.result()
                metas[phone] = meta
                if meta:
                    logged[phone]["jsession"] = meta["jsession"]

        ready = []
        for a, b in pairs:
            if metas.get(a["phone"]) and metas.get(b["phone"]):
                ready.append((a, b))
            else:
                who = a["phone"] if not metas.get(a["phone"]) else b["phone"]
                print(f"  {who} skipped this round")
        if not ready:
            time.sleep(2)
            continue

        before = {}
        bet_ok = {}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = []
            for a, b in ready:
                amt_a = max(10, min(int(a["balance"]), int(max_bal - a["balance"])))
                amt_b = max(10, min(int(b["balance"]), int(max_bal - b["balance"])))
                before[a["phone"]] = a["balance"]
                before[b["phone"]] = b["balance"]
                print(f"  {a['phone']} {amt_a} Blue vs {b['phone']} {amt_b} Red")
                futs.append(ex.submit(bet_one, a, metas[a["phone"]], amt_a, "0"))
                futs.append(ex.submit(bet_one, b, metas[b["phone"]], amt_b, "1"))
            for fut in as_completed(futs):
                phone, ok = fut.result()
                bet_ok[phone] = ok

        for a, b in ready:
            for acc in (a, b):
                meta = metas.get(acc["phone"]) or {}
                bal = get_pp_wallet_balance(meta.get("jsession", "")) if meta.get("jsession") else None
                if bal is not None:
                    acc["balance"] = bal
            old_a = before.get(a["phone"], a["balance"])
            old_b = before.get(b["phone"], b["balance"])
            def mark(old, new):
                if new > old + 1:
                    return "WIN"
                if new < old - 1:
                    return "LOSS"
                return "PUSH"
            print(
                f"  {a['phone']} {mark(old_a, a['balance'])} {a['balance']:.2f}"
                f" | {b['phone']} {mark(old_b, b['balance'])} {b['balance']:.2f}"
            )
            if a["balance"] >= max_bal:
                save_winner(a["phone"], a["balance"])
            if b["balance"] >= max_bal:
                save_winner(b["phone"], b["balance"])

        active = [acc for acc in active if 10 <= acc["balance"] < max_bal]
        print(f"  {C.C}Active: {len(active)}{C.END}")

    show_final()

def form_api(session, path, body, suid, device_id, cf_token=None, cf_scene=None):
    extra = {"suid": suid, "dudd": device_id}
    if cf_token:
        extra["cf-token"] = cf_token
        extra["cf-scene"] = cf_scene or "COMMON_MANAGED"
    r = post_signed(session, path, body, extra)
    if r is None:
        return {"code": 0, "msg": "no response"}
    try:
        return r.json()
    except Exception:
        return {"code": 0, "msg": (r.text or "")[:180]}

def otp_on_phone(phone, label, after_timestamp=None, exclude_otp=None):
    print(f"  Waiting OTP on {phone} ({label})", flush=True)
    code = get_latest_otp(
        phone,
        after_timestamp=after_timestamp or int(time.time() * 1000) - 15000,
        exclude_otp=exclude_otp,
        max_age_seconds=60,
        wait_seconds=50,
    )
    if not code:
        code = input(f"  OTP for {phone}: ").strip()
    return code

def verify_sms(session, token, suid, device_id, phone, otp, sms_type):
    body = {
        "token": token,
        "phone": phone,
        "telephoneCode": "+63",
        "code": otp,
        "type": str(sms_type),
    }
    return form_api(session, "/api/v2/sms/verify/short/msg/code", body, suid, device_id)

def send_sms(session, token, suid, device_id, phone, sms_type):
    cf = get_cf_token()
    body = {
        "phone": phone,
        "telephoneCode": "+63",
        "type": str(sms_type),
        "deviceId": device_id,
        "token": token,
    }
    return form_api(session, "/api/v2/sms/send/short/msg", body, suid, device_id, cf, "COMMON_MANAGED")

def account_otp_gate(session, token, suid, device_id, account_phone):
    phone = phone_no_zero(account_phone)
    print(f"  Account OTP required. Sending to {phone}")
    sent = send_sms(session, token, suid, device_id, phone, 24)
    print(f"  {sent.get('msg')}")
    if sent.get("code") not in (200, "200"):
        return False
    otp = otp_on_phone(account_phone, "account")
    if not otp:
        return False
    checked = verify_sms(session, token, suid, device_id, phone, otp, 24)
    print(f"  Account OTP: {checked.get('msg')}")
    return checked.get("code") in (200, "200")

def bind_gcash(session, token, suid, device_id, account_phone, gcash):
    gcash = normalize_phone(gcash)
    print(f"  Step 1: OTP on account {normalize_phone(account_phone)}", flush=True)
    if not account_otp_gate(session, token, suid, device_id, account_phone):
        print(f"  {C.R}Account OTP failed. Cannot bind yet.{C.END}", flush=True)
        return None
    checked = form_api(session, "/api/v2/check/account/info", {
        "token": token,
        "account_no": gcash,
        "type": "3",
    }, suid, device_id)
    print(f"  Check number: {checked.get('msg')} {checked.get('data')}", flush=True)
    if checked.get("code") not in (200, "200"):
        print(f"  {C.R}Cannot use {gcash}: {checked.get('msg')}{C.END}", flush=True)
        return None
    if (checked.get("data") or {}).get("bonded_by_other"):
        print(f"  {C.R}{gcash} already used by another account{C.END}", flush=True)
        return None

    print(f"  Step 2: OTP on new GCash {gcash}", flush=True)
    sms_cf = get_cf_token()
    sent_at = int(time.time() * 1000)
    sent = form_api(session, "/api/v2/sms/send/short/msg", {
        "phone": gcash,
        "telephoneCode": "+63",
        "type": "19",
        "deviceId": device_id,
        "token": token,
    }, suid, device_id, sms_cf, "COMMON_MANAGED")
    print(f"  Bind OTP: {sent.get('code')} {sent.get('msg')}", flush=True)
    if sent.get("code") not in (200, "200"):
        return None
    with ThreadPoolExecutor(max_workers=1) as pool:
        token_job = pool.submit(get_bind_tokens)
        otp = otp_on_phone(gcash, "gcash", after_timestamp=sent_at - 5000)
        cf_withdraw, cf_main = token_job.result()
    if not otp:
        print(f"  {C.R}No OTP{C.END}", flush=True)
        return None
    print(f"  Using bind OTP: {otp}", flush=True)
    verified = verify_sms(session, token, suid, device_id, gcash, otp, 19)
    print(f"  Bind verify: {verified.get('code')} {verified.get('msg')}", flush=True)
    if verified.get("code") not in (200, "200"):
        return None
    base = {
        "token": token,
        "account_no": gcash,
        "first_name": "",
        "middle_name": "",
        "last_name": "",
        "pay_code": "GCASH",
        "type": "3",
        "logicVersion": "2",
    }
    tries = [
        ("withdraw key", cf_withdraw, False),
        ("main key", cf_main, False),
        ("main key + code", cf_main, True),
    ]
    seen = set()
    for label, cf, with_code in tries:
        if not cf or (cf, with_code) in seen:
            continue
        seen.add((cf, with_code))
        body = dict(base)
        if with_code:
            body["code"] = otp
        print(f"  Bind try {label}", flush=True)
        added = form_api(session, "/api/v2/add/withdraw/no", body, suid, device_id, cf, "COMMON_INVISABLE")
        print(f"  Bind result: {added.get('code')} {added.get('msg')} {added.get('data')}", flush=True)
        data = added.get("data") or {}
        if added.get("code") in (200, "200") and isinstance(data, dict) and data.get("account_id"):
            return data.get("account_id"), data.get("account_no") or phone_no_zero(gcash)
    return None

def list_bound_gcash(session, token, suid, device_id):
    listed = form_api(session, "/api/v2/get/withdraw/list", {
        "type": "3",
        "token": token,
    }, suid, device_id)
    accounts = ((listed.get("data") or {}).get("list") or [])
    default = form_api(session, "/api/v2/get/default/account", {
        "product_type": "3",
        "token": token,
    }, suid, device_id)
    picked = (default.get("data") or {}) if isinstance(default.get("data"), dict) else {}
    if not picked.get("account_id") and accounts:
        for item in accounts:
            if item.get("is_true"):
                picked = item
                break
        if not picked.get("account_id"):
            picked = accounts[0]
    return accounts, picked

def withdraw_one(session, token, suid, device_id, account_phone, gcash, amount):
    if gcash:
        gcash = normalize_phone(gcash)
        target = phone_no_zero(gcash)
        accounts, _ = list_bound_gcash(session, token, suid, device_id)
        account_id = None
        gcash_no = None
        for item in accounts:
            if phone_no_zero(str(item.get("account_no") or "")) == target:
                account_id = item.get("account_id")
                gcash_no = item.get("account_no")
                break
        if account_id:
            print(f"  {target} already bound. Using that.")
        else:
            print(f"  Binding {gcash}. OTP on account, then OTP on this GCash.", flush=True)
            bound = bind_gcash(session, token, suid, device_id, account_phone, gcash)
            if not bound:
                print(f"  {C.R}Bind failed{C.END}")
                return False
            account_id, gcash_no = bound
            print(f"  {C.G}Bound {gcash_no}{C.END}")
    else:
        _, picked = list_bound_gcash(session, token, suid, device_id)
        account_id = picked.get("account_id")
        gcash_no = picked.get("account_no")
        if not account_id:
            print(f"  {C.R}No GCash bound yet{C.END}")
            return False
        print(f"  Using bound {gcash_no}")

    amount = int(amount)
    amount = max_withdrawable(amount) if amount >= 50 else 50
    if amount < 50:
        print(f"  {C.R}Amount too small. Min 50.{C.END}")
        return False
    quantity = amount // 50
    price = 50
    print(f"  \033[90mWithdrawing {amount} to {gcash_no}...{C.END}", flush=True)
    kyc = form_api(session, "/api/v2/get/kyc", {
        "token": token,
        "is_pre_ex_valid": "1",
    }, suid, device_id)
    kyc_data = kyc.get("data") or {}
    print(f"  KYC: skip={kyc_data.get('skip_kyc_flag')} full={kyc_data.get('kyc_is_full')} model={kyc_data.get('kyc_model')}", flush=True)
    bal = form_api(session, "/api/v2/check/balance", {
        "price": str(price),
        "quantity": str(quantity),
        "token": token,
    }, suid, device_id)
    if bal.get("code") not in (200, "200"):
        print(f"  {C.R}Balance check: {bal}{C.END}")
        return False
    result = form_api(session, "/api/v2/exchange", {
        "id": "2",
        "product_type": "3",
        "g_cash_no": phone_no_zero(str(gcash_no)),
        "quantity": str(quantity),
        "account_id": str(account_id),
        "token": token,
    }, suid, device_id)
    print(f"  Exchange: {result}", flush=True)
    msg = result.get("msg") or ""
    data = result.get("data") or {}
    if isinstance(data, list) and data:
        data = data[0]
    if result.get("code") in (200, "200"):
        left = data.get("balance") if isinstance(data, dict) else ""
        order = data.get("no") if isinstance(data, dict) else ""
        print(f"  {C.Y}pending {order} balance {left}{C.END}")

        def do_allin():
            print(f"  {C.G}First withdraw success. Auto all-in remaining.{C.END}")
            # re-fetch balance
            bal_txt = get_balance(session, token, suid, device_id, phone=account_phone)
            pesos = parse_balance_pesos(bal_txt)
            allin = max_withdrawable(pesos)
            if allin >= 50:
                print(f"  {C.Y}All-in {allin}{C.END}")
                withdraw_one(session, token, suid, device_id, account_phone, None, allin)
            else:
                print(f"  {C.Y}Remaining {pesos} too small for all-in.{C.END}")

        show_withdraw_history(session, token, suid, device_id, refresh_secs=15, watch_order=order, on_success=do_allin)
        return True
    if result.get("code") == 106006:
        print(f"  {C.R}KYC required. This account cannot cashout until ID is verified in the app.{C.END}")
        return False
    extra = ""
    if isinstance(data, dict):
        if data.get("remaining_display"):
            extra = f" need {data.get('remaining_display')} more turnover"
        elif data.get("msg"):
            extra = f" {data.get('msg')}"
    print(f"  {C.R}Withdraw failed: {msg}{extra}{C.END}")
    return False

def max_withdrawable(balance):
    """Largest multiple of 50 <= balance, min 50."""
    try:
        b = int(float(balance))
    except Exception:
        return 0
    if b < 50:
        return 0
    return (b // 50) * 50

def show_withdraw_history(session, token, suid, device_id, limit=5, refresh_secs=15, watch_order=None, on_success=None):
    paths = [
        "/api/v2/withdraw/history",
        "/api/v2/exchange/list",
        "/api/v2/get/withdraw/record",
        "/api/v2/withdraw/list",
        "/api/v2/payment/withdraw/history",
    ]
    print(f"  {C.Y}History refresh every {refresh_secs}s. Ctrl+C to stop.{C.END}")
    success_seen = False
    try:
        while True:
            found = False
            for path in paths:
                body = {"token": token, "page": "1", "page_size": str(limit), "type": "3"}
                r = form_api(session, path, body, suid, device_id)
                if r.get("code") in (200, "200", 0):
                    data = r.get("data") or {}
                    items = data if isinstance(data, list) else data.get("list") or data.get("records") or data.get("items") or []
                    if items:
                        found = True
                        print(f"  [{datetime.now().strftime('%H:%M:%S')}] history:")
                        for it in items[:limit]:
                            if not isinstance(it, dict):
                                continue
                            no = str(it.get("no") or it.get("order_no") or it.get("id") or "")
                            amt = it.get("amount") or it.get("price") or it.get("money") or ""
                            st = str(it.get("status") or it.get("state") or it.get("msg") or "").lower()
                            tm = it.get("created_at") or it.get("time") or it.get("create_time") or ""
                            color = C.W
                            label = "withdrawing"
                            if "success" in st or "complete" in st or st in ("2", "1", "done"):
                                color = C.G
                                label = "success"
                            elif "pending" in st or "process" in st or st in ("0", "pending"):
                                color = C.Y
                                label = "pending"
                            else:
                                color = "\033[90m"
                                label = st or "withdrawing"
                            print(f"    {color}{no} | {amt} | {label} | {tm}{C.END}")
                            if watch_order and no == watch_order and label == "success" and not success_seen:
                                success_seen = True
                                if on_success:
                                    on_success()
                        break
            if not found:
                print(f"  \033[90m[{datetime.now().strftime('%H:%M:%S')}] withdrawing...{C.END}")
            time.sleep(refresh_secs)
    except KeyboardInterrupt:
        print(f"\n  {C.Y}History refresh stopped.{C.END}")
    return success_seen
    """Read remaining turnover by probing exchange. Returns pesos remaining, 0 if clear, None on error.
    Safe only when turnover is not yet met (exchange returns 103040 without withdrawing)."""
    _, picked = list_bound_gcash(session, token, suid, device_id)
    account_id = picked.get("account_id")
    gcash_no = picked.get("account_no")
    if not account_id:
        print(f"  {C.R}No GCash bound. Cannot read turnover.{C.END}")
        return None
    result = form_api(session, "/api/v2/exchange", {
        "id": "2",
        "product_type": "3",
        "g_cash_no": phone_no_zero(str(gcash_no)),
        "quantity": "1",
        "account_id": str(account_id),
        "token": token,
    }, suid, device_id)
    code = result.get("code")
    data = result.get("data") or {}
    if isinstance(data, list) and data:
        data = data[0]
    if code == 103040 and isinstance(data, dict):
        remaining = data.get("remaining_amount")
        display = data.get("remaining_display") or ""
        if remaining is not None:
            pesos = int(remaining) / 100
            print(f"  Turnover left: {display or pesos}")
            return pesos
    if code in (200, "200"):
        print(f"  {C.Y}Exchange succeeded. Turnover already clear (a withdraw was sent).{C.END}")
        return 0
    print(f"  {C.R}Turnover probe: {result.get('msg') or code}{C.END}")
    return None

def _pb_varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)

def _pb_var(field, n):
    return bytes([(field << 3) | 0]) + _pb_varint(n)

def _pb_bytes(field, data):
    return bytes([(field << 3) | 2]) + _pb_varint(len(data)) + data

def ge_packet(cmd, inner, token, key):
    body = b""
    if cmd is not None:
        body += _pb_var(1, cmd)
    if inner:
        body += _pb_bytes(2, inner)
    body += _pb_bytes(3, token) + _pb_bytes(4, key)
    return body

def ge_open(session, token, suid, device_id):
    extra = {"dudd": device_id, "suid": suid, "CaType": "JILI", "token": token}
    r = post_signed(session, "/api/v2/jili/login", {
        "token": token,
        "third_game_id": "103",
        "company_id": "1",
    }, extra)
    if not r:
        print(f"  {C.R}JILI login failed{C.END}")
        return None
    try:
        data = r.json()
    except Exception:
        print(f"  {C.R}JILI login not JSON{C.END}")
        return None
    game_url = data.get("game_url") or ""
    if not game_url:
        print(f"  {C.R}No game_url {data}{C.END}")
        return None
    parsed = urllib.parse.urlparse(game_url)
    qs = urllib.parse.parse_qs(parsed.query)
    sso = (qs.get("ssoKey") or [""])[0]
    gs_host = (qs.get("gs") or [""])[0][::-1]
    web_host = (qs.get("be") or [""])[0][::-1]
    if not web_host and parsed.hostname:
        web_host = parsed.hostname.replace("wbgame.", "wbwebapi.", 1)
    if not sso or not gs_host or not web_host or "." not in web_host:
        print(f"  {C.R}Bad game_url {game_url[:180]}{C.END}")
        return None
    origin = f"{parsed.scheme}://{parsed.hostname}"
    print(f"  SSO {web_host}")
    try:
        web = requests.post(
            f"https://{web_host}/sso-login.api",
            data={"key": sso, "lang": "en-US"},
            headers={
                "User-Agent": session.headers.get("User-Agent", "Mozilla/5.0"),
                "Origin": origin,
                "Referer": origin + "/",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=20,
        )
    except Exception as e:
        print(f"  {C.R}SSO connect failed: {e}{C.END}")
        return None
    try:
        info = web.json()
    except Exception:
        print(f"  {C.R}SSO login failed{C.END}")
        return None
    raw_token = info.get("token") or ""
    if len(raw_token) != 40:
        print(f"  {C.R}SSO token missing{C.END}")
        return None
    print(f"  Golden Empire session ok")
    return {
        "url": f"https://{gs_host}/mw2/req",
        "origin": origin,
        "token": bytes.fromhex(raw_token),
        "key": os.urandom(32),
        "ua": session.headers.get("User-Agent", "Mozilla/5.0"),
    }

def ge_send(game, cmd, inner):
    body = ge_packet(cmd, inner, game["token"], game["key"])
    try:
        r = requests.post(
            game["url"],
            data=body,
            headers={
                "User-Agent": game["ua"],
                "Accept": "*/*",
                "Origin": game["origin"],
                "Referer": game["origin"] + "/",
            },
            timeout=20,
        )
        return r.status_code == 200 and len(r.content) > 0
    except Exception as e:
        print(f"  {C.R}Spin request failed: {e}{C.END}")
        return False

def ge_handshake(game):
    lang = _pb_bytes(1, b"en-US")
    browser = (
        _pb_bytes(1, b"Windows")
        + _pb_bytes(2, b"en-US")
        + _pb_bytes(3, _pb_bytes(1, b"chrome") + _pb_bytes(2, b"155.0.0.0") + _pb_bytes(3, b"en-US") + _pb_var(4, 2560) + _pb_var(5, 1440))
        + _pb_bytes(4, b"")
        + _pb_bytes(5, b"")
    )
    steps = [
        (1, browser),
        (58, _pb_var(1, 0)),
        (69, None),
        (51, None),
        (60, lang),
        (58, _pb_var(1, 0)),
        (58, _pb_var(1, 0)),
        (19, _pb_var(1, 17)),
        (10, lang + _pb_var(2, 17)),
        (21, None),
        (33, None),
        (49, lang + _pb_var(2, 17)),
        (25, None),
        (27, None),
        (55, None),
    ]
    for cmd, inner in steps:
        if not ge_send(game, cmd, inner):
            return False
    return True

def ge_spin_one(game, amount):
    payload = b"\x09" + struct.pack("<d", float(amount))
    flags = bytes.fromhex("ca0106080010002000")
    return ge_send(game, None, payload + flags)

def run_turnover_clear(cfg):
    print(f"""
{C.M}TURNOVER CLEAR (Golden Empire){C.END}
  {C.G}[2]{C.END} Paste phone
  {C.G}[3]{C.END} Load from accounts.txt (first)
""")
    choice = input(f"{C.Y}Account source [2/3] (2): {C.END}").strip() or "2"
    phones = []
    if choice == "3":
        phones = [phone_key(a["phone"]) for a in load_accounts()[:1]]
    else:
        print(f"{C.C}Paste phone. Empty line to finish:{C.END}")
        while True:
            line = input().strip()
            if not line:
                break
            phones.append(phone_key(line.split("|")[0].split(":")[0]))
            break
    if not phones:
        print(f"{C.R}No account{C.END}")
        return
    phone = phones[0]
    all_acc = {phone_key(a["phone"]): a for a in load_accounts()}
    acc = all_acc.get(phone_key(phone))
    if not acc:
        print(f"{C.R}{phone} not in accounts.txt{C.END}")
        return
    proxy = load_proxy()
    session = make_session(proxy)
    token, suid, uid = login_with_security_check(session, phone, acc["password"], acc["device_id"], cfg)
    if not token:
        print(f"{C.R}Login failed{C.END}")
        return
    print(f"  Logged in {phone}")
    remaining = probe_turnover(session, token, suid, acc["device_id"])
    if remaining is None:
        return
    if remaining <= 0:
        print(f"  {C.G}No turnover left.{C.END}")
        return
    mode = input(f"{C.C}[1] Clear all turnover  [2] Set spin count (1): {C.END}").strip() or "1"
    bet_txt = input(f"{C.C}Bet amount (1): {C.END}").strip() or "1"
    try:
        bet = float(bet_txt)
    except Exception:
        bet = 1
    if bet <= 0:
        bet = 1
    if mode == "2":
        count_txt = input(f"{C.C}How many spins: {C.END}").strip() or "1"
        try:
            needed = int(count_txt)
        except Exception:
            needed = 1
        clear_all = False
    else:
        needed = int(remaining / bet)
        if remaining - needed * bet > 0.009:
            needed += 1
        clear_all = True
    if needed < 1:
        needed = 1
    print(f"  {needed} spins x {bet}")
    game = ge_open(session, token, suid, acc["device_id"])
    if not game:
        return
    if not ge_handshake(game):
        print(f"  {C.R}Game handshake failed{C.END}")
        return
    placed = 0
    stalled = 0
    start_left = remaining
    while placed < needed:
        if not ge_spin_one(game, bet):
            print(f"  {C.R}Spin failed{C.END}")
            break
        placed += 1
        print(f"  Spin {placed}/{needed} bet {bet}")
        if clear_all and (placed == 3 or placed % 10 == 0):
            left = probe_turnover(session, token, suid, acc["device_id"])
            if left is None:
                break
            if left <= 0:
                print(f"  {C.G}Turnover clear. Withdraw sent.{C.END}")
                return
            dropped = start_left - left
            if dropped < bet * 0.5:
                stalled += 1
            else:
                stalled = 0
                start_left = left
            more = int(left / bet)
            if left - more * bet > 0.009:
                more += 1
            needed = placed + max(more, 1)
            if stalled >= 2:
                print(f"  {C.R}Spins are not counting. Server rejected the bet packet.{C.END}")
                break
        time.sleep(0.4)
    if clear_all:
        left = probe_turnover(session, token, suid, acc["device_id"])
        if left is not None and left <= 0:
            print(f"  {C.G}Turnover clear. Withdraw sent.{C.END}")
            return
        if left is not None:
            print(f"  Turnover left: {left}")
    print(f"  Done. Sent {placed} spins x {bet}.")

def run_withdraw(cfg):
    print(f"""
{C.M}GCASH WITHDRAW{C.END}
  {C.G}[2]{C.END} Paste phones
  {C.G}[3]{C.END} Load from accounts.txt
""")
    choice = input(f"{C.Y}Account source [2/3] (2): {C.END}").strip() or "2"
    phones = []
    if choice == "3":
        phones = [phone_key(a["phone"]) for a in load_accounts()]
    else:
        print(f"{C.C}Paste phones. Empty line to finish:{C.END}")
        while True:
            line = input().strip()
            if not line:
                break
            phones.append(phone_key(line.split("|")[0].split(":")[0]))
    if not phones:
        print(f"{C.R}No accounts{C.END}")
        return
    all_acc = {phone_key(a["phone"]): a for a in load_accounts()}
    proxy = load_proxy()
    for phone in phones:
        acc = all_acc.get(phone_key(phone))
        print(f"\n{C.M}Withdraw {phone}{C.END}", flush=True)
        if not acc:
            print(f"  {C.R}Not in accounts.txt{C.END}", flush=True)
            continue
        try:
            print("  Logging in...", flush=True)
            session = make_session(proxy)
            token, suid, uid = login_with_security_check(session, phone, acc["password"], acc["device_id"], cfg)
            if not token:
                print(f"  {C.R}Login failed{C.END}", flush=True)
                continue
            print("  Logged in", flush=True)
            print(f"  Balance: {get_balance(session, token, suid, acc['device_id'], phone)}", flush=True)
            bind_ans = input(f"  {C.C}Bind a new GCash? [y/n] (n): {C.END}").strip().lower()
            gcash = None
            if bind_ans in ("y", "yes"):
                gcash = input(f"  {C.C}GCash number to bind: {C.END}").strip()
                if not gcash:
                    print(f"  {C.R}No number{C.END}")
                    continue
                print(f"  Binding {normalize_phone(gcash)}. OTP on account, then OTP on this GCash.", flush=True)
                bound = bind_gcash(session, token, suid, acc["device_id"], phone, gcash)
                if not bound:
                    print(f"  {C.R}Bind failed{C.END}")
                    continue
                print(f"  {C.G}Bound {bound[1]}{C.END}")
            amount = input(f"  {C.C}Amount (50, 100, 150...): {C.END}").strip() or "50"
            try:
                amount = int(amount)
            except Exception:
                print(f"  {C.R}Bad amount{C.END}")
                continue
            withdraw_one(session, token, suid, acc["device_id"], phone, gcash, amount)
        except Exception as e:
            print(f"  {C.R}Withdraw error: {e}{C.END}", flush=True)

def print_menu():
    print(f"""
{C.M}========================================================
  {C.BOLD}{C.W}JUSTINE POGI{C.END}{C.M}
  {C.C}PTGaming Auto Tools{C.M}
========================================================{C.END}

  {C.G}[1]{C.END} Register (manual)
  {C.G}[2]{C.END} CypherLink Auto Register
  {C.G}[3]{C.END} Deposit (depo.txt)
  {C.G}[4]{C.END} Check + Claim all
  {C.G}[5]{C.END} Mutual Invite + Claim
  {C.G}[6]{C.END} Re-login (retoken.txt)
  {C.G}[7]{C.END} Edit config
  {C.G}[8]{C.END} Exit
  {C.G}[9]{C.END} Baccarat Cross-Bet (2 accounts)
  {C.G}[10]{C.END} Baccarat Merge (multi + max balance)
  {C.G}[11]{C.END} GCash Withdraw
  {C.G}[12]{C.END} Turnover Clear (Golden Empire)

""")

def get_hwid():
    import platform
    import subprocess
    parts = []
    try:
        if platform.system() == "Windows":
            for cmd in [
                "wmic csproduct get uuid",
                "wmic baseboard get serialnumber",
                "wmic diskdrive get serialnumber",
            ]:
                try:
                    out = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, timeout=5).decode(errors="ignore")
                    val = "".join(out.split()[1:]) if len(out.split()) > 1 else ""
                    if val and val.lower() not in ("none", "to be filled by o.e.m.", "default string"):
                        parts.append(val)
                except Exception:
                    pass
        else:
            try:
                out = subprocess.check_output("cat /etc/machine-id", shell=True, timeout=5).decode().strip()
                if out:
                    parts.append(out)
            except Exception:
                pass
    except Exception:
        pass
    if not parts:
        parts.append(platform.node() + platform.machine())
    raw = "|".join(parts)
    return hashlib.md5(raw.encode()).hexdigest()[:16]

ALLOWLIST_URL = "https://raw.githubusercontent.com/tektekthird-svg/ptallow/main/allowhwid"

def check_hwid():
    hwid = get_hwid()
    print(f"{C.C}HWID: {hwid}{C.END}")
    try:
        r = requests.get(ALLOWLIST_URL, timeout=10)
        if r.status_code != 200:
            print(f"{C.R}Allowlist unreachable (HTTP {r.status_code}). Make sure the repo is public and the file exists.{C.END}")
            return False
        allowed = {line.strip().lower() for line in r.text.splitlines() if line.strip() and not line.startswith("#")}
        if hwid.lower() in allowed:
            print(f"{C.G}Activated.{C.END}")
            return True
        print(f"{C.R}Not activated. Send this HWID to the owner: {hwid}{C.END}")
        return False
    except Exception as e:
        print(f"{C.R}Activation check failed: {e}{C.END}")
        return False

VERSION = "1.0.0"
VERSION_URL = "https://raw.githubusercontent.com/tektekthird-svg/ptallow/main/version.txt"
UPDATE_URL = "https://raw.githubusercontent.com/tektekthird-svg/ptallow/main/justine_pogi.py"  # or .exe raw if you host the built exe

def check_update():
    try:
        r = requests.get(VERSION_URL, timeout=8)
        if r.status_code != 200:
            return
        remote = r.text.strip()
        if remote and remote != VERSION:
            print(f"{C.Y}Update available: {VERSION} -> {remote}{C.END}")
            ans = input(f"{C.C}Update now? (y/n): {C.END}").strip().lower()
            if ans in ("y", "yes"):
                print(f"  Downloading...")
                ur = requests.get(UPDATE_URL, timeout=30)
                if ur.status_code == 200:
                    # For script: overwrite current file. For exe: save as new and relaunch.
                    target = "justine_pogi_new.py"
                    with open(target, "wb") as f:
                        f.write(ur.content)
                    print(f"{C.G}Downloaded {target}. Replace your file and restart.{C.END}")
                    input("Press Enter to exit...")
                    raise SystemExit
                else:
                    print(f"{C.R}Download failed ({ur.status_code}){C.END}")
    except Exception as e:
        print(f"  Update check skipped: {e}")

def ensure_files():
    files = [
        ACCOUNTS_FILE,
        DEPOT_FILE,
        TOKENS_FILE,
        RETOKEN_FILE,
        INVITE_FILE,
        PROXIES_FILE,
        WINNER_FILE,
        LOG_FILE,
    ]
    for f in files:
        if not os.path.exists(f):
            open(f, "a", encoding="utf-8").close()
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
    os.makedirs(QR_FOLDER, exist_ok=True)
    os.makedirs(SESSIONS_DIR, exist_ok=True)

def main():
    ensure_files()
    check_update()
    if not check_hwid():
        input("Press Enter to exit...")
        return
    cfg = load_config()
    while True:
        try:
            print_menu()
            c = input(f"{C.Y}Select: {C.END}").strip()
            if c == "1":
                run_register_mode(cfg)
            elif c == "2":
                run_cypherlink_register(cfg)
            elif c == "3":
                run_deposit_mode(cfg)
            elif c == "4":
                check_and_claim_all(cfg)
            elif c == "5":
                mutual_invite(cfg)
            elif c == "6":
                run_relogin(cfg)
            elif c == "7":
                print(cfg)
                amt = input(f"{C.C}Deposit amount [{cfg['deposit_amount']}]: {C.END}").strip()
                if amt:
                    cfg["deposit_amount"] = int(amt)
                save_config(cfg)
            elif c == "8":
                print(f"{C.G}Bye.{C.END}")
                break
            elif c == "9":
                run_baccarat_crossbet(cfg)
            elif c == "10":
                run_baccarat_merge(cfg)
            elif c == "11":
                run_withdraw(cfg)
            elif c == "12":
                run_turnover_clear(cfg)
            else:
                print(f"{C.R}Invalid{C.END}")
        except KeyboardInterrupt:
            print(f"\n{C.Y}Returning to menu...{C.END}")
            continue

if __name__ == "__main__":
    main()
