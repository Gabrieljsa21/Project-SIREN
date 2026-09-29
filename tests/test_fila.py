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


def test_faixa_com_voto_negativo_fica_na_fila_mas_e_pulada():
    fila = Fila()
    fila.adicionar("A", "Artista A")
    fila.adicionar("B", "Artista B")
    fila.adicionar("C", "Artista C")
    fila.definir_voto(0, "negativo")
    fila.definir_voto(1, "negativo")
    assert len(fila) == 3
    assert fila.proxima()["titulo"] == "C"
    assert len(fila) == 0


def test_voto_positivo_nao_pula():
    fila = Fila()
    fila.adicionar("A", "Artista A")
    fila.definir_voto(0, "positivo")
    assert fila.proxima()["titulo"] == "A"


def test_fila_so_com_negativas_devolve_none():
    fila = Fila()
    fila.adicionar("A", "Artista A")
    fila.definir_voto(0, "negativo")
    assert fila.proxima() is None


def _titulos(fila):
    return [f["titulo"] for f in fila.listar()]


def test_mover_para_baixo_e_para_cima():
    fila = Fila()
    for titulo in "ABCD":
        fila.adicionar(titulo, "X")
    fila.mover_para(0, 3)  # solta A entre C e D
    assert _titulos(fila) == ["B", "C", "A", "D"]
    fila.mover_para(3, 0)  # solta D no topo
    assert _titulos(fila) == ["D", "B", "C", "A"]
    fila.mover_para(1, 4)  # solta B no fim
    assert _titulos(fila) == ["D", "C", "A", "B"]


def test_mover_para_mesma_posicao_nao_muda():
    fila = Fila()
    for titulo in "ABC":
        fila.adicionar(titulo, "X")
    fila.mover_para(1, 1)
    fila.mover_para(1, 2)
    assert _titulos(fila) == ["A", "B", "C"]


def test_aleatorio_sorteia_entre_as_nao_puladas():
    import random
    random.seed(3)
    fila = Fila()
    for titulo in "ABCDE":
        fila.adicionar(titulo, "X")
    fila.definir_voto(0, "negativo")
    tocadas = []
    while True:
        faixa = fila.proxima(aleatorio=True)
        if faixa is None:
            break
        tocadas.append(faixa["titulo"])
    assert sorted(tocadas) == ["B", "C", "D", "E"]
    assert tocadas != ["B", "C", "D", "E"]  # com essa semente a ordem não é a da fila
    assert len(fila) == 0
