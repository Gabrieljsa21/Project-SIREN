# -*- coding: utf-8 -*-
"""Importar playlist do YouTube - lista os vídeos de uma playlist pública
sem baixar nada (`extract_flat`), reaproveitando o mesmo yt-dlp do
resolver. Não precisa de credencial nenhuma - YouTube não exige login pra
listar playlist pública (diferente do Spotify, ver `core/importador_texto.py`)."""
from urllib.parse import parse_qs, urlparse

import yt_dlp

_OPCOES = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True}


def _normalizar_url(url):
    """Link de vídeo dentro de playlist (`watch?v=...&list=...`, o que o
    navegador copia ao abrir um item da playlist) vira o link da playlist
    em si. Com `extract_flat`, o yt-dlp devolve o `watch` como um único
    item `_type: url` sem `entries`, e a importação saía vazia."""
    lista = parse_qs(urlparse(url).query).get("list")
    if lista and lista[0]:
        return f"https://www.youtube.com/playlist?list={lista[0]}"
    return url


def importar_playlist(url):
    """Devolve lista de `{"titulo", "artista"}`, ou lista vazia se a URL não
    for uma playlist válida/pública ou a extração falhar - nunca inventa
    faixa. "artista" aqui é o nome do canal (mesma aproximação de
    `Project-ERIS/eris/core/musica.py::_buscar_no_youtube` - texto de
    exibição, não dado 100% confiável)."""
    url = _normalizar_url(url)
    try:
        with yt_dlp.YoutubeDL(_OPCOES) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"[SIREN] Falha ao importar playlist do YouTube ({url}): {e}")
        return []
    if not info:
        return []
    entradas = info.get("entries") or []
    faixas = []
    for entrada in entradas:
        if not entrada:
            continue
        faixas.append({
            "titulo": entrada.get("title") or "?",
            "artista": entrada.get("uploader") or entrada.get("channel") or "Desconhecido",
        })
    return faixas
