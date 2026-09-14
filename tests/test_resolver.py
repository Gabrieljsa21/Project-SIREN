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


def test_extrair_resultados_busca_ignora_entrada_invalida_e_prioriza_artista():
    info = {"entries": [
        None,
        {"uploader": "Sem título"},
        {"title": "Faixa A", "artist": "Artista A", "uploader": "Canal A", "duration": 123},
        {"title": "Faixa B", "channel": "Canal B"},
    ]}

    assert resolver.extrair_resultados_busca(info) == [
        {"titulo": "Faixa A", "artista": "Artista A", "duracao": 123},
        {"titulo": "Faixa B", "artista": "Canal B", "duracao": None},
    ]


def test_buscar_faixas_vazia_nao_abre_youtube(monkeypatch):
    monkeypatch.setattr(resolver.yt_dlp, "YoutubeDL", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError))
    assert resolver.buscar_faixas("   ") == []
