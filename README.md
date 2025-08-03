# Watch Mix – Playlist Automática do Spotify

Este projeto gera uma playlist chamada **Watch Mix** com faixas aleatórias das suas músicas curtidas no Spotify, atualizando diariamente uma única playlist (mesmo ID), ideal para sincronizar com o Apple Watch e evitar duplicação.

## Funcionalidades

* Seleciona aleatoriamente 30 faixas da sua biblioteca de músicas curtidas
* Substitui o conteúdo de uma única playlist existente (sem criar novas)
* Automatiza a execução com GitHub Actions (execução diária)
* Configurado com **Poetry** para gerenciamento de dependências

---

## Pré-requisitos

* Python 3.12+
* Conta no [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
* Um repositório no GitHub para configurar o agendamento automático (opcional)

---

## Instalação

1. **Clone o repositório:**

```bash
git clone https://github.com/Sissaz/playlist-spotify-watchmix.git
cd playlist-spotify-watchmix
cd src
cd assets

```

2. **Configure o ambiente com Poetry:**

```bash
poetry install
```

3. **Crie um arquivo `.env` dentro de `src/assets/` com os dados da sua API:**

```env
CLIENT_ID=seu_client_id
CLIENT_SECRET=seu_client_secret
REDIRECT_URI=https://localhost:8888/callback
REFRESH_TOKEN=seu_refresh_token
PLAYLIST_ID=id_da_sua_playlist_watchmix
```

*Você pode obter esses valores ao criar um app em [https://developer.spotify.com/dashboard](https://developer.spotify.com/dashboard).*

---

## Execução manual

Com o ambiente virtual ativado:

```bash
poetry run gerar_watch_mix.py
```

---

## Execução automática (GitHub Actions)

O projeto já inclui um workflow `.github/workflows/run_watch_mix.yml`. Ele roda o script uma vez por dia.

1. Suba seu projeto para o GitHub.
2. Vá até as **Secrets** do repositório e adicione:

* `CLIENT_ID`
* `CLIENT_SECRET`
* `REDIRECT_URI`
* `REFRESH_TOKEN`
* `PLAYLIST_ID`

> O script será executado automaticamente todos os dias conforme o cron configurado (`0 5 * * *`).
