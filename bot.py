import os, json, time, requests, websocket

TOKEN = os.environ["DISCORD_USER_TOKEN"]
GUILD_ID = "1121177632185258108"
CHANNEL_ID = "1136760078964363387"
COMMAND = os.environ.get("COMMAND", "daily")

API = "https://discord.com/api/v9"
HEADERS = {"Authorization": TOKEN, "Content-Type": "application/json"}

def get_session_id():
    ws = websocket.create_connection("wss://gateway.discord.gg/?v=9&encoding=json")
    hello = json.loads(ws.recv())
    ws.send(json.dumps({"op": 2, "d": {"token": TOKEN, "capabilities": 16381,
        "properties": {"os": "Windows", "browser": "Chrome", "device": ""}, "compress": False}}))
    sid = None
    deadline = time.time() + 20
    while time.time() < deadline:
        msg = json.loads(ws.recv())
        if msg.get("t") == "READY":
            sid = msg["d"]["session_id"]
            break
    ws.close()
    return sid

def discover(name):
    r = requests.get(f"{API}/channels/{CHANNEL_ID}/application-commands/search",
        headers=HEADERS, params={"type": 1, "query": name, "limit": 10, "include_applications": "true"})
    if r.status_code != 200:
        print(f"kesif hatasi {r.status_code}: {r.text[:200]}"); return None
    for c in r.json().get("application_commands", []):
        if c.get("name") == name:
            return {"app": c["application_id"], "id": c["id"], "ver": c["version"], "name": c["name"]}
    print(f"/{name} komutu bulunamadi"); return None

def trigger(cmd, sid):
    nonce = str(int(time.time() * 1000) * 4096)
    payload = {"type": 2, "application_id": cmd["app"], "guild_id": GUILD_ID,
        "channel_id": CHANNEL_ID, "session_id": sid,
        "data": {"version": cmd["ver"], "id": cmd["id"], "name": cmd["name"],
            "type": 1, "options": [], "attachments": []}, "nonce": nonce}
    r = requests.post(f"{API}/interactions", headers=HEADERS, json=payload)
    if r.status_code in (200, 204):
        print(f"/{cmd['name']} tetiklendi"); return True
    print(f"/{cmd['name']} tetik hatasi {r.status_code}: {r.text[:200]}"); return False

def main():
    sid = get_session_id()
    if not sid:
        print("session alinamadi"); return
    cmd = discover(COMMAND)
    if not cmd:
        return
    trigger(cmd, sid)

if __name__ == "__main__":
    main()
