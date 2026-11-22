#!/usr/bin/env python3
"""Interactive CLI for the Cue Agent System backend."""

import json
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
HISTORY_FILE = Path.home() / ".cue_history.json"
MAX_HISTORY = 50
BANNER = (
    "\n" + "=" * 60
    + "\n\U0001F3AF Cue Agent System CLI"
    + "\nCommands: /history, /clear, /tools, /exit"
    + "\n" + "=" * 60 + "\n"
)


def load_history() -> list[dict]:
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def save_history(history: list[dict]) -> None:
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[-MAX_HISTORY:], f)


def handle_command(cmd: str, history: list[dict]) -> tuple[bool, list[dict]]:
    """Handle a slash command. Returns (should_continue, new_history)."""
    if cmd in ("/exit", "/quit"):
        return False, history

    if cmd == "/history":
        print("\nHistory:")
        for i, m in enumerate(history[-10:], 1):
            print(f"{i}. [{m.get('role', '?')}] {m.get('content', '')[:100]}")
        return True, history

    if cmd == "/clear":
        save_history([])
        print("Cleared.")
        return True, []

    if cmd == "/tools":
        try:
            resp = requests.get(f"{BASE_URL}/api/tools", timeout=5)
            if resp.ok:
                print("\nTools:", list(resp.json().get("tools", {}).keys()))
            else:
                print(f"\nBackend error: HTTP {resp.status_code}")
        except requests.RequestException:
            print("Backend unreachable.")
        return True, history

    print(f"Unknown command: {cmd}")
    return True, history


def send_message(message: str, history: list[dict]) -> list[dict]:
    try:
        resp = requests.post(
            f"{BASE_URL}/api/chat/default",
            json={"message": message, "use_tools": True},
            timeout=30,
        )
    except requests.ConnectionError:
        print("Cannot connect to backend.\n")
        return history
    except requests.RequestException as exc:
        print(f"Error: {exc}\n")
        return history

    if not resp.ok:
        print(f"Error: {resp.json().get('detail', 'Unknown')}\n")
        return history

    data = resp.json()
    reply = data.get("reply", "")
    provider = data.get("provider", "?")
    print(f"cue ({provider}) > {reply}\n")

    history.extend(
        [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply, "provider": provider},
        ]
    )
    save_history(history)
    return history


def main() -> None:
    print(BANNER)
    history = load_history()

    while True:
        try:
            message = input("you > ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not message:
            continue

        if message.startswith("/"):
            should_continue, history = handle_command(message.lower(), history)
            if not should_continue:
                break
            continue

        history = send_message(message, history)


if __name__ == "__main__":
    main()
