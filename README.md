# Project SIREN

Player de música pessoal - PySide6 + MPV + yt-dlp. Roda sozinho (busca, toca,
favorita, sem dependência nenhuma), e ganha uma camada de inteligência musical
(descoberta, recomendação, Caos) quando o [Project ECHO](../Project-ECHO) está
disponível na rede local.

> Project SIREN é um player musical independente. A integração com Project
> ECHO é opcional e adiciona inteligência, descoberta e personalização, mas
> não é requisito para as funções fundamentais de reprodução.

Ver `PLANO_SIREN.md` pro desenho completo (fronteira com ECHO/ERIS, ownership
de dados, guardrails, critérios da v1 e roadmap).

## Requisitos

- Python 3.11+
- `ffmpeg` no PATH (usado pelo `yt-dlp` pra extrair áudio) - `winget install
  Gyan.FFmpeg`.
- **`libmpv-2.dll`** - o `python-mpv` (biblioteca usada por `playback/player.py`)
  precisa dessa DLL especificamente (não é o mesmo que instalar o player `mpv`
  sozinho). `winget install shinchiro.mpv` instala só o executável do player,
  **sem** essa DLL - não resolve. Passo que funciona de verdade (testado
  2026-09-06):
  1. Baixar o build "dev" mais recente pra `x86_64` em
     https://github.com/shinchiro/mpv-winbuild-cmake/releases (arquivo
     `mpv-dev-x86_64-<data>-git-<hash>.7z`) - o mirror de download do
     SourceForge (`sourceforge.net/projects/mpv-player-windows`) bloqueia
     downloads via script (403 do Cloudflare), o release do GitHub não.
  2. Extrair com 7-Zip (`winget install 7zip.7zip` se não tiver) - o `.7z` traz
     `libmpv-2.dll` solto.
  3. Copiar `libmpv-2.dll` pra dentro de `.venv/Lib/site-packages/` (mesma
     pasta de `mpv.py`) - o `python-mpv` procura a DLL primeiro no `PATH`, e
     cai de volta pra essa pasta se não achar lá (ver `mpv.py`, topo do
     arquivo). Evita mexer no `PATH` do sistema; a DLL fica isolada dentro do
     venv do projeto.

## Rodando

```bash
uv sync
uv run siren
```

Sem nenhuma variável de ambiente configurada, o SIREN funciona em modo
standalone (sem Caos/recomendação) assim que a busca própria (v1.3) estiver
implementada. Na v1, a fonte de faixas é só o ECHO - ver `.env.example`.
