# -*- coding: utf-8 -*-
"""Controlador de reprodução com um player falso - sem MPV, sem rede."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from siren.core import playlists as playlists_mod
from siren.core import sessao as sessao_mod
from siren.playback import controlador as controlador_mod
from siren.playback.resolver import ResolvedStream

# Referência no módulo: um QApplication criado e descartado dentro do
# fixture era destruído na hora, e os testes de interface seguintes criavam
# outro por cima - o Qt abortava o processo inteiro (achado 2026-09-26).
_APP = QApplication.instance() or QApplication([])


class _PlayerFalso:
    def __init__(self):
        self.pausado = False
        self.posicao_segundos = 0.0
        self.duracao_segundos = 200.0
        self.tocadas = []
        self.repetir_faixa = False
        self.encerrado = False

    def observar_fim_de_faixa(self, callback):
        self.fim = callback

    def definir_volume(self, volume):
        pass

    def definir_repetir_faixa(self, ligado):
        self.repetir_faixa = ligado

    def tocar(self, resolvido, pausado=False, inicio=None):
        self.pausado = pausado
        self.posicao_segundos = inicio or 0.0
        self.tocadas.append((resolvido.title, pausado, inicio))

    def alternar_pausa(self):
        self.pausado = not self.pausado

    def buscar_posicao(self, segundos):
        self.posicao_segundos = segundos

    def encerrar(self):
        self.encerrado = True


def _resolvido(titulo, artista):
    return ResolvedStream(url=f"url:{titulo}", title=titulo, artist=artista, duration=200, thumbnail=None,
                          source="teste", expires_at=0)


@pytest.fixture
def controlador(monkeypatch):
    def tocar_falso(player, titulo, artista, origem="fila"):
        resolvido = _resolvido(titulo, artista)
        player.tocar(resolvido)
        return resolvido

    monkeypatch.setattr(controlador_mod.orquestrador, "tocar_faixa", tocar_falso)
    monkeypatch.setattr(controlador_mod.echo_client, "enviar_feedback", lambda *a, **k: None)
    ctrl = controlador_mod.ControladorReproducao(player=_PlayerFalso(), midia=False)
    yield ctrl
    ctrl.encerrar()
    # Libera o QObject agora, de forma controlada - deixado pro coletor de
    # lixo, ele era destruído no meio do processEvents de outro teste e o Qt
    # abortava o processo (achado 2026-09-26).
    ctrl.deleteLater()
    _APP.processEvents()


def _titulos(ctrl):
    return [f["titulo"] for f in ctrl.fila.listar()]


def test_tocar_lista_toca_a_primeira_e_enfileira_o_resto(controlador):
    controlador.tocar_lista([{"titulo": t, "artista": "X"} for t in "ABC"], "playlist:P")
    assert controlador.faixa_atual["titulo"] == "A"
    assert _titulos(controlador) == ["B", "C"]
    assert controlador.tocando


def test_proxima_com_repetir_fila_recicla_a_atual(controlador):
    controlador.tocar_lista([{"titulo": t, "artista": "X"} for t in "AB"], "playlist:P")
    controlador.repetir = "fila"
    controlador.proxima()
    assert controlador.faixa_atual["titulo"] == "B"
    assert _titulos(controlador) == ["A"]


def test_nao_curtir_pula_sem_reciclar_e_registra_o_voto(controlador):
    controlador.tocar_lista([{"titulo": t, "artista": "X"} for t in "AB"], "playlist:P")
    controlador.repetir = "fila"
    controlador.nao_curtir()
    assert controlador.faixa_atual["titulo"] == "B"
    assert _titulos(controlador) == []
    nao_curtidas = playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_NAO_CURTIDAS)
    assert {"titulo": "A", "artista": "X"} in nao_curtidas


def test_curtir_marca_o_voto_da_faixa_atual(controlador):
    votos = []
    controlador.voto_mudou.connect(votos.append)
    controlador.tocar_faixa("A", "X")
    controlador.curtir()
    assert votos[-1] == "positivo"
    assert controlador.voto_local("A", "X") == "positivo"


def test_alternar_repetir_percorre_os_tres_modos(controlador):
    controlador.repetir = "desligado"
    modos = []
    for _ in range(3):
        controlador.alternar_repetir()
        modos.append((controlador.repetir, controlador.player.repetir_faixa))
    assert modos == [("fila", False), ("faixa", True), ("desligado", False)]


def test_encerrar_salva_a_sessao(controlador):
    controlador.tocar_faixa("Levels", "Avicii", origem="caos")
    controlador.player.posicao_segundos = 42.0
    controlador.encerrar()
    dados = sessao_mod.carregar()
    assert (dados["titulo"], dados["posicao"], dados["continuar"]) == ("Levels", 42.0, False)
    assert controlador.player.encerrado


def test_troca_de_modo_so_espera_se_estiver_tocando(controlador):
    controlador.tocar_faixa("Levels", "Avicii")
    controlador.alternar_play_pause()  # pausa
    assert controlador.iniciar_troca_de_modo() is False
    controlador.alternar_play_pause()  # volta a tocar
    assert controlador.iniciar_troca_de_modo() is True
    assert sessao_mod.carregar()["continuar"] is True


def test_troca_concluida_quando_a_outra_janela_avisa(controlador):
    avisos = []
    controlador.troca_concluida.connect(lambda: avisos.append(True))
    controlador.tocar_faixa("Levels", "Avicii")
    controlador.iniciar_troca_de_modo()
    sessao_mod.sinalizar_troca_concluida(os.getpid())
    controlador._acompanhar_troca_de_modo()
    assert avisos == [True]
    controlador.encerrar()
    # Depois da troca, a sessão é da outra janela: encerrar não sobrescreve.
    assert sessao_mod.carregar()["continuar"] is True


class _MidiaFalsa(controlador_mod.QObject):
    from PySide6.QtCore import Signal as _Signal
    botao = _Signal(str)

    def __init__(self):
        super().__init__()
        self.faixas = []
        self.estados = []

    def definir_faixa(self, titulo, artista, url_capa=None):
        self.faixas.append((titulo, artista))

    def definir_tocando(self, tocando):
        self.estados.append(tocando)

    def encerrar(self):
        pass


def test_teclas_multimidia_controlam_o_player(monkeypatch):
    def tocar_falso(player, titulo, artista, origem="fila"):
        resolvido = _resolvido(titulo, artista)
        player.tocar(resolvido)
        return resolvido

    monkeypatch.setattr(controlador_mod.orquestrador, "tocar_faixa", tocar_falso)
    midia = _MidiaFalsa()
    ctrl = controlador_mod.ControladorReproducao(player=_PlayerFalso(), midia=midia)
    ctrl.tocar_lista([{"titulo": t, "artista": "X"} for t in "ABC"], "playlist:P")
    assert midia.faixas[-1] == ("A", "X") and midia.estados[-1] is True

    midia.botao.emit("play")  # já tocando: play não faz nada
    assert ctrl.tocando
    midia.botao.emit("pause")
    assert not ctrl.tocando and ctrl.player.pausado
    midia.botao.emit("play")
    assert ctrl.tocando
    midia.botao.emit("proxima")
    assert ctrl.faixa_atual["titulo"] == "B"
    midia.botao.emit("anterior")
    assert ctrl.faixa_atual["titulo"] == "A"
    midia.botao.emit("parar")
    assert not ctrl.tocando
    ctrl.encerrar()
    ctrl.deleteLater()
    _APP.processEvents()
