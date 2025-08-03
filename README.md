# 🎧 Watch Mix – Playlist Automática do Spotify

Este projeto gera uma playlist chamada **Watch Mix** com faixas aleatórias das suas músicas curtidas no Spotify. Ela é atualizada diariamente, sempre utilizando o **mesmo ID**, ideal para sincronizar com o **Apple Watch** sem criar novas playlists duplicadas.

---

## 🚀 Funcionalidades

* Seleciona aleatoriamente 30 faixas da sua biblioteca de músicas curtidas
* Substitui o conteúdo de uma única playlist existente (sem criar novas)
* Automatiza a execução com **GitHub Actions** (execução diária)
* Utiliza **Poetry** para gerenciamento de dependências

---

## 📦 Pré-requisitos

* Python 3.12 ou superior
* Conta no [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
* Repositório no GitHub (opcional, para agendamento automático)


## ⚙️ Instalação e configuração

> Todas as etapas abaixo devem ser feitas via **PowerShell** no Windows.

### 1. Crie uma pasta para o projeto

Abra o **PowerShell** do Windows e execute os comandos abaixo para criar e acessar a pasta do projeto:

```powershell
cd $env:USERPROFILE\Desktop
```

```powershell
mkdir playlist-spotify-watchmix
```

```powershell
cd playlist-spotify-watchmix
```

> Isso irá criar uma pasta chamada `playlist-spotify-watchmix` na sua área de trabalho e já posicionar você dentro dela.

### 2. Clone o repositório e acesse a pasta do script

```powershell
git clone https://github.com/Sissaz/playlist-spotify-watchmix.git
```

```powershell
cd playlist-spotify-watchmix\src\assets
```

### 3. Instale as dependências com o Poetry

Se você ainda não possui o [Poetry](https://python-poetry.org/), instale antes de continuar.

Depois, no PowerShell:

```powershell
poetry install
```

---

## ▶️ Execução manual

Ative o ambiente virtual:

```powershell
poetry shell
```

Rode o script:

```powershell
poetry run python gerar_watch_mix.py
```

### 3. Primeira execução: forneça suas credenciais do Spotify

Ao rodar o script pela primeira vez, você será solicitado a informar:

* `CLIENT_ID`
* `CLIENT_SECRET`
* `REDIRECT_URI` (ex: `http://127.0.0.1:8888/callback`)

Esses dados são obtidos ao registrar seu app no [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).

> Após essa etapa, o script abrirá uma janela no navegador para autorizar o acesso à sua conta. O token será salvo automaticamente no `.env`.

Na segunda execução, o script criará automaticamente a playlist **Watch Mix** (caso ainda não exista) e atualizará o arquivo `.env` com o `PLAYLIST_ID`.

---

## ⏰ Execução automática (via GitHub Actions)

Este projeto já inclui um workflow:
`.github/workflows/run_watch_mix.yml`
Ele executa o script **diariamente** de forma automática.

### Como configurar:

1. Suba o projeto para o seu GitHub.
2. Vá até **Settings > Secrets and variables > Actions > New repository secret** e adicione:

```
CLIENT_ID
CLIENT_SECRET
REDIRECT_URI
REFRESH_TOKEN
PLAYLIST_ID
```

> ⚠️ O `REFRESH_TOKEN` e o `PLAYLIST_ID` são obtidos após rodar o script manualmente pela primeira vez.

---

## ⏲️ Cron de agendamento

O agendamento atual está configurado para rodar todos os dias às 5h UTC:

```
0 5 * * *
```

Você pode alterar esse horário no arquivo `run_watch_mix.yml` conforme sua necessidade.
