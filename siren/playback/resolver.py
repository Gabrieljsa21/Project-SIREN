# -*- coding: utf-8 -*-
"""Playback Resolver mínimo (docs/PLANO_SIREN.md, seção 7) - artista+título ->
yt-dlp -> 1 resultado -> ResolvedStream. Sem múltiplos provedores, cache ou
fallback nesta fase; o contrato (`ResolvedStream`) é o mesmo conceito usado
pelo Project ERIS (`eris/core/musica.py::_buscar_no_youtube`), cada
repositório com sua própria implementação (guardrail 2 - nenhum código
Python compartilhado entre os dois).

`extrair_resolved_stream` fica separado de `resolver_stream` de propósito -
é a parte pura (sem rede), testável sem depender do yt-dlp de verdade."""
import os
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
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
RESULTADOS_PLANO_B = 5


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
    query = montar_query(titulo, artista)
    try:
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(query, download=False)
    except Exception as e:
        print(f"[SIREN] Falha ao resolver stream (\"{artista} - {titulo}\"): {e}")
        info = None
    resolvido = extrair_resolved_stream(info, titulo, artista)
    if resolvido is None:
        resolvido = _resolver_pelos_proximos_resultados(query, opcoes, titulo, artista)
    return resolvido


def _resolver_pelos_proximos_resultados(query, opcoes, titulo, artista):
    """Plano B quando o 1º resultado não toca (2026-10-06, log real: vídeo
    com restrição de idade, ou busca do YouTube que volta vazia - "Frejat
    Por você" não acha nada lá, só no YouTube Music): lista os próximos
    resultados das duas buscas sem abrir nenhum e tenta um por um até achar
    um tocável."""
    for url in _candidatos(query, opcoes):
        try:
            with yt_dlp.YoutubeDL(opcoes) as ydl:
                resolvido = extrair_resolved_stream(ydl.extract_info(url, download=False), titulo, artista)
        except Exception:
            continue
        if resolvido is not None:
            return resolvido
    return None


def _candidatos(query, opcoes):
    opcoes_lista = dict(opcoes)
    opcoes_lista.update({"extract_flat": "in_playlist", "skip_download": True, "playlistend": RESULTADOS_PLANO_B})
    buscas = [
        f"ytsearch{RESULTADOS_PLANO_B}:{query}",
        f"https://music.youtube.com/search?q={urllib.parse.quote(query)}#songs",
    ]
    vistos = set()
    for busca in buscas:
        try:
            with yt_dlp.YoutubeDL(opcoes_lista) as ydl:
                lista = ydl.extract_info(busca, download=False)
        except Exception as e:
            print(f"[SIREN] Falha ao listar resultados ({busca}): {e}")
            continue
        for entrada in ((lista or {}).get("entries") or [])[:RESULTADOS_PLANO_B]:
            url = entrada and (entrada.get("url") or entrada.get("id"))
            if url and entrada.get("id") not in vistos:
                vistos.add(entrada.get("id"))
                yield url


def extrair_resultados_busca(info):
    """Converte a resposta de ``ytsearch`` em faixas exibíveis na Busca.

    A reprodução resolve o stream novamente só quando o usuário escolhe um
    resultado; a pesquisa não abre nem baixa áudio antecipadamente. A data
    que vem aqui é a aproximada do YouTube ("há 2 anos"), trocada pela exata
    quando `detalhes_video` responde.
    """
    resultados = []
    for entrada in (info or {}).get("entries") or []:
        if not entrada or not entrada.get("title"):
            continue
        canal = entrada.get("channel") or entrada.get("uploader")
        artista = entrada.get("artist") or canal or "Artista desconhecido"
        resultados.append({
            "titulo": entrada["title"],
            "artista": artista,
            "duracao": entrada.get("duration"),
            "canal": canal,
            "visualizacoes": entrada.get("view_count"),
            "data": entrada.get("timestamp"),
            "url": entrada.get("url") or entrada.get("id"),
        })
    return resultados


def _opcoes_busca():
    opcoes = dict(OPCOES_BASE)
    cookies = os.getenv("YOUTUBE_COOKIES_FILE")
    if cookies and os.path.exists(cookies):
        opcoes["cookiefile"] = cookies
    return opcoes


def buscar_faixas(texto, limite=5):
    """Pesquisa faixas diretamente no YouTube, sem depender do ECHO."""
    texto = texto.strip()
    if not texto:
        return []
    limite = max(1, min(20, int(limite)))
    opcoes = _opcoes_busca()
    opcoes.update({
        "extract_flat": "in_playlist",
        "skip_download": True,
        # Sem isso a busca não traz data nenhuma: o YouTube só manda o texto
        # "há 2 anos", que o yt-dlp converte numa data aproximada.
        "extractor_args": {**OPCOES_BASE["extractor_args"], "youtubetab": {"approximate_date": [""]}},
    })
    try:
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(f"ytsearch{limite}:{texto}", download=False)
    except Exception as e:
        print(f"[SIREN] Falha na busca (\"{texto}\"): {e}")
        return []
    return extrair_resultados_busca(info)


def extrair_detalhes_video(info):
    """Parte pura de `detalhes_video`: curtidas (`None` quando o canal
    esconde) e a data exata de publicação como timestamp."""
    info = info or {}
    data = info.get("timestamp")
    if data is None and info.get("upload_date"):
        try:
            data = datetime.strptime(info["upload_date"], "%Y%m%d").timestamp()
        except ValueError:
            data = None
    return {"curtidas": info.get("like_count"), "data": data}


def detalhes_video(url):
    """Abre a página do vídeo só pelos dados que a busca não traz (cerca de
    2 s por vídeo), sem resolver formato de áudio."""
    try:
        with yt_dlp.YoutubeDL(_opcoes_busca()) as ydl:
            info = ydl.extract_info(url, download=False, process=False)
    except Exception as e:
        print(f"[SIREN] Falha ao ler detalhes do vídeo ({url}): {e}")
        return {"curtidas": None, "data": None}
    return extrair_detalhes_video(info)


def stream_expirado(resolved_stream):
    return time.time() >= resolved_stream.expires_at
