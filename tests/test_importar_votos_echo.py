# -*- coding: utf-8 -*-
from siren.core import favoritos as favoritos_mod
from siren.core import importar_votos_echo
from siren.core import playlists as playlists_mod


def test_importa_favoritando_e_adicionando_a_descobertas():
    aprovadas = [
        {"titulo": "Doomsday", "artista": "MF DOOM"},
        {"titulo": "Rust and Velvet", "artista": "Nine Grain"},
    ]
    novas = importar_votos_echo.importar_aprovadas(aprovadas)
    assert novas == 2
    assert favoritos_mod.esta_favoritada("Doomsday", "MF DOOM")
    assert favoritos_mod.esta_favoritada("Rust and Velvet", "Nine Grain")
    faixas_descobertas = playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_DESCOBERTAS)
    assert {"titulo": "Doomsday", "artista": "MF DOOM"} in faixas_descobertas
    assert {"titulo": "Rust and Velvet", "artista": "Nine Grain"} in faixas_descobertas


def test_importar_de_novo_nao_conta_como_nova_nem_duplica():
    aprovadas = [{"titulo": "Doomsday", "artista": "MF DOOM"}]
    importar_votos_echo.importar_aprovadas(aprovadas)
    novas_segunda_vez = importar_votos_echo.importar_aprovadas(aprovadas)
    assert novas_segunda_vez == 0
    assert len(favoritos_mod.carregar()) == 1
    assert len(playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_DESCOBERTAS)) == 1


def test_lista_vazia_nao_faz_nada():
    assert importar_votos_echo.importar_aprovadas([]) == 0
    assert favoritos_mod.carregar() == []
