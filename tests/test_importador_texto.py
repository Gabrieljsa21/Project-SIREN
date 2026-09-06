# -*- coding: utf-8 -*-
from siren.core import importador_texto


def test_parseia_linhas_simples():
    texto = "MF DOOM - Doomsday\nNine Grain - Rust and Velvet"
    assert importador_texto.parsear_texto(texto) == [
        {"titulo": "Doomsday", "artista": "MF DOOM"},
        {"titulo": "Rust and Velvet", "artista": "Nine Grain"},
    ]


def test_ignora_numeracao_inicial():
    texto = "1. MF DOOM - Doomsday\n2) Nine Grain - Rust and Velvet"
    assert importador_texto.parsear_texto(texto) == [
        {"titulo": "Doomsday", "artista": "MF DOOM"},
        {"titulo": "Rust and Velvet", "artista": "Nine Grain"},
    ]


def test_ignora_linha_vazia_e_sem_hifen():
    texto = "MF DOOM - Doomsday\n\nlinha sem separador nenhum"
    assert importador_texto.parsear_texto(texto) == [{"titulo": "Doomsday", "artista": "MF DOOM"}]


def test_titulo_com_hifen_no_meio_usa_o_primeiro_separador():
    texto = "MF DOOM - Doomsday - Remix"
    assert importador_texto.parsear_texto(texto) == [{"titulo": "Doomsday - Remix", "artista": "MF DOOM"}]


def test_texto_vazio_devolve_lista_vazia():
    assert importador_texto.parsear_texto("") == []
