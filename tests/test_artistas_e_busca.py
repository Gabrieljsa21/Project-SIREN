# -*- coding: utf-8 -*-
from siren.ui.full.views.artistas import juntar_artistas
from siren.ui.full.views.playlists import faixa_combina


def test_busca_ignora_acento_maiuscula_e_ordem_das_palavras():
    faixa = {"titulo": "Naughty Girl", "artista": "Beyoncé"}
    assert faixa_combina(faixa, "beyonce")
    assert faixa_combina(faixa, "GIRL beyon")
    assert faixa_combina(faixa, "")
    assert not faixa_combina(faixa, "rihanna")


def test_juntar_artistas_prefere_o_echo_e_soma_reproducoes_locais():
    historico = [{"artista": "Avicii"}, {"artista": "avicii"}, {"artista": "Zedd"}]
    curtidas = [{"titulo": "A", "artista": "Zedd"}, {"titulo": "B", "artista": "Zedd"}]
    registros = [{"nome": "Avicii", "nota": 0.97, "curtidas": 14, "descurtidas": 1, "estado": "normal"}]
    por_nome = {a["nome"]: a for a in juntar_artistas(registros, historico, curtidas, [])}
    assert por_nome["Avicii"]["reproducoes"] == 2
    assert (por_nome["Avicii"]["nota"], por_nome["Avicii"]["curtidas"]) == (0.97, 14)
    assert (por_nome["Zedd"]["nota"], por_nome["Zedd"]["curtidas"]) == (None, 2)  # sem ECHO: contagem local


def test_juntar_artistas_sem_echo():
    artistas = juntar_artistas(None, [{"artista": "X"}], [], [{"titulo": "Y", "artista": "X"}])
    assert artistas == [{"nome": "X", "nota": None, "curtidas": 0, "descurtidas": 1, "reproducoes": 1, "estado": "normal",
                         "curtidas_local": 0, "descurtidas_local": 1, "tem_echo": False}]
