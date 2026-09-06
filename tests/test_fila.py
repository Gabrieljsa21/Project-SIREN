# -*- coding: utf-8 -*-
from siren.core.fila import Fila


def test_adicionar_e_proxima_fifo():
    fila = Fila()
    fila.adicionar("A", "Artista A")
    fila.adicionar("B", "Artista B")
    assert fila.proxima()["titulo"] == "A"
    assert fila.proxima()["titulo"] == "B"
    assert fila.proxima() is None


def test_adicionar_a_seguir_entra_no_topo():
    fila = Fila()
    fila.adicionar("A", "Artista A")
    fila.adicionar_a_seguir("B", "Artista B")
    assert fila.proxima()["titulo"] == "B"
    assert fila.proxima()["titulo"] == "A"


def test_remover_por_indice():
    fila = Fila()
    fila.adicionar("A", "Artista A")
    fila.adicionar("B", "Artista B")
    fila.remover(0)
    assert len(fila) == 1
    assert fila.listar()[0]["titulo"] == "B"


def test_mover_reordena():
    fila = Fila()
    fila.adicionar("A", "Artista A")
    fila.adicionar("B", "Artista B")
    fila.mover(1, -1)  # sobe B pra posição 0
    assert [i["titulo"] for i in fila.listar()] == ["B", "A"]


def test_mover_fora_dos_limites_nao_faz_nada():
    fila = Fila()
    fila.adicionar("A", "Artista A")
    fila.mover(0, -1)
    fila.mover(0, 1)
    assert [i["titulo"] for i in fila.listar()] == ["A"]


def test_limpar():
    fila = Fila()
    fila.adicionar("A", "Artista A")
    fila.limpar()
    assert len(fila) == 0
