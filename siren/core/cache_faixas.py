# -*- coding: utf-8 -*-
"""Cache em disco de álbum e duração por faixa (2026-09-26) - colunas
"Álbum" e "Duração" das listas de faixas (tela Fila, tela do artista).

Duas fontes, que se completam:
- o ECHO (`/faixa/info`, Last.fm `track.getInfo`), pedido em segundo plano
  quando a faixa aparece numa lista;
- o próprio player: toda faixa que toca tem a duração real descoberta pelo
  resolvedor, gravada aqui.

Um campo já conhecido nunca é apagado por uma resposta sem ele."""
import atexit
import json
import threading

from siren.core.arquivos import gravar_json

ARQUIVO_CACHE = "data/cache_faixas.json"

# O arquivo passa de 250 KB e era regravado inteiro a cada faixa tocada e a
# cada resposta do ECHO (dezenas por lista aberta). Agora a gravação espera
# este intervalo e junta as mudanças; `descarregar` grava o que faltar ao
# fechar. 0 grava na hora (testes).
INTERVALO_GRAVACAO = 5.0

_lock = threading.Lock()
_memoria = None
_gravacao_agendada = None


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
    """Chamado com `_lock` preso."""
    global _gravacao_agendada
    if INTERVALO_GRAVACAO <= 0:
        gravar_json(ARQUIVO_CACHE, _memoria)
        return
    if _gravacao_agendada is None:
        _gravacao_agendada = threading.Timer(INTERVALO_GRAVACAO, descarregar)
        _gravacao_agendada.daemon = True
        _gravacao_agendada.start()


def descarregar():
    """Grava agora o que estiver esperando (fim do intervalo, ou o SIREN
    fechando)."""
    global _gravacao_agendada
    with _lock:
        agendada, _gravacao_agendada = _gravacao_agendada, None
        if agendada is None or _memoria is None:
            return
        agendada.cancel()
        try:
            gravar_json(ARQUIVO_CACHE, _memoria)
        except OSError:
            pass  # cache: perder uma gravação só custa uma consulta a mais


atexit.register(descarregar)


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
