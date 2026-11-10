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

    def observar_erro(self, callback):
        self.erro = callback

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


def _sem_threads(monkeypatch):
    """Resolve na hora, na própria chamada, e não manda voto nenhum ao ECHO:
    os testes do controlador não dependem de thread nem de rede."""
    monkeypatch.setattr(controlador_mod.orquestrador, "resolver_faixa", lambda titulo, artista, url=None: _resolvido(titulo, artista))

    def resolver_na_hora(self, chave, titulo, artista, url=None):
        self._ao_resolver(chave, controlador_mod.orquestrador.resolver_faixa(titulo, artista, url))

    monkeypatch.setattr(controlador_mod.ControladorReproducao, "_despachar_resolucao", resolver_na_hora)
    monkeypatch.setattr(controlador_mod.ControladorReproducao, "_despachar_envio_votos", lambda self: None)


@pytest.fixture
def controlador(monkeypatch):
    _sem_threads(monkeypatch)
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


def test_proxima_pula_faixa_que_nao_resolve(controlador, monkeypatch):
    controlador.tocar_lista([{"titulo": t, "artista": "X"} for t in "ABC"], "playlist:P")
    monkeypatch.setattr(
        controlador_mod.orquestrador, "resolver_faixa",
        lambda titulo, artista, url=None: None if titulo == "B" else _resolvido(titulo, artista),
    )
    controlador.nao_curtir()
    assert controlador.faixa_atual["titulo"] == "C"
    assert _titulos(controlador) == []
    assert controlador_mod.id_faixa("B", "X") in controlador._excluidos_sessao


def test_posicao_parada_recarrega_o_audio_uma_vez(controlador, monkeypatch):
    recargas = []
    controlador.player.diagnostico = lambda: {"paused_for_cache": False, "seeking": False}
    controlador.player.recarregar_audio = lambda: recargas.append(True)
    controlador.tocar_lista([{"titulo": "A", "artista": "X"}], "playlist:P")
    controlador.player.posicao_segundos = 64.0
    agora = [1000.0]
    monkeypatch.setattr(controlador_mod.time, "monotonic", lambda: agora[0])
    controlador._atualizar_progresso()
    for _ in range(3):
        agora[0] += controlador_mod.LIMITE_POSICAO_PARADA + 1
        controlador._atualizar_progresso()
    assert recargas == [True]


def test_curtir_marca_o_voto_da_faixa_atual(controlador):
    votos = []
    controlador.voto_mudou.connect(votos.append)
    controlador.tocar_faixa("A", "X")
    controlador.curtir()
    assert votos[-1] == "positivo"
    assert controlador.voto_local("A", "X") == "positivo"


def test_curtir_de_novo_tira_o_voto(controlador):
    """Pedido do usuário 2026-10-12: clicar de novo no botão já marcado."""
    votos = []
    controlador.voto_mudou.connect(votos.append)
    controlador.tocar_faixa("A", "X")
    controlador.curtir()
    controlador.curtir()
    assert votos[-1] is None
    assert controlador.voto_local("A", "X") is None


def test_trocar_curtir_por_nao_curtir_pela_fila(controlador):
    faixa = {"titulo": "A", "artista": "X"}
    controlador.votar_faixa(faixa, True)
    controlador.votar_faixa(faixa, False)
    assert controlador.voto_local("A", "X") == "negativo"
    controlador.votar_faixa(faixa, True)
    assert controlador.voto_local("A", "X") == "positivo"


def test_nao_curtir_faixa_ja_descurtida_tira_o_voto_sem_pular(controlador):
    controlador.tocar_lista([{"titulo": t, "artista": "X"} for t in "AB"], "playlist:P")
    controlador.votar_faixa(controlador.faixa_atual, False)
    controlador.nao_curtir()
    assert controlador.faixa_atual["titulo"] == "A"
    assert controlador.voto_local("A", "X") is None


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
    _sem_threads(monkeypatch)
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


# ---------------- resolução fora da interface, pré-resolução e falhas ----------------

def _resolvido_valido(titulo, artista):
    resolvido = _resolvido(titulo, artista)
    resolvido.expires_at = float("inf")
    return resolvido


def test_proxima_da_fila_ja_fica_resolvida_e_nao_resolve_de_novo(controlador, monkeypatch):
    pedidos = []

    def resolver(titulo, artista, url=None):
        pedidos.append(titulo)
        return _resolvido_valido(titulo, artista)

    monkeypatch.setattr(controlador_mod.orquestrador, "resolver_faixa", resolver)
    controlador.tocar_lista([{"titulo": t, "artista": "X"} for t in "ABC"], "playlist:P")
    assert pedidos == ["A", "B"]  # B achada com antecedência, enquanto A toca
    controlador.proxima()
    assert controlador.faixa_atual["titulo"] == "B"
    assert pedidos == ["A", "B", "C"]  # B não foi resolvida de novo; C já está a caminho


def test_aleatorio_nao_pre_resolve(controlador, monkeypatch):
    pedidos = []
    monkeypatch.setattr(
        controlador_mod.orquestrador, "resolver_faixa",
        lambda titulo, artista, url=None: pedidos.append(titulo) or _resolvido_valido(titulo, artista),
    )
    controlador.aleatorio = True
    controlador.tocar_lista([{"titulo": t, "artista": "X"} for t in "ABC"], "playlist:P")
    assert pedidos == ["A"]


def test_tocar_faixa_repassa_o_video_exato_da_busca(controlador, monkeypatch):
    urls = []
    monkeypatch.setattr(
        controlador_mod.orquestrador, "resolver_faixa",
        lambda titulo, artista, url=None: urls.append(url) or _resolvido(titulo, artista),
    )
    controlador.tocar_faixa("A", "Canal", origem="busca", url="https://www.youtube.com/watch?v=abc")
    assert urls == ["https://www.youtube.com/watch?v=abc"]
    assert controlador.faixa_atual["origem"] == "busca"


def test_pedido_novo_substitui_o_que_ainda_resolvia(controlador, monkeypatch):
    """Clicar em outra faixa enquanto a primeira ainda resolve: só a última toca."""
    pendentes = []
    monkeypatch.setattr(
        controlador_mod.ControladorReproducao, "_despachar_resolucao",
        lambda self, chave, titulo, artista, url=None: pendentes.append((chave, titulo, artista)),
    )
    controlador.tocar_faixa("A", "X")
    controlador.tocar_faixa("B", "X")
    for chave, titulo, artista in pendentes:
        controlador._ao_resolver(chave, _resolvido(titulo, artista))
    assert controlador.faixa_atual["titulo"] == "B"
    assert [t[0] for t in controlador.player.tocadas] == ["B"]


def test_sem_internet_para_depois_de_algumas_falhas(controlador, monkeypatch):
    controlador.tocar_faixa("A", "X")
    monkeypatch.setattr(controlador_mod.orquestrador, "resolver_faixa", lambda titulo, artista, url=None: None)
    monkeypatch.setattr(controlador, "iniciar_caos", lambda semente=None: None)
    for letra in "BCDEFGHIJ":
        controlador.fila.adicionar(letra, "X")
    controlador.proxima()
    assert controlador.faixa_atual["titulo"] == "A"
    # parou na 5ª falha: não esvaziou a fila inteira tentando
    assert len(controlador.fila) == 9 - controlador_mod.MAXIMO_FALHAS_SEGUIDAS


def test_erro_do_mpv_resolve_de_novo_e_continua_da_mesma_posicao(controlador):
    controlador.tocar_faixa("A", "X")
    controlador.player.posicao_segundos = 95.0
    controlador._atualizar_progresso()
    controlador.player.posicao_segundos = None  # o MPV largou a faixa
    controlador._ao_erro_do_player()
    assert controlador.player.tocadas[-1] == ("A", False, 95.0)
    assert controlador.faixa_atual["titulo"] == "A"
    assert len(controlador._historico_sessao) == 1  # não conta como outra reprodução


def test_segundo_erro_do_mpv_na_mesma_faixa_pula_para_a_proxima(controlador):
    controlador.tocar_lista([{"titulo": t, "artista": "X"} for t in "AB"], "playlist:P")
    controlador._ao_erro_do_player()
    controlador._ao_erro_do_player()
    assert controlador.faixa_atual["titulo"] == "B"


def test_mpv_sem_faixa_com_a_interface_tocando_recupera(controlador, monkeypatch):
    controlador.player.diagnostico = lambda: {"idle_active": True, "core_idle": True}
    controlador.player.recarregar_audio = lambda: None
    controlador.tocar_faixa("A", "X")
    controlador.player.posicao_segundos = 44.0
    agora = [1000.0]
    monkeypatch.setattr(controlador_mod.time, "monotonic", lambda: agora[0])
    controlador._atualizar_progresso()
    agora[0] += controlador_mod.LIMITE_POSICAO_PARADA + 1
    controlador._atualizar_progresso()
    assert controlador.player.tocadas[-1] == ("A", False, 44.0)


def test_voto_fica_pendente_para_o_echo(controlador):
    from siren.core import votos_pendentes as votos_pendentes_mod
    controlador.votar_faixa({"titulo": "A", "artista": "X"}, True)
    controlador.votar_faixa({"titulo": "A", "artista": "X"}, False)
    pendentes = votos_pendentes_mod.listar()
    assert [(p["titulo"], p["voto"]) for p in pendentes] == [("A", "negativo")]  # só o mais recente
