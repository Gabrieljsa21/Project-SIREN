# -*- coding: utf-8 -*-
"""Importar votos do ECHO (2026-09-06, pedido do usuário: "não consegue já
importar as músicas que gostei e não gostei que coloquei enquanto ouvia
pelo Discord?") - o Modo Música do ERIS já vota no MESMO `discord_user_id`
fixo que o SIREN usa (ver `integrations/echo_client.py::DONO_DISCORD_ID`),
então o voto em si (❤️/👎) já é compartilhado automaticamente, sem precisar
de nenhuma importação - `_tocar_faixa` já consulta `echo_client.obter_voto`
toda vez que uma faixa toca.

O que FALTAVA é trazer esse histórico pra dentro dos dados PRÓPRIOS do
SIREN de uma vez só (favoritos, playlist "Descobertas do SIREN") - sem
isso, só ficava visível faixa por faixa, conforme o usuário fosse tocando
de novo cada uma no SIREN."""
from siren.core import favoritos as favoritos_mod
from siren.core import playlists as playlists_mod


def importar_aprovadas(aprovadas):
    """`aprovadas`: lista de entradas do ECHO (`echo_client.obter_aprovados`),
    cada uma com pelo menos "titulo"/"artista". Marca ★ favorito (se ainda
    não fosse) e adiciona na playlist "Descobertas do SIREN" - idempotente,
    rodar de novo com a mesma lista não duplica nada. Devolve quantas eram
    NOVAS (não estavam favoritadas ainda)."""
    novas = 0
    for entrada in aprovadas:
        titulo, artista = entrada["titulo"], entrada["artista"]
        if not favoritos_mod.esta_favoritada(titulo, artista):
            favoritos_mod.favoritar(titulo, artista)
            novas += 1
        playlists_mod.adicionar_a_descobertas(titulo, artista)
    return novas
