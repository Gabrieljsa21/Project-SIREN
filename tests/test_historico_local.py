# -*- coding: utf-8 -*-
from siren.core import historico_local as historico_mod


def test_registrar_e_obter_recentes():
    historico_mod.registrar("Doomsday", "MF DOOM", origem="caos")
    recentes = historico_mod.obter_recentes()
    assert len(recentes) == 1
    assert recentes[0]["titulo"] == "Doomsday"
    assert recentes[0]["origem"] == "caos"


def test_mais_recente_primeiro():
    historico_mod.registrar("Song A", "Artista A")
    historico_mod.registrar("Song B", "Artista B")
    recentes = historico_mod.obter_recentes()
    assert recentes[0]["titulo"] == "Song B"
    assert recentes[1]["titulo"] == "Song A"


def test_limite_corta_as_mais_antigas():
    for i in range(5):
        historico_mod.registrar(f"Song {i}", "Artista", limite=3)
    historico = historico_mod.carregar()
    assert len(historico) == 3
    assert [h["titulo"] for h in historico] == ["Song 2", "Song 3", "Song 4"]


def test_artistas_mais_tocados():
    historico_mod.registrar("A1", "MF DOOM")
    historico_mod.registrar("A2", "MF DOOM")
    historico_mod.registrar("B1", "Nine Grain")
    top = historico_mod.obter_artistas_mais_tocados()
    assert top[0] == ("MF DOOM", 2)
