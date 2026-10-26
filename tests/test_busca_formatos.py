# -*- coding: utf-8 -*-
from siren.ui.full.views.busca import formatar_contagem, formatar_data_relativa

AGORA = 1_800_000_000


def test_formatar_contagem_como_youtube():
    assert formatar_contagem(None) is None
    assert formatar_contagem(950) == "950"
    assert formatar_contagem(1000) == "1 mil"
    assert formatar_contagem(1800) == "1,8 mil"
    assert formatar_contagem(51817) == "51 mil"
    assert formatar_contagem(7492948) == "7,4 mi"
    assert formatar_contagem(2_300_000_000) == "2,3 bi"


def test_formatar_data_relativa_singular_e_plural():
    assert formatar_data_relativa(None, AGORA) is None
    assert formatar_data_relativa(AGORA - 30, AGORA) == "agora há pouco"
    assert formatar_data_relativa(AGORA - 3 * 3600, AGORA) == "há 3 horas"
    assert formatar_data_relativa(AGORA - 86400, AGORA) == "há 1 dia"
    assert formatar_data_relativa(AGORA - 40 * 86400, AGORA) == "há 1 mês"
    assert formatar_data_relativa(AGORA - 4 * 365 * 86400, AGORA) == "há 4 anos"
