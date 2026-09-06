# -*- coding: utf-8 -*-
from siren.core import config as config_mod


def test_carregar_sem_arquivo_devolve_padrao():
    assert config_mod.carregar() == config_mod.PADRAO


def test_definir_persiste_e_mantem_as_demais_chaves():
    config_mod.definir("modo_ui", "full")
    config = config_mod.carregar()
    assert config["modo_ui"] == "full"
    assert config["volume_inicial"] == config_mod.PADRAO["volume_inicial"]


def test_obter_chave_unica():
    config_mod.definir("volume_inicial", 42)
    assert config_mod.obter("volume_inicial") == 42
    assert config_mod.obter("chave_que_nao_existe") is None


def test_arquivo_salvo_com_versao_antiga_ganha_chaves_novas():
    """Simula um config.json salvo antes de uma chave nova existir - carregar
    nunca deve dar KeyError, sempre preenche com o padrão."""
    config_mod.salvar({"modo_ui": "full"})
    config = config_mod.carregar()
    assert config["modo_ui"] == "full"
    assert config["lyrics_ativado"] == config_mod.PADRAO["lyrics_ativado"]
