# -*- coding: utf-8 -*-
from siren.core import playlists as playlists_mod


def test_criar_e_listar():
    playlists_mod.criar("Treino")
    assert playlists_mod.listar() == [{"nome": "Treino", "quantidade": 0}]


def test_adicionar_faixa_cria_playlist_se_nao_existir():
    playlists_mod.adicionar_faixa("Piscina", "Doomsday", "MF DOOM")
    assert playlists_mod.obter_faixas("Piscina") == [{"titulo": "Doomsday", "artista": "MF DOOM"}]


def test_adicionar_faixa_nao_duplica():
    playlists_mod.adicionar_faixa("Piscina", "Doomsday", "MF DOOM")
    playlists_mod.adicionar_faixa("Piscina", "Doomsday", "MF DOOM")
    assert len(playlists_mod.obter_faixas("Piscina")) == 1


def test_remover_faixa():
    playlists_mod.adicionar_faixa("Piscina", "Doomsday", "MF DOOM")
    playlists_mod.remover_faixa("Piscina", "Doomsday", "MF DOOM")
    assert playlists_mod.obter_faixas("Piscina") == []


def test_renomear():
    playlists_mod.criar("Treino")
    assert playlists_mod.renomear("Treino", "Cardio") is True
    assert playlists_mod.obter_faixas("Treino") == []
    assert "Cardio" in [p["nome"] for p in playlists_mod.listar()]


def test_renomear_falha_se_nome_novo_ja_existir():
    playlists_mod.criar("Treino")
    playlists_mod.criar("Cardio")
    assert playlists_mod.renomear("Treino", "Cardio") is False


def test_excluir():
    playlists_mod.criar("Treino")
    assert playlists_mod.excluir("Treino") is True
    assert playlists_mod.listar() == []


def test_adicionar_a_descobertas():
    playlists_mod.adicionar_a_descobertas("Doomsday", "MF DOOM")
    assert playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_DESCOBERTAS) == [
        {"titulo": "Doomsday", "artista": "MF DOOM"}
    ]


def test_votos_viram_playlists_mutuamente_exclusivas():
    playlists_mod.registrar_voto("Doomsday", "MF DOOM", positivo=True)
    assert playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_CURTIDAS) == [
        {"titulo": "Doomsday", "artista": "MF DOOM"}
    ]

    playlists_mod.registrar_voto("Doomsday", "MF DOOM", positivo=False)
    assert playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_CURTIDAS) == []
    assert playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_NAO_CURTIDAS) == [
        {"titulo": "Doomsday", "artista": "MF DOOM"}
    ]


def test_playlists_de_voto_nao_podem_ser_excluidas():
    playlists_mod.registrar_voto("Doomsday", "MF DOOM", positivo=True)
    assert playlists_mod.excluir(playlists_mod.NOME_PLAYLIST_CURTIDAS) is False
    assert len(playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_CURTIDAS)) == 1
