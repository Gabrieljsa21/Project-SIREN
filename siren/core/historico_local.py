# -*- coding: utf-8 -*-
"""Histórico local de reprodução do SIREN (PLANO_SIREN.md, seção 3/10) -
registra o que REALMENTE tocou no player, independente do ECHO estar no ar.

Não confundir com `Project-ECHO/echo/core/historico.py` (outro repositório):
aquele é sobre RECOMENDAÇÃO (o que o ECHO sugeriu e quando, usado pro dedup
do Radar); este é sobre REPRODUÇÃO DE VERDADE no SIREN (inclusive faixas
escolhidas na Biblioteca ou na Busca, sem o ECHO ter participado)."""
import os
import json
from datetime import datetime

ARQUIVO_HISTORICO = "data/historico_local.json"
LIMITE_PADRAO = 500  # mais que suficiente pra alimentar a tela de Histórico; evita crescimento sem fim


def carregar():
    if not os.path.exists(ARQUIVO_HISTORICO):
        return []
    try:
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _salvar(historico):
    os.makedirs(os.path.dirname(ARQUIVO_HISTORICO), exist_ok=True)
    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


def registrar(titulo, artista, origem="desconhecida", limite=LIMITE_PADRAO):
    """`origem`: de onde veio a faixa ("caos", "busca", "playlist:Treino",
    "redescoberta"...) - mesma etiqueta que aparece na Fila, útil pra
    entender de onde vêm as faixas mais tocadas. Corta as entradas mais
    ANTIGAS quando passa do limite - as recentes sempre ficam."""
    historico = carregar()
    historico.append({
        "titulo": titulo,
        "artista": artista,
        "origem": origem,
        "tocado_em": datetime.now().isoformat(timespec="seconds"),
    })
    if len(historico) > limite:
        historico = historico[-limite:]
    _salvar(historico)
    return historico


def obter_recentes(limite=20):
    return list(reversed(carregar()))[:limite]


def obter_artistas_mais_tocados(top_n=10):
    """Contagem simples de aparições por artista - alimenta a Biblioteca
    (ordenar por quanto você realmente ouve, não por ordem alfabética)."""
    contagem = {}
    for entrada in carregar():
        nome = entrada["artista"]
        contagem[nome] = contagem.get(nome, 0) + 1
    return sorted(contagem.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
