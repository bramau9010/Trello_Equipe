#!/usr/bin/env python3
import os
import requests
import json
from pathlib import Path
import subprocess
from datetime import datetime

# Variáveis via env (serão providas pelo GitHub Actions como secrets)
TRELLO_KEY = os.environ.get("TRELLO_KEY")
TRELLO_TOKEN = os.environ.get("TRELLO_TOKEN")
BOARD_ID = os.environ.get("BOARD_ID")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")

if not (TRELLO_KEY and TRELLO_TOKEN and BOARD_ID):
    raise SystemExit("ERRO: faltam variáveis de ambiente (TRELLO_KEY, TRELLO_TOKEN, BOARD_ID)")

REPO_DIR = Path('.').resolve()
JSON_FILE = REPO_DIR / "trello.json"

def get_board():
    url = f"https://api.trello.com/1/boards/{BOARD_ID}"
    params = {
        "key": TRELLO_KEY,
        "token": TRELLO_TOKEN,
        "lists": "all",
        "cards": "all",
        "card_fields": "all",
        "fields": "all",
        "members": "all",
        "labels": "all",       # <-- add this
        "label_fields": "all"  # <-- optional, ensures full label details
    }
    r = requests.get(url, params=params)
    if r.status_code != 200:
        print(f"Erro ao baixar do Trello: {r.status_code} -> {r.text}")
        r.raise_for_status()
    return r.json()



def save_json(board_json):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(board_json, f, ensure_ascii=False, indent=2)
    print(f"Saved {JSON_FILE}")

def git_commit_and_push():
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if not status.stdout.strip():
        print("Nenhuma mudança para commitar.")
        return

    # configura autor (github-actions[bot])
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], check=True)

    subprocess.run(["git", "add", str(JSON_FILE)], check=True)
    commit_msg = f"Atualização Trello {datetime.utcnow().isoformat()}Z"
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
    subprocess.run(["git", "push", "origin", GITHUB_BRANCH], check=True)
    print("Push concluído.")

def main():
    board = get_board()
    save_json(board)
    git_commit_and_push()

if __name__ == "__main__":
    main()
