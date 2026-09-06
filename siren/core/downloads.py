# -*- coding: utf-8 -*-
"""Download de faixas pra ouvir sem internet (pedido do usuário, 2026-09-06:
"acho interessante ter opção de baixar música, pra poder ouvir mesmo sem
internet"). Reaproveita o MESMO Playback Resolver (`playback/resolver.py`)
pra achar a faixa no YouTube - só troca `download=False` por `download=True`,
em vez de reimplementar a busca. Sem pós-processador de áudio de propósito:
fica com o container original (webm/m4a) que o MPV já toca direto - conversão
pra mp3 gastaria CPU/ffmpeg à toa.

`baixar` é SÍNCRONA de propósito (mesmo padrão de `resolver_stream`) - quem
chama (a UI) decide como rodar isso sem travar a janela (thread/worker
próprio do PySide6); este módulo não sabe nada de Qt.

Quem decide RESOLVER, e prioridade entre stream local baixado vs. buscar de
novo no YouTube (a UI, em `_tocar_faixa`), nunca este módulo - senão criaria
import cíclico com `playback/resolver.py` (que já é importado por aqui)."""
import os
import json
import yt_dlp

from siren.core import config as config_mod
from siren.playback.resolver import montar_query, OPCOES_BASE

ARQUIVO_MANIFESTO = "data/downloads.json"


def _track_id(titulo, artista):
    return f"{artista.strip().lower()}::{titulo.strip().lower()}"


def _carregar_manifesto():
    if not os.path.exists(ARQUIVO_MANIFESTO):
        return {}
    try:
        with open(ARQUIVO_MANIFESTO, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_manifesto(manifesto):
    os.makedirs(os.path.dirname(ARQUIVO_MANIFESTO), exist_ok=True)
    with open(ARQUIVO_MANIFESTO, "w", encoding="utf-8") as f:
        json.dump(manifesto, f, ensure_ascii=False, indent=2)


def esta_baixada(titulo, artista):
    return obter_caminho_local(titulo, artista) is not None


def obter_caminho_local(titulo, artista):
    """Caminho do arquivo já baixado, ou `None` se não tiver - nunca confia
    só no registro do manifesto sem checar se o arquivo ainda existe de
    verdade no disco (usuário pode ter apagado a pasta por fora)."""
    entrada = _carregar_manifesto().get(_track_id(titulo, artista))
    if entrada and os.path.exists(entrada.get("caminho", "")):
        return entrada["caminho"]
    return None


def listar_baixadas():
    return [e for e in _carregar_manifesto().values() if os.path.exists(e.get("caminho", ""))]


def remover(titulo, artista):
    """Apaga o arquivo do disco E o registro do manifesto juntos - nunca só
    um dos dois (senão sobra lixo em disco ou uma referência quebrada)."""
    manifesto = _carregar_manifesto()
    entrada = manifesto.pop(_track_id(titulo, artista), None)
    if entrada and os.path.exists(entrada.get("caminho", "")):
        try:
            os.remove(entrada["caminho"])
        except OSError:
            pass
    _salvar_manifesto(manifesto)


def baixar(titulo, artista):
    """Baixa de verdade pro disco (bloqueante, faz chamada de rede) - devolve
    o caminho final, ou `None` se falhar. Sempre em
    `<pasta_downloads>/<artista> - <titulo>.<ext>` (extensão decidida pelo
    yt-dlp - geralmente .webm/.m4a)."""
    pasta = config_mod.obter("pasta_downloads")
    os.makedirs(pasta, exist_ok=True)

    nome_arquivo = f"{artista} - {titulo}".replace("/", "-").replace("\\", "-")
    opcoes = dict(OPCOES_BASE)
    opcoes.update({
        "outtmpl": os.path.join(pasta, nome_arquivo + ".%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    })
    cookies = config_mod.obter("youtube_cookies_file")
    if cookies and os.path.exists(cookies):
        opcoes["cookiefile"] = cookies

    try:
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(montar_query(titulo, artista), download=True)
            if info and "entries" in info:
                entradas = [e for e in info["entries"] if e]
                if not entradas:
                    return None
                info = entradas[0]
            if info is None:
                return None
            caminho = ydl.prepare_filename(info)
    except Exception as e:
        print(f"[SIREN] Falha ao baixar (\"{artista} - {titulo}\"): {e}")
        return None

    if not os.path.exists(caminho):
        return None

    manifesto = _carregar_manifesto()
    manifesto[_track_id(titulo, artista)] = {"titulo": titulo, "artista": artista, "caminho": caminho}
    _salvar_manifesto(manifesto)
    return caminho
