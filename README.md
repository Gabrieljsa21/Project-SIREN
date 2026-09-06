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
- [`mpv`](https://mpv.io/) instalado no sistema (`libmpv-2.dll` precisa estar
  no PATH pro `python-mpv` conseguir carregar) - via `winget install mpv-player.mpv`
  ou `scoop install mpv`, por exemplo.
- `ffmpeg` no PATH (usado pelo `yt-dlp` pra extrair áudio).

## Rodando

```bash
uv sync
uv run siren
```

Sem nenhuma variável de ambiente configurada, o SIREN funciona em modo
standalone (sem Caos/recomendação) assim que a busca própria (v1.3) estiver
implementada. Na v1, a fonte de faixas é só o ECHO - ver `.env.example`.
