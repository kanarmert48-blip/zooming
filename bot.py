import os, json, time, threading, requests, websocket

TOKEN = os.environ["DISCORD_USER_TOKEN"].strip()
GUILD_ID = "1121177632185258108"
CHANNEL_ID = "1136760078964363387"
COMMANDS = [c.strip() for c in os.environ.get("COMMANDS", "work,crime,daily").split(",") if c.strip()]

API = "https://discord.com/api/v9"
HEADERS = {"Authorization": TOKEN, "Content-Type": "application/json"}

state = {"seq": None, "alive": True}

def recv_json(ws):
    try:
        data = ws.recv()
    except Exception as e:
        print(f"baglanti kapandi: {e}")
        state["alive"] = False
        return None
    if not data:
        return None
    try:
        msg = json.loads(data)
    except Exception:
        return None
    if msg.get("s") is not None:
        state["seq"] = msg["s"]
    return msg

def heartbeat(ws, interval):
    while state["alive"]:
        time.sleep(interval)
        try:
            ws.send(json.dumps({"op": 1, "d": state["seq"]}))
        except Exception:
            state["alive"] = False
            return

def reader(ws):
    while state["alive"]:
        msg = recv_json(ws)
        if msg and msg.get("op") == 9:
            print("discord oturumu gecersiz sayildi")
            state["alive"] = False

def connect():
    ws = websocket.create_connection("wss://gateway.discord.gg/?v=9&encoding=json", timeout=30)
    hello = recv_json(ws)
    if not hello or hello.get("op") != 10:
        print("hello alinamadi"); return None, None
    interval = hello["d"]["heartbeat_interval"] / 1000
    threading.Thread(target=heartbeat, args=(ws, interval), daemon=True).start()
    ws.send(json.dumps({"op": 2, "d": {"token": TOKEN, "capabilities": 16381,
        "properties": {"os": "Windows", "browser": "Chrome", "device": ""}, "compress": False}}))
    deadline = time.time() + 30
    while time.time() < deadline and state["alive"]:
        msg = recv_json(ws)
        if not msg:
            continue
        if msg.get("t") == "READY":
            sid = msg["d"]["session_id"]
            threading.Thread(target=reader, args=(ws,), daemon=True).start()
            return ws, sid
        if msg.get("op") == 9:
            print("token gecersiz ya da oturum reddedildi"); return None, None
    print("READY gelmedi"); return None, None

def discover(name):
    r = requests.get(f"{API}/channels/{CHANNEL_ID}/application-commands/search",
        headers=HEADERS, params={"type": 1, "query": name, "limit": 10, "include_applications": "true"})
    if r.status_code != 200:
        print(f"/{name} kesif hatasi {r.status_code}: {r.text[:200]}"); return None
    for c in r.json().get("application_commands", []):
        if c.get("name") == name:
            return c
    print(f"/{name} bulunamadi"); return None

def trigger(c, sid):
    payload = {"type": 2, "application_id": c["application_id"], "guild_id": GUILD_ID,
        "channel_id": CHANNEL_ID, "session_id": sid,
        "data": {"version": c["version"], "id": c["id"], "name": c["name"],
            "type": 1, "options": [], "application_command": c, "attachments": []},
        "nonce": str(int(time.time() * 1000) << 22)}
    r = requests.post(f"{API}/interactions", headers=HEADERS, json=payload)
    if r.status_code in (200, 204):
        print(f"/{c['name']} tetiklendi")
    else:
        print(f"/{c['name']} hata {r.status_code}: {r.text[:200]}")

def main():
    ws, sid = connect()
    if not sid:
        raise SystemExit(1)
    print("baglanti tamam")
    for name in COMMANDS:
        c = discover(name)
        if c:
            trigger(c, sid)
        time.sleep(4)
    time.sleep(3)
    state["alive"] = False
    ws.close()

if __name__ == "__main__":
    main()
