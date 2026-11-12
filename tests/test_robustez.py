# -*- coding: utf-8 -*-
"""Gravação atômica, limpeza de logs, cache de votos, vídeo exato no
resolver e o caminho com thread de verdade do controlador."""
import datetime
import json
import os
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from siren.core import arquivos as arquivos_mod
from siren.core import playlists as playlists_mod
from siren.core import registro as registro_mod
from siren.playback import controlador as controlador_mod
from siren.playback import resolver as resolver_mod
from siren.playback.resolver import ResolvedStream

_APP = QApplication.instance() or QApplication([])


def test_gravar_json_nao_deixa_temporario(tmp_path):
    caminho = str(tmp_path / "sub" / "dados.json")
    arquivos_mod.gravar_json(caminho, {"a": "é"})
    assert json.load(open(caminho, encoding="utf-8")) == {"a": "é"}
    assert os.listdir(tmp_path / "sub") == ["dados.json"]


def test_falha_na_gravacao_mantem_o_arquivo_anterior(tmp_path):
    caminho = str(tmp_path / "dados.json")
    arquivos_mod.gravar_json(caminho, {"bom": 1})
    try:
        arquivos_mod.gravar_json(caminho, {"ruim": object()})  # não é JSON: falha no meio
    except TypeError:
        pass
    assert json.load(open(caminho, encoding="utf-8")) == {"bom": 1}
    assert os.listdir(tmp_path) == ["dados.json"]


def test_logs_antigos_sao_apagados(tmp_path, monkeypatch):
    pasta = tmp_path / "logs"
    pasta.mkdir()
    hoje = datetime.date.today()
    velho = pasta / f"{(hoje - datetime.timedelta(days=registro_mod.DIAS_DE_LOG + 5)).isoformat()}.log"
    recente = pasta / f"{(hoje - datetime.timedelta(days=3)).isoformat()}.log"
    outro = pasta / "anotacoes.txt"
    for arquivo in (velho, recente, outro):
        arquivo.write_text("x", encoding="utf-8")
    monkeypatch.setattr(registro_mod, "_limpeza_feita_em", None)
    registro_mod.registrar("teste")
    assert not velho.exists()
    assert recente.exists() and outro.exists()


def test_cache_de_votos_acompanha_o_arquivo():
    playlists_mod.registrar_voto("A", "X", positivo=True)
    assert playlists_mod.voto_local("A", "X") == "positivo"
    playlists_mod.registrar_voto("A", "X", positivo=False)
    assert playlists_mod.voto_local("A", "X") == "negativo"
    playlists_mod.remover_voto("A", "X")
    assert playlists_mod.voto_local("A", "X") is None


def test_resolver_abre_o_video_exato_antes_de_pesquisar(monkeypatch):
    abertos = []

    class _YdlFalso:
        def __init__(self, opcoes):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, alvo, download=False):
            abertos.append(alvo)
            return {"url": "https://stream", "duration": 100}

    monkeypatch.setattr(resolver_mod.yt_dlp, "YoutubeDL", _YdlFalso)
    resolvido = resolver_mod.resolver_stream("Titulo", "Canal", url="abc123")
    assert abertos == ["https://www.youtube.com/watch?v=abc123"]
    assert resolvido.url == "https://stream"


def test_resolver_cai_na_pesquisa_se_o_video_exato_falhar(monkeypatch):
    abertos = []

    class _YdlFalso:
        def __init__(self, opcoes):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, alvo, download=False):
            abertos.append(alvo)
            if alvo.startswith("https://www.youtube.com/watch"):
                raise RuntimeError("vídeo indisponível")
            return {"url": "https://stream", "duration": 100}

    monkeypatch.setattr(resolver_mod.yt_dlp, "YoutubeDL", _YdlFalso)
    resolvido = resolver_mod.resolver_stream("Titulo", "Canal", url="https://www.youtube.com/watch?v=abc")
    assert abertos == ["https://www.youtube.com/watch?v=abc", "Canal Titulo"]
    assert resolvido is not None


class _PlayerFalso:
    pausado = False
    posicao_segundos = 0.0
    duracao_segundos = 100.0

    def __init__(self):
        self.tocadas = []

    def observar_fim_de_faixa(self, callback):
        pass

    def definir_volume(self, volume):
        pass

    def definir_repetir_faixa(self, ligado):
        pass

    def tocar(self, resolvido, pausado=False, inicio=None):
        self.tocadas.append(resolvido.title)

    def encerrar(self):
        pass


def test_resolucao_roda_em_thread_e_a_chamada_volta_na_hora(monkeypatch):
    """`tocar_faixa` não espera a rede: o resolvedor só termina depois que a
    chamada já voltou (se rodasse na mesma thread, esperaria o sinal até o
    prazo e o teste falharia). Sem medir relógio, que oscila com a máquina
    carregada."""
    chamada_voltou = threading.Event()
    viu_a_chamada_voltar = []

    def resolver_lento(titulo, artista, url=None):
        viu_a_chamada_voltar.append(chamada_voltou.wait(timeout=5))
        return ResolvedStream(url="u", title=titulo, artist=artista, duration=100, thumbnail=None,
                              source="teste", expires_at=float("inf"))

    monkeypatch.setattr(controlador_mod.orquestrador, "resolver_faixa", resolver_lento)
    monkeypatch.setattr(controlador_mod.ControladorReproducao, "_despachar_envio_votos", lambda self: None)
    ctrl = controlador_mod.ControladorReproducao(player=_PlayerFalso(), midia=False)
    mensagens = []
    ctrl.mensagem.connect(mensagens.append)
    ctrl.tocar_faixa("A", "X")
    chamada_voltou.set()
    assert ctrl.faixa_atual is None and mensagens == ["Carregando X - A…"]
    prazo = time.monotonic() + 10
    while ctrl.faixa_atual is None and time.monotonic() < prazo:
        _APP.processEvents()
        time.sleep(0.01)
    assert viu_a_chamada_voltar == [True]
    assert ctrl.faixa_atual["titulo"] == "A"
    assert ctrl.player.tocadas == ["A"]
    ctrl.encerrar()
    ctrl.deleteLater()
    _APP.processEvents()
