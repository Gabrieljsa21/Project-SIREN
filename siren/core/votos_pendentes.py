# -*- coding: utf-8 -*-
"""Votos esperando para chegar ao ECHO (`data/votos_pendentes.json`).

O voto vale na hora nas playlists locais (Músicas Curtidas/Não Curtidas).
O envio ao ECHO acontecia na thread da interface (janela parada até 15 s
com o ECHO lento) e, com o ECHO desligado, o voto se perdia para ele - só o
script `scripts/sincronizar_votos_com_echo.py`, rodado à mão, recuperava.
Agora todo voto entra nesta fila, é enviado em segundo plano e fica nela
até o ECHO responder; a fila é reenviada ao abrir o SIREN e a cada voto."""
import json
import threading
import time

from siren.core.arquivos import gravar_json
from siren.core.registro import registrar
from siren.integrations import echo_client

ARQUIVO_PENDENTES = "data/votos_pendentes.json"
TENTATIVAS_MAXIMAS = 30  # voto que o ECHO nunca aceita não fica na fila para sempre

_lock = threading.Lock()


def _id(titulo, artista):
    return f"{artista.strip().lower()}::{titulo.strip().lower()}"


def _ler():
    try:
        with open(ARQUIVO_PENDENTES, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, list) else []
    except Exception:
        return []


def listar():
    with _lock:
        return _ler()


def adicionar(titulo, artista, voto):
    """`voto`: "positivo", "negativo" ou `None` (tirar o voto). Só o voto
    mais recente de cada faixa fica na fila."""
    with _lock:
        alvo = _id(titulo, artista)
        pendentes = [p for p in _ler() if _id(p["titulo"], p["artista"]) != alvo]
        pendentes.append({"titulo": titulo, "artista": artista, "voto": voto, "em": time.time(), "tentativas": 0})
        gravar_json(ARQUIVO_PENDENTES, pendentes)


def _concluir(item, enviado):
    """Tira o item da fila (enviado, ou tentativas esgotadas) ou conta a
    tentativa. Um voto mais novo da mesma faixa, feito durante o envio, tem
    outro `em` e não é tocado."""
    with _lock:
        pendentes = _ler()
        for indice, pendente in enumerate(pendentes):
            if pendente.get("em") == item.get("em") and _id(pendente["titulo"], pendente["artista"]) == _id(item["titulo"], item["artista"]):
                pendente["tentativas"] = int(pendente.get("tentativas") or 0) + 1
                if enviado or pendente["tentativas"] >= TENTATIVAS_MAXIMAS:
                    if not enviado:
                        registrar(f"VOTO descartado depois de {TENTATIVAS_MAXIMAS} tentativas: {item['artista']} - {item['titulo']}")
                    del pendentes[indice]
                break
        else:
            return
        gravar_json(ARQUIVO_PENDENTES, pendentes)


def enviar_pendentes():
    """Envia a fila ao ECHO, do voto mais antigo ao mais novo. Para no
    primeiro que falhar (ECHO fora do ar: os outros falhariam igual).
    Devolve quantos foram enviados. Bloqueia: chamar fora da thread da
    interface."""
    enviados = 0
    for item in listar():
        if item.get("voto") is None:
            resposta = echo_client.remover_voto(item["artista"], item["titulo"])
        else:
            resposta = echo_client.enviar_feedback(item["artista"], item["titulo"], item["voto"])
        _concluir(item, enviado=resposta is not None)
        if resposta is None:
            break
        enviados += 1
    return enviados
