# -*- coding: utf-8 -*-
"""Playback Resolver mínimo (PLANO_SIREN.md, seção 7) - artista+título ->
yt-dlp -> 1 resultado -> ResolvedStream. Sem múltiplos provedores, cache ou
fallback nesta fase; o contrato (`ResolvedStream`) é o mesmo conceito usado
pelo Project ERIS (`eris/core/musica.py::_buscar_no_youtube`), cada
repositório com sua própria implementação (guardrail 2 - nenhum código
Python compartilhado entre os dois).

`extrair_resolved_stream` fica separado de `resolver_stream` de propósito -
é a parte pura (sem rede), testável sem depender do yt-dlp de verdade."""
import os
import time
from dataclasses import dataclass
from typing import Optional

import yt_dlp

OPCOES_BASE = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "default_search": "ytsearch1",
    "quiet": True,
    "no_warnings": True,
    "extractor_args": {"youtube": {"player_client": ["android"]}},
}

# URL de stream do YouTube expira - 5h é uma folga confortável pra qualquer
# sessão de escuta razoável sem precisar reagendar re-resolução no meio dela.
DURACAO_EXPIRACAO_SEGUNDOS = 5 * 60 * 60


@dataclass
class ResolvedStream:
    url: str
    title: str
    artist: str
    duration: Optional[float]
    thumbnail: Optional[str]
    source: str
    expires_at: float


def montar_query(titulo, artista):
    return f"{artista} {titulo}".strip()


def extrair_resolved_stream(info, titulo, artista):
    """Converte o dict cru do yt-dlp num `ResolvedStream` - `None` se a busca
    não achou nada tocável (nunca inventa uma faixa)."""
    if info is None:
        return None
    if "entries" in info:
        entradas = [e for e in info["entries"] if e]
        if not entradas:
            return None
        info = entradas[0]
    if not info.get("url"):
        return None
    return ResolvedStream(
        url=info["url"],
        title=titulo,
        artist=artista,
        duration=info.get("duration"),
        thumbnail=info.get("thumbnail"),
        source="youtube",
        expires_at=time.time() + DURACAO_EXPIRACAO_SEGUNDOS,
    )


def resolver_stream(titulo, artista):
    """Busca no YouTube (aceita "artista título" como texto livre) e devolve
    o `ResolvedStream` do primeiro resultado, ou `None` se a busca falhar ou
    não achar nada."""
    opcoes = dict(OPCOES_BASE)
    cookies = os.getenv("YOUTUBE_COOKIES_FILE")
    if cookies and os.path.exists(cookies):
        opcoes["cookiefile"] = cookies
    try:
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(montar_query(titulo, artista), download=False)
    except Exception as e:
        print(f"[SIREN] Falha ao resolver stream (\"{artista} - {titulo}\"): {e}")
        return None
    return extrair_resolved_stream(info, titulo, artista)


def stream_expirado(resolved_stream):
    return time.time() >= resolved_stream.expires_at
