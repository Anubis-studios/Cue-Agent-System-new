#!/usr/bin/env python3
import requests, sys, json
from pathlib import Path

BASE = "http://localhost:8000"
HISTORY_FILE = Path.home() / ".cue_history.json"

def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f: return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w') as f: json.dump(history[-50:], f)

def main():
    print("\n" + "="*60 + "\n🎯 Cue Agent System CLI\nCommands: /history, /clear, /tools, /exit\n" + "="*60 + "\n")
    history = load_history()
    
    while True:
        try:
            msg = input("you > ").strip()
            if not msg: continue
            
            if msg.startswith("/"):
                cmd = msg.lower()
                if cmd in ["/exit", "/quit"]: break
                elif cmd == "/history":
                    print("\nHistory:")
                    for i, m in enumerate(history[-10:], 1): print(f"{i}. [{m.get('role','?')}] {m.get('content','')[:100]}")
                    continue
                elif cmd == "/clear": history = []; save_history(history); print("Cleared."); continue
                elif cmd == "/tools":
                    try:
                        r = requests.get(f"{BASE}/api/tools", timeout=5)
                        if r.ok: print("\nTools:", list(r.json().get("tools", {}).keys()))
                    except: print("Backend unreachable.")
                    continue
            
            try:
                r = requests.post(f"{BASE}/api/chat/default", json={"message": msg, "use_tools": True}, timeout=30)
                if r.ok:
                    d = r.json()
                    print(f"cue ({d.get('provider','?')}) > {d.get('reply','')}\n")
                    history.extend([{"role": "user", "content": msg}, {"role": "assistant", "content": d.get("reply",""), "provider": d.get("provider","")}])
                    save_history(history)
                else: print(f"Error: {r.json().get('detail','Unknown')}\n")
            except requests.exceptions.ConnectionError: print("Cannot connect to backend.\n")
            except Exception as e: print(f"Error: {e}\n")
                
        except (KeyboardInterrupt, EOFError): break

if __name__ == "__main__": main()
