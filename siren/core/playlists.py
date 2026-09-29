# -*- coding: utf-8 -*-
"""Playlists do SIREN (docs/PLANO_SIREN.md, seção 3/11) - criadas por você ou
pelo próprio SIREN a partir dos votos (Músicas Curtidas/Não Curtidas).
Salvas localmente; o ECHO nunca guarda playlist nenhuma (só sugere quais
faixas provavelmente combinam, nunca o que fica salvo de fato)."""
import os
import json

ARQUIVO_PLAYLISTS = "data/playlists.json"
# Coleção automática removida em 2026-09-25 (era um subconjunto de Músicas
# Curtidas: só as curtidas vindas do ECHO) - o nome fica só pra
# `remover_descobertas_legada` limpar o dado antigo.
NOME_LEGADO_DESCOBERTAS = "Descobertas do SIREN"
NOME_PLAYLIST_CURTIDAS = "Músicas Curtidas"
NOME_PLAYLIST_NAO_CURTIDAS = "Não Curtidas"
PLAYLISTS_DO_SISTEMA = {
    NOME_PLAYLIST_CURTIDAS,
    NOME_PLAYLIST_NAO_CURTIDAS,
}


def _track_id(titulo, artista):
    return f"{artista.strip().lower()}::{titulo.strip().lower()}"


def carregar():
    if not os.path.exists(ARQUIVO_PLAYLISTS):
        return {}
    try:
        with open(ARQUIVO_PLAYLISTS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar(playlists):
    os.makedirs(os.path.dirname(ARQUIVO_PLAYLISTS), exist_ok=True)
    with open(ARQUIVO_PLAYLISTS, "w", encoding="utf-8") as f:
        json.dump(playlists, f, ensure_ascii=False, indent=2)


def listar():
    """Nome + quantidade de faixas de cada playlist, ordenado por nome - o
    suficiente pra montar o grid da tela de Playlists sem carregar as
    faixas inteiras de todas de uma vez."""
    playlists = carregar()
    return sorted(
        [{"nome": nome, "quantidade": len(faixas)} for nome, faixas in playlists.items()],
        key=lambda p: p["nome"].lower(),
    )


def obter_faixas(nome):
    return carregar().get(nome, [])


def criar(nome):
    playlists = carregar()
    if nome not in playlists:
        playlists[nome] = []
        _salvar(playlists)
    return playlists[nome]


def renomear(nome_atual, nome_novo):
    if nome_atual in PLAYLISTS_DO_SISTEMA or nome_novo in PLAYLISTS_DO_SISTEMA:
        return False
    playlists = carregar()
    if nome_atual not in playlists or nome_novo in playlists:
        return False
    playlists[nome_novo] = playlists.pop(nome_atual)
    _salvar(playlists)
    return True


def excluir(nome):
    if nome in PLAYLISTS_DO_SISTEMA:
        return False
    playlists = carregar()
    if nome in playlists:
        del playlists[nome]
        _salvar(playlists)
        return True
    return False


def adicionar_faixa(nome, titulo, artista):
    """Cria a playlist na hora se ainda não existir - "adicionar numa
    playlist que ainda não existe" não deveria ser um erro, o usuário só
    quer que a faixa entre lá. Nunca duplica a mesma faixa duas vezes na
    mesma playlist."""
    playlists = carregar()
    faixas = playlists.setdefault(nome, [])
    alvo = _track_id(titulo, artista)
    if not any(_track_id(f["titulo"], f["artista"]) == alvo for f in faixas):
        faixas.append({"titulo": titulo, "artista": artista})
        _salvar(playlists)
    return faixas


def remover_faixa(nome, titulo, artista):
    playlists = carregar()
    if nome not in playlists:
        return []
    alvo = _track_id(titulo, artista)
    playlists[nome] = [f for f in playlists[nome] if _track_id(f["titulo"], f["artista"]) != alvo]
    _salvar(playlists)
    return playlists[nome]


def remover_descobertas_legada():
    """Apaga a antiga playlist automática "Descobertas do SIREN", se ainda
    existir no arquivo. Toda faixa dela já estava em Músicas Curtidas (só
    entrava lá quem recebia ❤️), então nada se perde. Idempotente."""
    playlists = carregar()
    if NOME_LEGADO_DESCOBERTAS in playlists:
        del playlists[NOME_LEGADO_DESCOBERTAS]
        _salvar(playlists)
        return True
    return False


def registrar_voto(titulo, artista, positivo):
    """Mantém os votos em duas playlists especiais e mutuamente exclusivas.

    Elas são persistidas no mesmo arquivo das playlists comuns para que toda
    a UI possa tratá-las como coleções normais, mas não podem ser excluídas.
    """
    destino = NOME_PLAYLIST_CURTIDAS if positivo else NOME_PLAYLIST_NAO_CURTIDAS
    oposta = NOME_PLAYLIST_NAO_CURTIDAS if positivo else NOME_PLAYLIST_CURTIDAS
    remover_faixa(oposta, titulo, artista)
    return adicionar_faixa(destino, titulo, artista)
