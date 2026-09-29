# -*- coding: utf-8 -*-
import os
import time

from siren.core import sessao as sessao_mod


def test_salvar_e_carregar():
    sessao_mod.salvar("Levels", "Avicii", "caos", 83.456, duracao=199.7, thumbnail="http://x/y.jpg")
    dados = sessao_mod.carregar()
    assert {k: dados[k] for k in ("titulo", "artista", "origem", "posicao", "duracao", "thumbnail", "continuar")} == {
        "titulo": "Levels", "artista": "Avicii", "origem": "caos", "posicao": 83.46, "duracao": 199,
        "thumbnail": "http://x/y.jpg", "continuar": False,
    }
    assert dados["pid"] == os.getpid()


def test_sem_sessao_devolve_none():
    assert sessao_mod.carregar() is None


def test_arquivo_corrompido_nao_quebra(tmp_path, monkeypatch):
    arquivo = tmp_path / "quebrado.json"
    arquivo.write_text("{nao e json", encoding="utf-8")
    monkeypatch.setattr(sessao_mod, "ARQUIVO_SESSAO", str(arquivo))
    assert sessao_mod.carregar() is None


def test_geometria_da_janela():
    assert sessao_mod.carregar_janela() is None
    sessao_mod.salvar_janela(100, 50, 1200, 800, True)
    assert sessao_mod.carregar_janela() == {"x": 100, "y": 50, "largura": 1200, "altura": 800, "maximizada": True}


def test_posicao_compensa_o_tempo_na_troca_de_modo():
    sessao_mod.salvar("Levels", "Avicii", "caos", 60, continuar=True)
    dados = sessao_mod.carregar()
    dados["salvo_em"] = time.time() - 2
    assert 61.9 < sessao_mod.posicao_atualizada(dados) < 62.5
    dados["continuar"] = False
    assert sessao_mod.posicao_atualizada(dados) == 60


def test_aviso_de_troca_so_vale_pro_pid_certo():
    sessao_mod.sinalizar_troca_concluida(1234)
    assert not sessao_mod.troca_concluida_para(999)
    assert sessao_mod.troca_concluida_para(1234)
    assert not sessao_mod.troca_concluida_para(1234)  # consumido


def test_geometria_fora_de_qualquer_monitor_e_ignorada():
    telas = [(0, 0, 1920, 1040)]
    assert sessao_mod.geometria_visivel({"x": 100, "y": 100}, telas)
    assert not sessao_mod.geometria_visivel({"x": 3887, "y": 323}, telas)
    assert sessao_mod.geometria_visivel({"x": 3887, "y": 323}, telas + [(1920, 0, 2560, 1400)])
    assert not sessao_mod.geometria_visivel(None, telas)
