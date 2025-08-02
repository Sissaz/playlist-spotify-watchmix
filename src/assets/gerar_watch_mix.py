"""
Atualiza SEMPRE a mesma playlist (Watch Mix) com faixas aleatórias
das Liked Songs para sincronizar com o Apple Watch.

.env necessário:
CLIENT_ID=...
CLIENT_SECRET=...
REDIRECT_URI=http://localhost:8888/callback
REFRESH_TOKEN=...            # obtido após 1ª execução
PLAYLIST_ID=7gAsZNmkP00WpXTJMCA12w   # ID fixo da sua Watch Mix
"""

import os, random, time, threading, requests, webbrowser
from datetime import date
from flask import Flask, request, redirect
from werkzeug.serving import make_server
from dotenv import load_dotenv
load_dotenv()

# ---------- CONFIG ----------
TARGET_SIZE   = 30
PLAYLIST_NAME = "Watch Mix"
SCOPES        = "user-library-read playlist-modify-private"

CLIENT_ID     = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
REDIRECT_URI  = "http://localhost:8888/callback"
FIXED_PL_ID   = os.getenv("PLAYLIST_ID")      # ← já está no seu .env

SPOTIFY_SAVED = "https://api.spotify.com/v1/me/tracks"
PL_URL        = "https://api.spotify.com/v1/playlists/{pid}/tracks"
CREATE_PL_URL = "https://api.spotify.com/v1/users/{uid}/playlists"

# ---------- OAuth infra ----------
app, auth_code = Flask(__name__), None
class ServerThread(threading.Thread):
    def __init__(self, app): super().__init__(); self.server = make_server('localhost', 8888, app)
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
    print("\nAccess Token :", access)
    print("Refresh Token:", refresh)
    print(">>> copie e cole no .env como REFRESH_TOKEN <<<\n")
    return access, refresh

def renovar_token(refresh):
    tk = post_token({"grant_type":"refresh_token","refresh_token":refresh,
                     "client_id":CLIENT_ID,"client_secret":CLIENT_SECRET})
    return tk["access_token"], tk.get("refresh_token", refresh)

def sp_get(url, headers):
    r = requests.get(url, headers=headers); r.raise_for_status(); return r.json()

# ---------- Playlist helpers ----------
def obter_playlist_id(headers, user_id):
    """Devolve o ID fixo se estiver no .env;
       senão procura por nome; cria se não existir."""
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
    # verifica se o ID ainda existe
    chk = requests.get(f"https://api.spotify.com/v1/playlists/{pid}", headers=headers)
    if chk.status_code == 404:
        raise ValueError(f"Playlist ID {pid} não existe. Remova PLAYLIST_ID do .env e rode de novo.")
    chk.raise_for_status()
    # PUT substitui todo o conteúdo
    r = requests.put(PL_URL.format(pid=pid), json={"uris": uris[:100]}, headers=headers)
    r.raise_for_status()
    for i in range(100, len(uris), 100):
        r = requests.post(PL_URL.format(pid=pid), json={"uris": uris[i:i+100]}, headers=headers)
        r.raise_for_status()


# ---------- Main ----------
def main():
    global REFRESH_TOKEN
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Configure CLIENT_ID e CLIENT_SECRET."); return

    token, REFRESH_TOKEN = (renovar_token(REFRESH_TOKEN) if REFRESH_TOKEN else gerar_token())
    headers = {"Authorization": f"Bearer {token}"}
    user_id = sp_get("https://api.spotify.com/v1/me", headers)["id"]

    uris, url = [], SPOTIFY_SAVED + "?limit=50"
    while url:
        data = sp_get(url, headers); uris += [i["track"]["uri"] for i in data["items"]]
        url = data.get("next")
    if not uris:
        print("Nenhuma track curtida."); return

    sample = random.sample(uris, min(TARGET_SIZE, len(uris)))
    pid    = obter_playlist_id(headers, user_id)
    substituir_faixas(headers, pid, sample)

    print(f"✅  '{PLAYLIST_NAME}' atualizada ({len(sample)} faixas · {date.today()}). ID: {pid}")

if __name__ == "__main__":
    main()
