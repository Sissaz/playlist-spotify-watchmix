"""
Atualiza SEMPRE a mesma playlist (Watch Mix) com faixas aleatórias
das Liked Songs para sincronizar com o Apple Watch.

.env necessário (criado/atualizado automaticamente na 1ª execução):
CLIENT_ID=...
CLIENT_SECRET=...
REDIRECT_URI=http://127.0.0.1:8888/callback
REFRESH_TOKEN=...        # preenchido depois que você autorizar o app
PLAYLIST_ID=...          # ID fixo da sua Watch Mix
"""

import os, random, time, threading, requests, webbrowser
from datetime import date
from flask import Flask, request, redirect
from werkzeug.serving import make_server
from dotenv import load_dotenv, dotenv_values, set_key, find_dotenv

# ───────────────────────────── 1. CONFIG ──────────────────────────────
TARGET_SIZE   = 30
PLAYLIST_NAME = "Watch Mix"
SCOPES        = "user-library-read playlist-modify-private"

load_dotenv()  # lê .env existente (se houver)

CLIENT_ID     = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
REDIRECT_URI  = os.getenv("REDIRECT_URI")
FIXED_PL_ID   = os.getenv("PLAYLIST_ID")

SPOTIFY_SAVED = "https://api.spotify.com/v1/me/tracks"
PL_URL        = "https://api.spotify.com/v1/playlists/{pid}/tracks"
CREATE_PL_URL = "https://api.spotify.com/v1/users/{uid}/playlists"

# ─────────────── 2. utilitário p/ gravar REFRESH_TOKEN ───────────────
def gravar_refresh_token(novo_token: str):
    """Insere ou substitui REFRESH_TOKEN no .env localizado no cwd."""
    if not novo_token:  # às vezes o Spotify não devolve de novo
        return
    env_path = find_dotenv(usecwd=True) or ".env"
    # garante que o arquivo exista
    if not os.path.isfile(env_path):
        open(env_path, "w").close()

    atual = dotenv_values(env_path).get("REFRESH_TOKEN")
    if atual == novo_token:
        return  # nada a mudar

    set_key(env_path, "REFRESH_TOKEN", novo_token)
    print(f"🔑  REFRESH_TOKEN salvo/atualizado em '{env_path}'")

# ────────────────────── 3. Infra de OAuth local ───────────────────────
app, auth_code = Flask(__name__), None
class ServerThread(threading.Thread):
    def __init__(self, app): super().__init__(); self.server = make_server('127.0.0.1', 8888, app)
    def run(self): self.server.serve_forever()
    def shutdown(self): self.server.shutdown()

@app.route('/callback')
def callback():
    global auth_code; auth_code = request.args.get('code'); return redirect("/success")
@app.route('/success')
def success(): return "<h3>Autorizado ✔ &nbsp;Pode fechar.<script>window.close()</script>"

def post_token(data):
    r = requests.post("https://accounts.spotify.com/api/token", data=data,
                      headers={"Content-Type":"application/x-www-form-urlencoded"})
    r.raise_for_status(); return r.json()

def gerar_token():
    global auth_code
    url = (f"https://accounts.spotify.com/authorize?response_type=code"
           f"&client_id={CLIENT_ID}&scope={SCOPES.replace(' ', '%20')}"
           f"&redirect_uri={REDIRECT_URI}")
    webbrowser.open(url); st = ServerThread(app); st.start()
    while auth_code is None: time.sleep(0.1)

    tk = post_token({"grant_type":"authorization_code","code":auth_code,
                     "redirect_uri":REDIRECT_URI,"client_id":CLIENT_ID,"client_secret":CLIENT_SECRET})
    st.shutdown()
    access, refresh = tk["access_token"], tk.get("refresh_token")
    gravar_refresh_token(refresh)
    return access, refresh

def renovar_token(refresh):
    tk = post_token({"grant_type":"refresh_token","refresh_token":refresh,
                     "client_id":CLIENT_ID,"client_secret":CLIENT_SECRET})
    return tk["access_token"], tk.get("refresh_token", refresh)

def sp_get(url, headers):
    r = requests.get(url, headers=headers); r.raise_for_status(); return r.json()

# ─────────────────────── 4. Helpers de playlist ───────────────────────
def obter_playlist_id(headers, user_id):
    """Devolve FIXED_PL_ID se existir; senão encontra por nome ou cria."""
    if FIXED_PL_ID:
        return FIXED_PL_ID
    url = f"https://api.spotify.com/v1/users/{user_id}/playlists?limit=50"
    while url:
        data = sp_get(url, headers)
        for pl in data["items"]:
            if pl["name"] == PLAYLIST_NAME:
                return pl["id"]
        url = data.get("next")
    body = {"name": PLAYLIST_NAME, "public": False,
            "description": "Gerada automaticamente para Apple Watch"}
    r = requests.post(CREATE_PL_URL.format(uid=user_id), json=body, headers=headers)
    r.raise_for_status(); return r.json()["id"]

def substituir_faixas(headers, pid, uris):
    # PUT sobrescreve a playlist (máx 100 por requisição)
    r = requests.put(PL_URL.format(pid=pid), json={"uris": uris[:100]}, headers=headers)
    r.raise_for_status()
    for i in range(100, len(uris), 100):
        r = requests.post(PL_URL.format(pid=pid), json={"uris": uris[i:i+100]}, headers=headers)
        r.raise_for_status()

# ──────────────────────────── 5. Main ────────────────────────────────
def main():
    global REFRESH_TOKEN
    if not CLIENT_ID or not CLIENT_SECRET:
        print("⚠️  Configure CLIENT_ID e CLIENT_SECRET no .env"); return

    token, REFRESH_TOKEN = (renovar_token(REFRESH_TOKEN) if REFRESH_TOKEN else gerar_token())
    headers = {"Authorization": f"Bearer {token}"}
    user_id = sp_get("https://api.spotify.com/v1/me", headers)["id"]

    # busca likes
    uris, url = [], SPOTIFY_SAVED + "?limit=50"
    while url:
        data = sp_get(url, headers)
        uris += [item["track"]["uri"] for item in data["items"]]
        url = data.get("next")
    if not uris:
        print("Nenhuma track curtida encontrada."); return

    sample = random.sample(uris, min(TARGET_SIZE, len(uris)))
    pid    = obter_playlist_id(headers, user_id)
    substituir_faixas(headers, pid, sample)

    print(f"✅  '{PLAYLIST_NAME}' atualizada ({len(sample)} faixas · {date.today()}). ID: {pid}")

if __name__ == "__main__":
    main()
