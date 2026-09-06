# -*- coding: utf-8 -*-
from siren.integrations import lyrics as lyrics_mod


def test_parsear_lrc_linhas_com_e_sem_centesimos():
    bruto = "[00:12]Primeira linha\n[00:27.93]Segunda linha\n[01:03.5]Terceira linha"
    linhas = lyrics_mod.parsear_lrc(bruto)
    assert linhas == [
        {"tempo_segundos": 12.0, "texto": "Primeira linha"},
        {"tempo_segundos": 27.93, "texto": "Segunda linha"},
        {"tempo_segundos": 63.5, "texto": "Terceira linha"},
    ]


def test_parsear_lrc_ignora_metadado_e_linha_vazia():
    bruto = "[ar:MF DOOM]\n[ti:Doomsday]\n\n[00:10.00]Só essa linha importa\n[00:15.00]   "
    linhas = lyrics_mod.parsear_lrc(bruto)
    assert linhas == [{"tempo_segundos": 10.0, "texto": "Só essa linha importa"}]


def test_buscar_letra_none_quando_api_falha(monkeypatch):
    def _levanta(*a, **k):
        raise ConnectionError("sem rede")
    monkeypatch.setattr(lyrics_mod.requests, "get", _levanta)
    assert lyrics_mod.buscar_letra("Doomsday", "MF DOOM") is None


def test_buscar_letra_none_quando_status_diferente_de_200(monkeypatch):
    class _RespFalsa:
        status_code = 404
    monkeypatch.setattr(lyrics_mod.requests, "get", lambda *a, **k: _RespFalsa())
    assert lyrics_mod.buscar_letra("Doomsday", "MF DOOM") is None


def test_buscar_letra_instrumental_devolve_sem_linhas(monkeypatch):
    class _RespFalsa:
        status_code = 200
        def json(self): return {"instrumental": True}
    monkeypatch.setattr(lyrics_mod.requests, "get", lambda *a, **k: _RespFalsa())
    resultado = lyrics_mod.buscar_letra("Faixa Instrumental", "Artista")
    assert resultado == {"sincronizada": False, "linhas": [], "texto_simples": None}


def test_buscar_letra_sincronizada(monkeypatch):
    class _RespFalsa:
        status_code = 200
        def json(self):
            return {
                "instrumental": False,
                "syncedLyrics": "[00:10.00]Primeira linha\n[00:20.00]Segunda linha",
                "plainLyrics": "Primeira linha\nSegunda linha",
            }
    monkeypatch.setattr(lyrics_mod.requests, "get", lambda *a, **k: _RespFalsa())
    resultado = lyrics_mod.buscar_letra("Doomsday", "MF DOOM", duracao_segundos=222)
    assert resultado["sincronizada"] is True
    assert len(resultado["linhas"]) == 2
    assert resultado["texto_simples"] == "Primeira linha\nSegunda linha"


def test_buscar_letra_so_plain_quando_sem_sync(monkeypatch):
    class _RespFalsa:
        status_code = 200
        def json(self):
            return {"instrumental": False, "syncedLyrics": None, "plainLyrics": "Só letra sem sincronia"}
    monkeypatch.setattr(lyrics_mod.requests, "get", lambda *a, **k: _RespFalsa())
    resultado = lyrics_mod.buscar_letra("Song", "Artist")
    assert resultado["sincronizada"] is False
    assert resultado["linhas"] == []
    assert resultado["texto_simples"] == "Só letra sem sincronia"
