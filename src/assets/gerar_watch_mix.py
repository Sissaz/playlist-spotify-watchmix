import os, random, time, threading, requests, webbrowser
from datetime import date
from flask import Flask, request, redirect
from werkzeug.serving import make_server
from dotenv import load_dotenv

# ---------- Suporte a idiomas ----------

TEXTOS = {
    "pt": {
        "sem_env": "⚙️  Arquivo com suas credenciais do Spotify não encontrado. Vamos criá-lo agora.",
        "criado_env": "✅ .env criado com sucesso.\n",
        "ambiente_ci": "📦 Ambiente CI detectado. Pulando criação do .env.",
        "nenhuma_track": "Nenhuma track curtida.",
        "playlist_existente": "💾 Playlist já existente encontrada. ID salvo no .env",
        "playlist_criada": "🆕 Playlist criada e ID salvo no .env",
        "playlist_nao_existe": "Playlist ID {pid} não existe. Remova PLAYLIST_ID do .env e rode de novo.",
        "refresh_salvo": "\n✅ Refresh Token salvo automaticamente no .env. Por favor, aguarde o script finalizar o job.",
        "configure_id": "Configure CLIENT_ID e CLIENT_SECRET.",
        "playlist_atualizada": "✅  '{nome}' atualizada ({qtd} faixas · {data}). ID: {pid}",
        "escolha_idioma": "🌐 Selecione o idioma / Select language:\n1 - Português\n2 - English\n>> ",
        "digite_client_id": "Digite seu CLIENT_ID: ",
        "digite_client_secret": "Digite seu CLIENT_SECRET: ",
        "digite_redirect_uri": "Digite seu REDIRECT_URI (ex: http://127.0.0.1:8888/callback): ",
        "playlist_atualizada": "✅  '{nome}' atualizada ({quantidade} faixas · {data}). ID: {id}"

        
    },
    "en": {
        "sem_env": "⚙️  .env file with your Spotify credentials not found. Let's create it now.",
        "criado_env": "✅ .env created successfully.\n",
        "ambiente_ci": "📦 CI environment detected. Skipping .env creation.",
        "nenhuma_track": "No liked tracks found.",
        "playlist_existente": "💾 Playlist already exists. ID saved to .env",
        "playlist_criada": "🆕 Playlist created and ID saved to .env",
        "playlist_nao_existe": "Playlist ID {pid} does not exist. Remove PLAYLIST_ID from .env and rerun.",
        "refresh_salvo": "\n✅ Refresh Token automatically saved to .env. Please wait for the job to finish.",
        "configure_id": "Please configure CLIENT_ID and CLIENT_SECRET.",
        "playlist_atualizada": "✅  '{nome}' updated ({qtd} tracks · {data}). ID: {pid}",
        "escolha_idioma": "🌐 Selecione o idioma / Select language:\n1 - Português\n2 - English\n>> ",
        "digite_client_id": "Enter your CLIENT_ID: ",
        "digite_client_secret": "Enter your CLIENT_SECRET: ",
        "digite_redirect_uri": "Enter your REDIRECT_URI (e.g., http://127.0.0.1:8888/callback): ",
        "playlist_atualizada": "✅  '{nome}' updated ({quantidade} tracks · {data}). ID: {id}"
    }
}

# Define variável global para textos
texto = TEXTOS["pt"]

def selecionar_idioma():
    global texto

    # Ignora seleção se estiver em ambiente de CI (como GitHub Actions)
    if os.getenv("GITHUB_ACTIONS") == "true":
        print("📦 Ambiente CI detectado. Idioma padrão: Português.")
        return

    while True:
        escolha = input(TEXTOS["pt"]["escolha_idioma"]).strip()
        if escolha == "1":
            texto = TEXTOS["pt"]
            break
        elif escolha == "2":
            texto = TEXTOS["en"]
            break
        else:
            print("❌ Entrada inválida. Digite apenas 1 ou 2. / ❌ Invalid input. Please enter only 1 or 2.")


# ---------- Função para garantir que o .env exista ----------
def garantir_env():
    env_path = ".env"

    # Evita erro em ambientes não interativos como GitHub Actions
    if os.getenv("GITHUB_ACTIONS") == "true":
        print(texto["ambiente_ci"])
        return

    if not os.path.exists(env_path):
        print(texto["sem_env"])
        client_id     = input(texto["digite_client_id"]).strip()
        client_secret = input(texto["digite_client_secret"]).strip()
        redirect_uri  = input(texto["digite_redirect_uri"]).strip()

        with open(env_path, "w") as f:
            f.write(f"CLIENT_ID={client_id}\n")
            f.write(f"CLIENT_SECRET={client_secret}\n")
            f.write(f"REDIRECT_URI={redirect_uri}\n")

        print(texto["criado_env"])

# ---------- CONFIG ----------

garantir_env()
load_dotenv()

TARGET_SIZE   = 30
PLAYLIST_NAME = "Watch Mix"
SCOPES        = "user-library-read playlist-modify-private"

CLIENT_ID     = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
REDIRECT_URI  = os.getenv("REDIRECT_URI")
FIXED_PL_ID   = os.getenv("PLAYLIST_ID")

SPOTIFY_SAVED = "https://api.spotify.com/v1/me/tracks"
PL_URL        = "https://api.spotify.com/v1/playlists/{pid}/tracks"
CREATE_PL_URL = "https://api.spotify.com/v1/users/{uid}/playlists"

# ---------- OAuth infra ----------
app, auth_code = Flask(__name__), None
class ServerThread(threading.Thread):
    def __init__(self, app): super().__init__(); self.server = make_server('127.0.0.1', 8888, app)
    def run(self): self.server.serve_forever()
    def shutdown(self): self.server.shutdown()

@app.route('/callback')
def callback():
    global auth_code
    auth_code = request.args.get('code')
    return redirect("/success")

@app.route('/success')
def success():
    return "<h3>Autorizado ✔ &nbsp;Pode fechar.<script>window.close()</script>"

def post_token(data):
    r = requests.post("https://accounts.spotify.com/api/token", data=data,
                      headers={"Content-Type":"application/x-www-form-urlencoded"})
    r.raise_for_status()
    return r.json()

def gerar_token():
    global auth_code
    url = (f"https://accounts.spotify.com/authorize?response_type=code"
           f"&client_id={CLIENT_ID}&scope={SCOPES.replace(' ', '%20')}"
           f"&redirect_uri={REDIRECT_URI}")
    webbrowser.open(url)
    st = ServerThread(app); st.start()
    while auth_code is None: time.sleep(0.1)
    tk = post_token({"grant_type":"authorization_code","code":auth_code,
                     "redirect_uri":REDIRECT_URI,"client_id":CLIENT_ID,"client_secret":CLIENT_SECRET})
    st.shutdown()
    access, refresh = tk["access_token"], tk.get("refresh_token")

    # Atualiza o .env automaticamente com o refresh token
    with open(".env", "a") as f:
        f.write(f"REFRESH_TOKEN={refresh}\n")
    print(texto["refresh_salvo"])

    return access, refresh

def renovar_token(refresh):
    tk = post_token({"grant_type":"refresh_token","refresh_token":refresh,
                     "client_id":CLIENT_ID,"client_secret":CLIENT_SECRET})
    return tk["access_token"], tk.get("refresh_token", refresh)

def sp_get(url, headers):
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()

# ---------- Playlist helpers ----------
def obter_playlist_id(headers, user_id):
    global FIXED_PL_ID

    # Se já estiver no .env, retorna
    if FIXED_PL_ID:
        return FIXED_PL_ID

    # Tenta encontrar por nome
    url = f"https://api.spotify.com/v1/users/{user_id}/playlists?limit=50"
    while url:
        data = sp_get(url, headers)
        for pl in data["items"]:
            if pl["name"].lower() == PLAYLIST_NAME.lower():
                pid = pl["id"]
                atualizar_env("PLAYLIST_ID", pid)
                FIXED_PL_ID = pid  # Atualiza a variável global também
                print(texto["playlist_existente"])
                return pid
        url = data.get("next")

    # Se não existir, cria a playlist
    body = {
        "name": PLAYLIST_NAME,
        "public": False,
        "description": "Gerada automaticamente para Apple Watch"
    }
    r = requests.post(CREATE_PL_URL.format(uid=user_id), json=body, headers=headers)
    r.raise_for_status()
    pid = r.json()["id"]

    atualizar_env("PLAYLIST_ID", pid)
    FIXED_PL_ID = pid
    print(texto["playlist_criada"])
    return pid

def substituir_faixas(headers, pid, uris):
    chk = requests.get(f"https://api.spotify.com/v1/playlists/{pid}", headers=headers)
    if chk.status_code == 404:
        raise ValueError(f"Playlist ID {pid} não existe. Remova PLAYLIST_ID do .env e rode de novo.")
    chk.raise_for_status()
    r = requests.put(PL_URL.format(pid=pid), json={"uris": uris[:100]}, headers=headers)
    r.raise_for_status()
    for i in range(100, len(uris), 100):
        r = requests.post(PL_URL.format(pid=pid), json={"uris": uris[i:i+100]}, headers=headers)
        r.raise_for_status()


def atualizar_env(chave, valor):
    """Adiciona ou atualiza uma chave no arquivo .env"""
    env_path = ".env"
    linhas = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            linhas = f.readlines()

    chave_encontrada = False
    for i, linha in enumerate(linhas):
        if linha.strip().startswith(f"{chave}="):
            linhas[i] = f"{chave}={valor}\n"
            chave_encontrada = True
            break

    if not chave_encontrada:
        linhas.append(f"{chave}={valor}\n")

    with open(env_path, "w") as f:
        f.writelines(linhas)


# ---------- Main ----------
def main():
    selecionar_idioma()
    garantir_env()
    load_dotenv()

    global REFRESH_TOKEN
    if not CLIENT_ID or not CLIENT_SECRET:
        print(texto["configure_id"])

    token, REFRESH_TOKEN = (renovar_token(REFRESH_TOKEN) if REFRESH_TOKEN else gerar_token())
    headers = {"Authorization": f"Bearer {token}"}
    user_id = sp_get("https://api.spotify.com/v1/me", headers)["id"]

    uris, url = [], SPOTIFY_SAVED + "?limit=50"
    while url:
        data = sp_get(url, headers)
        uris += [i["track"]["uri"] for i in data["items"]]
        url = data.get("next")
    if not uris: 
        print(texto["nenhuma_track"]); return

    sample = random.sample(uris, min(TARGET_SIZE, len(uris)))
    pid    = obter_playlist_id(headers, user_id)
    substituir_faixas(headers, pid, sample)

    print(texto["playlist_atualizada"].format(
    nome=PLAYLIST_NAME,
    quantidade=len(sample),
    data=date.today(),
    id=pid
))


if __name__ == "__main__":
    main()
