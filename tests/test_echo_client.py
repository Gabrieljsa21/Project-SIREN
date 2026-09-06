# -*- coding: utf-8 -*-
"""Guardrail 2 do PLANO_SIREN.md em teste: o SIREN nunca pode quebrar quando
o ECHO está fora do ar - toda função aqui devolve um valor usável (nunca
levanta exceção) quando `_get`/`_post` falham."""
from siren.integrations import echo_client


def test_esta_disponivel_false_quando_echo_nao_responde(monkeypatch):
    monkeypatch.setattr(echo_client, "_get", lambda *a, **k: None)
    assert echo_client.esta_disponivel() is False


def test_esta_disponivel_true_quando_echo_responde(monkeypatch):
    monkeypatch.setattr(echo_client, "_get", lambda *a, **k: {"provedor_configurado": True})
    assert echo_client.esta_disponivel() is True


def test_sugerir_semente_none_quando_echo_indisponivel(monkeypatch):
    monkeypatch.setattr(echo_client, "_post", lambda *a, **k: None)
    assert echo_client.sugerir_semente() is None


def test_sugerir_semente_devolve_faixa(monkeypatch):
    monkeypatch.setattr(echo_client, "_post", lambda *a, **k: {"semente": {"artista": "MF DOOM", "titulo": "Doomsday"}})
    assert echo_client.sugerir_semente() == {"artista": "MF DOOM", "titulo": "Doomsday"}


def test_sugerir_proxima_none_quando_echo_nao_acha_continuacao(monkeypatch):
    monkeypatch.setattr(echo_client, "_post", lambda *a, **k: {"proxima": None})
    assert echo_client.sugerir_proxima("MF DOOM", "Doomsday") is None


def test_enviar_feedback_nunca_levanta_excecao_com_echo_fora(monkeypatch):
    monkeypatch.setattr(echo_client, "_post", lambda *a, **k: None)
    assert echo_client.enviar_feedback("MF DOOM", "Doomsday", "positivo") is None


def test_obter_voto_none_quando_nunca_avaliada(monkeypatch):
    monkeypatch.setattr(echo_client, "_get", lambda *a, **k: {"voto": None})
    assert echo_client.obter_voto("MF DOOM", "Doomsday") is None


def test_obter_em_alta_lista_vazia_quando_echo_fora_do_ar(monkeypatch):
    monkeypatch.setattr(echo_client, "_get", lambda *a, **k: None)
    assert echo_client.obter_em_alta() == []


def test_obter_em_alta_devolve_lista(monkeypatch):
    monkeypatch.setattr(echo_client, "_get", lambda *a, **k: {"em_alta": [{"artista": "MF DOOM", "titulo": "Doomsday"}]})
    assert echo_client.obter_em_alta() == [{"artista": "MF DOOM", "titulo": "Doomsday"}]


def test_obter_redescobertas_lista_vazia_quando_echo_fora_do_ar(monkeypatch):
    monkeypatch.setattr(echo_client, "_get", lambda *a, **k: None)
    assert echo_client.obter_redescobertas() == []


def test_obter_redescobertas_devolve_lista(monkeypatch):
    monkeypatch.setattr(echo_client, "_get", lambda *a, **k: {"redescobertas": [{"artista": "MF DOOM", "titulo": "Doomsday", "dias_sem_aparecer": 200}]})
    assert echo_client.obter_redescobertas(quantidade=1) == [{"artista": "MF DOOM", "titulo": "Doomsday", "dias_sem_aparecer": 200}]


def test_obter_aprovados_lista_vazia_quando_echo_fora_do_ar(monkeypatch):
    monkeypatch.setattr(echo_client, "_get", lambda *a, **k: None)
    assert echo_client.obter_aprovados() == []


def test_obter_aprovados_devolve_lista(monkeypatch):
    monkeypatch.setattr(echo_client, "_get", lambda *a, **k: {"aprovadas": [{"titulo": "Doomsday", "artista": "MF DOOM"}]})
    assert echo_client.obter_aprovados() == [{"titulo": "Doomsday", "artista": "MF DOOM"}]


def test_obter_desaprovados_devolve_lista(monkeypatch):
    monkeypatch.setattr(echo_client, "_get", lambda *a, **k: {"desaprovadas": [{"titulo": "Song Ruim", "artista": "Artista Y"}]})
    assert echo_client.obter_desaprovados() == [{"titulo": "Song Ruim", "artista": "Artista Y"}]
