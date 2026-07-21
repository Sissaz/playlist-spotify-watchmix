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

Os comandos abaixo acessam automaticamente sua Área de Trabalho (Desktop), criam uma nova pasta chamada `playlist-spotify-watchmix` e entram nela.
Caso prefira criar a pasta em outro local (como em `Documentos`, `Downloads` ou outro diretório), você pode ignorar esses comandos. Basta criar a pasta manualmente onde desejar, abrir o **PowerShell dentro dela** e seguir a partir do **passo 2** normalmente.

Abra o **PowerShell** do Windows e execute os comandos abaixo para criar e acessar a pasta do projeto:

```powershell
cd ([Environment]::GetFolderPath('Desktop'))
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

![Screenshot](src/assets/images/Screenshot_2.png)
![Screenshot](src/assets/images/Screenshot_3.png)


> Após essa etapa, o script abrirá uma janela no navegador para autorizar o acesso à sua conta. O token será salvo automaticamente no `.env`.

Na segunda execução, o script criará automaticamente a playlist **Watch Mix** (caso ainda não exista) e atualizará o arquivo `.env` com o `PLAYLIST_ID`.

---

## ⏰ Execução automática (via GitHub Actions)

Este projeto já inclui um workflow: `.github/workflows/watch_mix.yml`, que executa o script **diariamente** de forma automática (05:00 BRT / 08:00 UTC).

Para o workflow funcionar, o repositório precisa destes secrets em **Settings > Secrets and variables > Actions**:

```
SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET
SPOTIFY_REDIRECT_URI
SPOTIFY_REFRESH_TOKEN
PLAYLIST_ID
```

Você pode criá-los de duas formas:

### Opção A — automático (recomendado)

1. Crie um [Personal Access Token](https://github.com/settings/personal-access-tokens/new) do GitHub, escopado só neste repositório, com a permissão **Secrets: Read and write**.
2. Adicione esse token ao seu `.env` local: `GH_PAT=<seu_token>`.
3. Rode o script localmente uma vez (`poetry run python gerar_watch_mix.py`) e autorize no navegador quando pedido.

O próprio script publica todos os secrets acima automaticamente no repositório (inclusive o `GH_PAT`, para que o workflow consiga se auto-atualizar depois se o Spotify emitir um refresh token novo). Nenhuma criação manual de secret é necessária.

### Opção B — manual

Se preferir não criar um PAT, crie cada secret manualmente em **Settings > Secrets and variables > Actions > New repository secret**, copiando os valores do seu `.env` local após a primeira execução (`REFRESH_TOKEN` e `PLAYLIST_ID` só existem depois de rodar o script pelo menos uma vez).

### Se o token quebrar (acesso revogado, secret trocado, etc.)

Rode o script localmente de novo (`poetry run python gerar_watch_mix.py`). Se o refresh token salvo estiver inválido, o script detecta sozinho e abre o navegador para uma nova autorização — não precisa apagar nada do `.env` na mão. Com `GH_PAT` configurado, o novo token já é publicado automaticamente no secret do GitHub.

---

## ⏲️ Cron de agendamento

O agendamento atual está configurado para rodar todos os dias às 08:00 UTC (05:00 BRT):

```
0 8 * * *
```

Você pode alterar esse horário no arquivo `.github/workflows/watch_mix.yml` conforme sua necessidade.
