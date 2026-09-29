# -*- coding: utf-8 -*-
from siren.core import cache_faixas as cache_mod


def test_registrar_e_obter():
    cache_mod.registrar("Stronger", "Kanye West", album="Graduation", duracao=312, consultado=True)
    assert cache_mod.obter("stronger", "kanye west") == {"album": "Graduation", "duracao": 312, "consultado": True}


def test_resposta_sem_campo_nao_apaga_o_que_ja_se_sabe():
    cache_mod.registrar("Stronger", "Kanye West", duracao=312)
    cache_mod.registrar("Stronger", "Kanye West", album=None, duracao=None, consultado=True)
    assert cache_mod.obter("Stronger", "Kanye West")["duracao"] == 312


def test_precisa_consultar_ate_o_echo_ser_perguntado():
    assert cache_mod.precisa_consultar("X", "Y")
    cache_mod.registrar("X", "Y", duracao=100)  # só o player sabia a duração
    assert cache_mod.precisa_consultar("X", "Y")
    cache_mod.registrar("X", "Y", consultado=True)
    assert not cache_mod.precisa_consultar("X", "Y")


def test_formatar_duracao():
    assert cache_mod.formatar_duracao(212) == "3:32"
    assert cache_mod.formatar_duracao(None) == "-"
