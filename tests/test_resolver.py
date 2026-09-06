# -*- coding: utf-8 -*-
import time

from siren.playback import resolver


def test_montar_query():
    assert resolver.montar_query("Doomsday", "MF DOOM") == "MF DOOM Doomsday"


def test_extrair_resolved_stream_none_quando_info_none():
    assert resolver.extrair_resolved_stream(None, "Doomsday", "MF DOOM") is None


def test_extrair_resolved_stream_none_quando_sem_url():
    assert resolver.extrair_resolved_stream({"title": "Doomsday"}, "Doomsday", "MF DOOM") is None


def test_extrair_resolved_stream_com_resultado_direto():
    info = {"url": "https://stream.example/x", "duration": 180, "thumbnail": "https://img.example/x.jpg"}
    resultado = resolver.extrair_resolved_stream(info, "Doomsday", "MF DOOM")
    assert resultado.url == "https://stream.example/x"
    assert resultado.title == "Doomsday"
    assert resultado.artist == "MF DOOM"
    assert resultado.duration == 180
    assert resultado.source == "youtube"


def test_extrair_resolved_stream_com_entries_pega_primeiro():
    info = {"entries": [{"url": "https://stream.example/primeiro"}, {"url": "https://stream.example/segundo"}]}
    resultado = resolver.extrair_resolved_stream(info, "Doomsday", "MF DOOM")
    assert resultado.url == "https://stream.example/primeiro"


def test_extrair_resolved_stream_entries_vazia_devolve_none():
    assert resolver.extrair_resolved_stream({"entries": []}, "Doomsday", "MF DOOM") is None


def test_stream_expirado():
    expirado = resolver.ResolvedStream(url="x", title="t", artist="a", duration=None, thumbnail=None, source="youtube", expires_at=time.time() - 1)
    valido = resolver.ResolvedStream(url="x", title="t", artist="a", duration=None, thumbnail=None, source="youtube", expires_at=time.time() + 100)
    assert resolver.stream_expirado(expirado) is True
    assert resolver.stream_expirado(valido) is False
