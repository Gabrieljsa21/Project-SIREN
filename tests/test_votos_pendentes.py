# -*- coding: utf-8 -*-
from siren.core import votos_pendentes as votos_mod


def _echo_falso(monkeypatch, no_ar=True):
    chamadas = []

    def enviar_feedback(artista, titulo, feedback, abrir_prova=True):
        chamadas.append((titulo, feedback))
        return {"ok": True} if no_ar else None

    def remover_voto(artista, titulo):
        chamadas.append((titulo, None))
        return {"ok": True} if no_ar else None

    monkeypatch.setattr(votos_mod.echo_client, "enviar_feedback", enviar_feedback)
    monkeypatch.setattr(votos_mod.echo_client, "remover_voto", remover_voto)
    return chamadas


def test_envia_e_esvazia_a_fila(monkeypatch):
    chamadas = _echo_falso(monkeypatch)
    votos_mod.adicionar("A", "X", "positivo")
    votos_mod.adicionar("B", "X", None)
    assert votos_mod.enviar_pendentes() == 2
    assert chamadas == [("A", "positivo"), ("B", None)]
    assert votos_mod.listar() == []


def test_echo_fora_do_ar_mantem_os_votos_e_para_no_primeiro(monkeypatch):
    chamadas = _echo_falso(monkeypatch, no_ar=False)
    votos_mod.adicionar("A", "X", "positivo")
    votos_mod.adicionar("B", "X", "negativo")
    assert votos_mod.enviar_pendentes() == 0
    assert chamadas == [("A", "positivo")]
    assert [p["titulo"] for p in votos_mod.listar()] == ["A", "B"]
    assert votos_mod.listar()[0]["tentativas"] == 1


def test_so_o_voto_mais_recente_da_faixa_fica(monkeypatch):
    votos_mod.adicionar("A", "X", "positivo")
    votos_mod.adicionar("a", "x ", "negativo")
    assert [p["voto"] for p in votos_mod.listar()] == ["negativo"]


def test_voto_que_nunca_e_aceito_sai_da_fila(monkeypatch):
    _echo_falso(monkeypatch, no_ar=False)
    monkeypatch.setattr(votos_mod, "TENTATIVAS_MAXIMAS", 2)
    votos_mod.adicionar("A", "X", "positivo")
    votos_mod.enviar_pendentes()
    assert len(votos_mod.listar()) == 1
    votos_mod.enviar_pendentes()
    assert votos_mod.listar() == []
