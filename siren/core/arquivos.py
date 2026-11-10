# -*- coding: utf-8 -*-
"""Gravação de JSON compartilhada por todos os arquivos de `data/`.

Grava num temporário e troca de uma vez (`os.replace`): fechar o SIREN, ou
cair a energia, no meio da gravação não deixa o arquivo pela metade. Era
assim só em `playlists.py` e `sessao.py` (depois de as Curtidas sumirem em
2026-10-13); os outros arquivos gravavam direto no destino."""
import json
import os
import threading
import time

TENTATIVAS_TROCA = 5


def gravar_json(caminho, dados):
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    # pid + thread no nome: dois processos (troca de modo) ou duas threads
    # nunca escrevem no mesmo temporário.
    temporario = f"{caminho}.{os.getpid()}.{threading.get_ident()}.tmp"
    try:
        with open(temporario, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        _trocar(temporario, caminho)
    finally:
        if os.path.exists(temporario):
            try:
                os.remove(temporario)
            except OSError:
                pass


def _trocar(origem, destino):
    """`os.replace` no Windows falha se outro processo estiver lendo o
    destino naquele instante; tenta de novo algumas vezes."""
    for tentativa in range(TENTATIVAS_TROCA):
        try:
            os.replace(origem, destino)
            return
        except PermissionError:
            if tentativa == TENTATIVAS_TROCA - 1:
                raise
            time.sleep(0.05)
