# -*- coding: utf-8 -*-
from siren.core import favoritos as favoritos_mod


def test_favoritar_e_consultar():
    assert not favoritos_mod.esta_favoritada("Doomsday", "MF DOOM")
    favoritos_mod.favoritar("Doomsday", "MF DOOM")
    assert favoritos_mod.esta_favoritada("Doomsday", "MF DOOM")


def test_favoritar_nao_duplica():
    favoritos_mod.favoritar("Doomsday", "MF DOOM")
    favoritos_mod.favoritar("Doomsday", "MF DOOM")
    assert len(favoritos_mod.carregar()) == 1


def test_desfavoritar():
    favoritos_mod.favoritar("Doomsday", "MF DOOM")
    favoritos_mod.desfavoritar("Doomsday", "MF DOOM")
    assert not favoritos_mod.esta_favoritada("Doomsday", "MF DOOM")


def test_alternar_liga_e_desliga():
    assert favoritos_mod.alternar("Doomsday", "MF DOOM") is True
    assert favoritos_mod.esta_favoritada("Doomsday", "MF DOOM")
    assert favoritos_mod.alternar("Doomsday", "MF DOOM") is False
    assert not favoritos_mod.esta_favoritada("Doomsday", "MF DOOM")
