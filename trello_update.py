#!/usr/bin/env python3
import os
import time
import requests
import json
from pathlib import Path
import subprocess
from datetime import datetime

TRELLO_KEY = os.environ.get("TRELLO_KEY")
TRELLO_TOKEN = os.environ.get("TRELLO_TOKEN")
BOARD_ID = os.environ.get("BOARD_ID")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")

if not (TRELLO_KEY and TRELLO_TOKEN and BOARD_ID):
    raise SystemExit("ERRO: faltam variáveis de ambiente (TRELLO_KEY, TRELLO_TOKEN, BOARD_ID)")

REPO_DIR = Path('.').resolve()
JSON_FILE = REPO_DIR / "trello.json"

_RETRYABLE = {429, 500, 502, 503, 504}
_MAX_RETRIES = 4
_TIMEOUT = 60  # segundos

def get_board() -> dict:
    url = f"https://api.trello.com/1/boards/{BOARD_ID}"
    params = {
        "key": TRELLO_KEY,
        "token": TRELLO_TOKEN,
        "lists": "all",
        "cards": "all",
        "card_fields": "all",
        "fields": "all",
        "members": "all",
        "labels": "all",
        "label_fields": "all",
    }
    for attempt in range(_MAX_RETRIES):
        try:
            r = requests.get(url, params=params, timeout=_TIMEOUT)
        except requests.exceptions.Timeout:
            wait = 2 ** attempt * 10
            print(f"Timeout na tentativa {attempt + 1}, aguardando {wait}s…")
            time.sleep(wait)
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code in _RETRYABLE and attempt < _MAX_RETRIES - 1:
            wait = 2 ** attempt * 10
            print(f"Erro {r.status_code} na tentativa {attempt + 1}, aguardando {wait}s…")
            time.sleep(wait)
            continue
        print(f"Erro ao baixar do Trello: {r.status_code} -> {r.text}")
        r.raise_for_status()
    raise SystemExit("ERRO: todas as tentativas falharam ao contactar a API do Trello")



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
