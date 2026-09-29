# -*- coding: utf-8 -*-
"""Cache em disco de álbum e duração por faixa (2026-09-26) - colunas
"Álbum" e "Duração" das listas de faixas (tela Fila, tela do artista).

Duas fontes, que se completam:
- o ECHO (`/faixa/info`, Last.fm `track.getInfo`), pedido em segundo plano
  quando a faixa aparece numa lista;
- o próprio player: toda faixa que toca tem a duração real descoberta pelo
  resolvedor, gravada aqui.

Um campo já conhecido nunca é apagado por uma resposta sem ele."""
import json
import os
import threading

ARQUIVO_CACHE = "data/cache_faixas.json"

_lock = threading.Lock()
_memoria = None


def _id(titulo, artista):
    return f"{artista.strip().lower()}::{titulo.strip().lower()}"


def _carregar():
    global _memoria
    if _memoria is None:
        try:
            with open(ARQUIVO_CACHE, "r", encoding="utf-8") as f:
                _memoria = json.load(f)
        except Exception:
            _memoria = {}
    return _memoria


def _salvar():
    os.makedirs(os.path.dirname(ARQUIVO_CACHE), exist_ok=True)
    with open(ARQUIVO_CACHE, "w", encoding="utf-8") as f:
        json.dump(_memoria, f, ensure_ascii=False, indent=2)


def obter(titulo, artista):
    """`{"album", "duracao", "consultado"}` ou `None` se nunca visto.
    `consultado` = o ECHO já foi perguntado (mesmo que não soubesse)."""
    with _lock:
        return _carregar().get(_id(titulo, artista))


def registrar(titulo, artista, album=None, duracao=None, consultado=False):
    with _lock:
        cache = _carregar()
        entrada = cache.setdefault(_id(titulo, artista), {"album": None, "duracao": None, "consultado": False})
        if album:
            entrada["album"] = album
        if duracao:
            entrada["duracao"] = int(duracao)
        if consultado:
            entrada["consultado"] = True
        _salvar()
        return dict(entrada)


def precisa_consultar(titulo, artista):
    entrada = obter(titulo, artista)
    return entrada is None or not entrada.get("consultado")


def formatar_duracao(segundos):
    if not segundos:
        return "-"
    segundos = int(segundos)
    return f"{segundos // 60}:{segundos % 60:02d}"
