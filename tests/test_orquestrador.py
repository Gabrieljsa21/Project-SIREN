# -*- coding: utf-8 -*-
from siren.playback import orquestrador
from siren.core import historico_local as historico_mod


class _PlayerFalso:
    def __init__(self):
        self.tocou = None

    def tocar(self, resolved):
        self.tocou = resolved


def test_toca_local_quando_ja_baixada(monkeypatch):
    monkeypatch.setattr(orquestrador.downloads_mod, "obter_caminho_local", lambda t, a: "/caminho/local.webm")
    player = _PlayerFalso()
    assert orquestrador.tocar_faixa(player, "Doomsday", "MF DOOM") is True
    assert player.tocou.url == "/caminho/local.webm"
    assert player.tocou.source == "local"


def test_resolve_pela_rede_quando_nao_baixada(monkeypatch):
    monkeypatch.setattr(orquestrador.downloads_mod, "obter_caminho_local", lambda t, a: None)
    resolved_falso = orquestrador.ResolvedStream(
        url="https://stream", title="Doomsday", artist="MF DOOM",
        duration=222, thumbnail=None, source="youtube", expires_at=0,
    )
    monkeypatch.setattr(orquestrador.resolver_mod, "resolver_stream", lambda t, a: resolved_falso)
    player = _PlayerFalso()
    assert orquestrador.tocar_faixa(player, "Doomsday", "MF DOOM") is True
    assert player.tocou is resolved_falso


def test_devolve_false_quando_nao_acha_em_lugar_nenhum(monkeypatch):
    monkeypatch.setattr(orquestrador.downloads_mod, "obter_caminho_local", lambda t, a: None)
    monkeypatch.setattr(orquestrador.resolver_mod, "resolver_stream", lambda t, a: None)
    player = _PlayerFalso()
    assert orquestrador.tocar_faixa(player, "Doomsday", "MF DOOM") is False


def test_registra_no_historico_local_quando_toca(monkeypatch):
    monkeypatch.setattr(orquestrador.downloads_mod, "obter_caminho_local", lambda t, a: "/caminho/local.webm")
    orquestrador.tocar_faixa(_PlayerFalso(), "Doomsday", "MF DOOM", origem="caos")
    recentes = historico_mod.obter_recentes()
    assert recentes[0]["titulo"] == "Doomsday"
    assert recentes[0]["origem"] == "caos"


def test_nao_registra_historico_quando_falha(monkeypatch):
    monkeypatch.setattr(orquestrador.downloads_mod, "obter_caminho_local", lambda t, a: None)
    monkeypatch.setattr(orquestrador.resolver_mod, "resolver_stream", lambda t, a: None)
    orquestrador.tocar_faixa(_PlayerFalso(), "Doomsday", "MF DOOM")
    assert historico_mod.obter_recentes() == []
