import os, json, time, threading, requests, websocket

TOKEN = os.environ["DISCORD_USER_TOKEN"].strip()
GUILD_ID = "1121177632185258108"
CHANNEL_ID = "1136760078964363387"
ROB_TARGET = os.environ.get("ROB_TARGET", "").strip()

env_cmds = os.environ.get("COMMANDS", "")
if env_cmds:
    COMMANDS = [c.strip() for c in env_cmds.split(",") if c.strip()]
else:
    COMMANDS = ["work"]
    if time.gmtime().tm_hour % 4 == 0:
        COMMANDS.append("daily")

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

def load_index():
    r = requests.get(f"{API}/guilds/{GUILD_ID}/application-command-index", headers=HEADERS)
    if r.status_code != 200:
        print(f"index hatasi {r.status_code}: {r.text[:150]}")
        return []
    cmds = [c for c in r.json().get("application_commands", []) if c.get("type", 1) == 1]
    print(f"{len(cmds)} komut bulundu")
    return cmds

def pick_app(cmds):
    counts = {}
    for c in cmds:
        if c.get("name") in ("work", "crime", "daily", "rob"):
            counts[c["application_id"]] = counts.get(c["application_id"], 0) + 1
    if not counts:
        return None
    app = max(counts, key=counts.get)
    print(f"secilen bot: {app} ({counts[app]} komut eslesti)")
    return app

def build_options(c):
    if c["name"] != "rob":
        return []
    target = ROB_TARGET or c["application_id"]
    opt = next((o for o in c.get("options", []) if o.get("type") == 6), None)
    opt_name = opt["name"] if opt else "user"
    print(f"/rob hedefi: {target}")
    return [{"type": 6, "name": opt_name, "value": target}]

def trigger(c, sid):
    payload = {"type": 2, "application_id": c["application_id"], "guild_id": GUILD_ID,
        "channel_id": CHANNEL_ID, "session_id": sid,
        "data": {"version": c["version"], "id": c["id"], "name": c["name"],
            "type": 1, "options": build_options(c), "application_command": c, "attachments": []},
        "nonce": str(int(time.time() * 1000) << 22)}
    r = requests.post(f"{API}/interactions", headers=HEADERS, json=payload)
    if r.status_code in (200, 204):
        print(f"/{c['name']} tetiklendi")
    else:
        print(f"/{c['name']} hata {r.status_code}: {r.text[:200]}")

def main():
    print(f"bu calismada: {', '.join(COMMANDS)}")
    ws, sid = connect()
    if not sid:
        raise SystemExit(1)
    print("baglanti tamam")
    cmds = load_index()
    app = pick_app(cmds)
    for name in COMMANDS:
        c = next((x for x in cmds if x["name"] == name and x["application_id"] == app), None)
        if c:
            trigger(c, sid)
        else:
            print(f"/{name} bu botta yok")
        time.sleep(4)
    time.sleep(3)
    state["alive"] = False
    ws.close()

if __name__ == "__main__":
    main()
