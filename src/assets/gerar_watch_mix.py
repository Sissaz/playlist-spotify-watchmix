import os, random, re, subprocess, time, threading, base64, requests, webbrowser
from collections import defaultdict
from datetime import date
from flask import Flask, request, redirect
from werkzeug.serving import make_server
from dotenv import load_dotenv
from nacl import encoding, public

load_dotenv()

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

TARGET_SIZE     = 30
MAX_POR_ARTISTA = 1
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

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 5

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
    for tentativa in range(MAX_RETRIES + 1):
        r = requests.post("https://accounts.spotify.com/api/token", data=data,
                          headers={"Content-Type":"application/x-www-form-urlencoded"})
        if r.status_code not in RETRYABLE_STATUS or tentativa == MAX_RETRIES:
            break
        espera = float(r.headers.get("Retry-After", 2 ** tentativa))
        print(f"⚠️  {r.status_code} em /api/token — tentativa {tentativa + 1}/{MAX_RETRIES}, aguardando {espera:.0f}s...")
        time.sleep(espera)

    if not r.ok:
        print(f"❌ Spotify token error {r.status_code}: {r.text}")
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
    if refresh:
        atualizar_env("REFRESH_TOKEN", refresh)
        print(texto["refresh_salvo"])

    return access, refresh

def renovar_token(refresh):
    tk = post_token({"grant_type":"refresh_token","refresh_token":refresh,
                     "client_id":CLIENT_ID,"client_secret":CLIENT_SECRET})
    return tk["access_token"], tk.get("refresh_token", refresh)

def detectar_repo_git():
    """Descobre 'owner/repo' a partir do remote 'origin' do git local,
    para que o script funcione corretamente em forks (sem apontar para
    o repositório original)."""
    try:
        url = subprocess.check_output(
            ["git", "-c", "safe.directory=*", "remote", "get-url", "origin"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None
    m = re.search(r"github\.com[:/](.+?)(\.git)?$", url)
    return m.group(1) if m else None

def obter_token(refresh):
    """Tenta renovar o access token com o refresh token salvo. Se o Spotify
    recusar (token revogado/invalido), cai automaticamente para uma nova
    autorizacao interativa — exceto em CI, onde nao ha navegador disponivel
    para autorizar, e por isso o erro deve subir para falhar o job de forma
    visivel em vez de travar esperando um callback que nunca vai chegar."""
    if not refresh:
        if os.getenv("GITHUB_ACTIONS") == "true":
            raise RuntimeError(
                "REFRESH_TOKEN não configurado. Rode o script localmente uma "
                "vez para autorizar e gerar um token antes de usar o workflow."
            )
        return gerar_token()
    try:
        return renovar_token(refresh)
    except requests.exceptions.HTTPError:
        if os.getenv("GITHUB_ACTIONS") == "true":
            raise
        print("⚠️  Refresh Token invalido ou expirado. Iniciando nova autorização no navegador...")
        return gerar_token()

def atualizar_secret_github(nome_secret, valor):
    """Atualiza um secret do repositório no GitHub Actions via API REST,
    usando um PAT (GH_PAT) com permissão de leitura/escrita em Secrets."""
    pat  = os.getenv("GH_PAT")
    repo = os.getenv("GITHUB_REPOSITORY") or detectar_repo_git()
    if not pat or not repo:
        return False

    api = f"https://api.github.com/repos/{repo}/actions/secrets"
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
    }

    r = requests.get(f"{api}/public-key", headers=headers)
    r.raise_for_status()
    chave = r.json()

    public_key = public.PublicKey(chave["key"].encode(), encoding.Base64Encoder())
    encrypted  = public.SealedBox(public_key).encrypt(valor.encode())

    r = requests.put(f"{api}/{nome_secret}", headers=headers, json={
        "encrypted_value": base64.b64encode(encrypted).decode(),
        "key_id": chave["key_id"],
    })
    r.raise_for_status()
    return True

SECRETS_GITHUB = {
    "CLIENT_ID":     "SPOTIFY_CLIENT_ID",
    "CLIENT_SECRET": "SPOTIFY_CLIENT_SECRET",
    "REDIRECT_URI":  "SPOTIFY_REDIRECT_URI",
    "REFRESH_TOKEN": "SPOTIFY_REFRESH_TOKEN",
    "PLAYLIST_ID":   "PLAYLIST_ID",
    "GH_PAT":        "GH_PAT",
}

def bootstrap_secrets_github(valores):
    """Na primeira execução local com GH_PAT definido no .env, publica todos
    os secrets necessários no repositório do GitHub de uma vez — assim quem
    clona o repo não precisa criar nenhum secret manualmente na interface do
    GitHub, só rodar o script localmente uma vez."""
    if os.getenv("GITHUB_ACTIONS") == "true" or not os.getenv("GH_PAT"):
        return

    falhou = False
    for chave, valor in valores.items():
        if valor and not atualizar_secret_github(SECRETS_GITHUB[chave], valor):
            falhou = True

    if falhou:
        print("⚠️  Não foi possível publicar todos os secrets automaticamente no GitHub.")
    else:
        print("🔐 Secrets publicados automaticamente no repositório do GitHub. O workflow já pode rodar sem configuração manual.")

def sp_request(method, url, headers, **kwargs):
    for tentativa in range(MAX_RETRIES + 1):
        r = requests.request(method, url, headers=headers, **kwargs)
        if r.status_code not in RETRYABLE_STATUS or tentativa == MAX_RETRIES:
            return r

        espera = float(r.headers.get("Retry-After", 2 ** tentativa))
        print(f"⚠️  {r.status_code} em {url} — tentativa {tentativa + 1}/{MAX_RETRIES}, aguardando {espera:.0f}s...")
        time.sleep(espera)
    return r

def sp_get(url, headers):
    r = sp_request("GET", url, headers)
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
    r = sp_request("POST", CREATE_PL_URL.format(uid=user_id), headers, json=body)
    r.raise_for_status()
    pid = r.json()["id"]

    atualizar_env("PLAYLIST_ID", pid)
    FIXED_PL_ID = pid
    print(texto["playlist_criada"])
    return pid

def substituir_faixas(headers, pid, uris):
    chk = sp_request("GET", f"https://api.spotify.com/v1/playlists/{pid}", headers)
    if chk.status_code == 404:
        raise ValueError(f"Playlist ID {pid} não existe. Remova PLAYLIST_ID do .env e rode de novo.")
    chk.raise_for_status()
    r = sp_request("PUT", PL_URL.format(pid=pid), headers, json={"uris": uris[:100]})
    r.raise_for_status()
    for i in range(100, len(uris), 100):
        r = sp_request("POST", PL_URL.format(pid=pid), headers, json={"uris": uris[i:i+100]})
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


# ---------- Amostragem diversificada por artista ----------
def amostra_diversificada(faixas, tamanho, max_por_artista=MAX_POR_ARTISTA):
    """Sorteia até `tamanho` URIs, limitando quantas faixas do mesmo artista entram,
    e só repete artista se não houver artistas diferentes suficientes."""
    por_artista = defaultdict(list)
    for uri, artist_id in faixas:
        por_artista[artist_id].append(uri)

    grupos = list(por_artista.values())
    for grupo in grupos:
        random.shuffle(grupo)
    random.shuffle(grupos)

    selecionadas = []
    rodada = 0
    while len(selecionadas) < tamanho and rodada < max_por_artista:
        for grupo in grupos:
            if len(selecionadas) >= tamanho:
                break
            if rodada < len(grupo):
                selecionadas.append(grupo[rodada])
        rodada += 1

    if len(selecionadas) < tamanho:
        restantes = [uri for grupo in grupos for uri in grupo[rodada:]]
        random.shuffle(restantes)
        selecionadas += restantes[:tamanho - len(selecionadas)]

    return selecionadas


# ---------- Main ----------
def main():
    selecionar_idioma()
    garantir_env()

    global REFRESH_TOKEN
    if not CLIENT_ID or not CLIENT_SECRET:
        print(texto["configure_id"])
        return

    refresh_original = REFRESH_TOKEN
    token, REFRESH_TOKEN = obter_token(REFRESH_TOKEN)

    if REFRESH_TOKEN != refresh_original and os.getenv("GITHUB_ACTIONS") == "true":
        if atualizar_secret_github("SPOTIFY_REFRESH_TOKEN", REFRESH_TOKEN):
            print("🔐 Refresh Token atualizado automaticamente no secret do GitHub.")
        else:
            print("⚠️  Refresh Token mudou, mas não foi possível atualizar o secret (defina GH_PAT nos secrets do repositório).")

    headers = {"Authorization": f"Bearer {token}"}
    user_id = sp_get("https://api.spotify.com/v1/me", headers)["id"]

    faixas, url = [], SPOTIFY_SAVED + "?limit=50"
    while url:
        data = sp_get(url, headers)
        for i in data["items"]:
            track = i.get("track")
            if not track or not track.get("uri"):
                continue
            artistas = track.get("artists") or []
            artist_id = artistas[0]["id"] if artistas else None
            faixas.append((track["uri"], artist_id))
        url = data.get("next")
    if not faixas:
        print(texto["nenhuma_track"]); return

    sample = amostra_diversificada(faixas, min(TARGET_SIZE, len(faixas)))
    pid    = obter_playlist_id(headers, user_id)
    substituir_faixas(headers, pid, sample)

    bootstrap_secrets_github({
        "CLIENT_ID": CLIENT_ID,
        "CLIENT_SECRET": CLIENT_SECRET,
        "REDIRECT_URI": REDIRECT_URI,
        "REFRESH_TOKEN": REFRESH_TOKEN,
        "PLAYLIST_ID": pid,
        "GH_PAT": os.getenv("GH_PAT"),
    })

    print(texto["playlist_atualizada"].format(
    nome=PLAYLIST_NAME,
    quantidade=len(sample),
    data=date.today(),
    id=pid
))


if __name__ == "__main__":
    main()
