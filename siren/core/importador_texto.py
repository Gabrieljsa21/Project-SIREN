# -*- coding: utf-8 -*-
"""Importar playlist colando texto - pedido do usuário (2026-09-06): "quero
poder importar playlist do Spotify e YouTube". O Spotify NÃO dá pra
importar direto via API sem exigir assinatura Premium ATIVA (mesmo achado
documentado em `Project-ECHO/ARQUITETURA.md`, seção "Por que Last.fm não
Spotify" - o app de desenvolvedor para de funcionar se o Premium expirar,
igual quebrou a Fase 1 do ECHO). Colar o texto da playlist (copiado do
app do Spotify, de um export, ou de qualquer lugar) evita essa dependência
por completo - sem credencial nenhuma, sem custo recorrente."""
import re

_PADRAO_LINHA = re.compile(r"^\s*(?:\d+[.)]\s*)?(.+?)\s*-\s*(.+?)\s*$")


def parsear_texto(texto):
    """Uma faixa por linha, formato "Artista - Título" (numeração inicial
    opcional, tipo "1. Artista - Título", é ignorada na extração). Linha
    sem esse formato (sem hífen separando 2 partes) é ignorada - nunca
    inventa artista/título a partir de uma linha ambígua."""
    faixas = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha:
            continue
        m = _PADRAO_LINHA.match(linha)
        if not m:
            continue
        artista, titulo = m.groups()
        if artista and titulo:
            faixas.append({"titulo": titulo, "artista": artista})
    return faixas
