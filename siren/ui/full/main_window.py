# -*- coding: utf-8 -*-
"""Janela do Modo Completo do SIREN - vidro fosco (Acrylic) tipo Argus,
biblioteca/playlists/fila/favoritos por cima do MESMO motor de reprodução
do Modo Leve (MPV + Playback Resolver + orquestrador compartilhado, ver
`playback/orquestrador.py`).

Biblioteca ainda mostra um aviso "em construção" (ver docs/TODO.md)."""
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSlider, QStackedWidget, QStyle,
    QVBoxLayout, QWidget,
)

from siren.core import config as config_mod
from siren.core import favoritos as favoritos_mod
from siren.core import playlists as playlists_mod
from siren.core.fila import Fila
from siren.integrations import echo_client
from siren.integrations.loki_events import PublicadorPlayback
from siren.playback import orquestrador
from siren.playback.player import Player
from siren.ui import chrome
from siren.ui import mode_switch
from siren.ui.full import styles
from siren.ui.full.import_worker import EchoStatusWorker, ImportEchoVotesWorker
from siren.ui.full.views.busca import ViewBusca
from siren.ui.full.views.descoberta import ViewDescoberta
from siren.ui.full.views.fila import ViewFila
from siren.ui.full.views.historico import ViewHistorico
from siren.ui.full.views.inicio import ViewInicio
from siren.ui.full.views.playlists import ViewPlaylists
from siren.ui.full.views.tocando_agora import ViewTocandoAgora

# Origens que contam como "descoberta do ECHO" pra fins da playlist
# automática "Descobertas do SIREN" (seção 11 do ECHO_SPEC original,
# adaptada - ver core/playlists.py::adicionar_a_descobertas). Faixa que veio
# de playlist/favoritos/histórico/busca própria NUNCA entra aqui - só o que
# o ECHO de fato descobriu pra você.
ORIGENS_DESCOBERTA = {"caos", "descoberta"}

class _SliderSeek(QSlider):
    """QSlider cujo clique pula exatamente para o ponto apontado."""

    seek_solicitado = Signal(int)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() != Qt.LeftButton:
            return
        valor = QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(), round(event.position().x()), max(1, self.width()),
        )
        self.setValue(valor)
        self.seek_solicitado.emit(valor)


class FullWindow(QWidget):
    # Ver mesmo comentário em ui/main_window.py::MainWindow.sinal_fim_de_faixa
    # - o callback do MPV roda na thread dele, nunca a do Qt; Signal é a
    # forma segura de marshaling de volta pra GUI thread.
    sinal_fim_de_faixa = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SIREN")
        self.resize(1180, 760)

        self._player = Player()
        self._eventos_loki = PublicadorPlayback()
        self._player.definir_volume(config_mod.obter("volume_inicial"))
        self._player.observar_fim_de_faixa(self.sinal_fim_de_faixa.emit)
        self.sinal_fim_de_faixa.connect(self._ao_fim_de_faixa)
        self._faixa_atual = None
        self._duracao_atual = 0
        self._historico_sessao = []  # pilha simples pro ⏮ - mesma ideia do Modo Leve, sem persistência
        self._excluidos_sessao = []
        self._fila = Fila()
        self._migrar_favoritos_legados()

        cor_fundo = styles.COR_FUNDO
        estado = chrome.configurar_janela_vidro_fosco(
            self, cor_fundo, alpha=130, acrylic_ativado=config_mod.obter("acrylic_ativado"),
        )
        folha_estilo = styles.QSS
        if not estado["acrylic_ok"]:
            # Sem suporte a Acrylic (Windows mais antigo, ou não-Windows) -
            # reforça um fundo sólido pra não sobrar texto sem nada atrás.
            folha_estilo += f"\nFullWindow {{ background: {cor_fundo}; }}"
        self.setStyleSheet(folha_estilo)

        self._barra_titulo = chrome.BarraTitulo(self, "SIREN")
        self._sidebar = self._construir_sidebar()
        self._stack = QStackedWidget()
        self._views = self._construir_views()
        for view in self._views.values():
            self._stack.addWidget(view)

        corpo = QWidget()
        layout_corpo = QVBoxLayout(corpo)
        layout_corpo.setContentsMargins(0, 0, 0, 0)
        layout_corpo.setSpacing(0)
        layout_corpo.addWidget(self._construir_topbar())
        layout_corpo.addWidget(self._stack, stretch=1)

        conteudo = QWidget()
        layout_conteudo = QHBoxLayout(conteudo)
        layout_conteudo.setContentsMargins(0, 0, 0, 0)
        layout_conteudo.setSpacing(0)
        layout_conteudo.addWidget(self._sidebar)
        layout_conteudo.addWidget(corpo, stretch=1)

        self._barra_player = self._construir_barra_player()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._barra_titulo)
        layout.addWidget(conteudo, stretch=1)
        layout.addWidget(self._barra_player)

        self._atualizar_sidebar_playlists()
        self._mudar_view("home")
        self._sincronizar_votos_echo()

    # ---------------- sidebar ----------------

    def _construir_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        # QWidget puro não pinta o próprio "background" do QSS sozinho -
        # sem isso o tom mais escuro de #sidebar (ver styles.py) nunca
        # aparecia, ficava indistinguível do resto do vidro fosco (mesmo
        # motivo do fix de clique-através em chrome.py::BarraTitulo).
        sidebar.setAttribute(Qt.WA_StyledBackground, True)
        sidebar.setFixedWidth(260)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(2)

        logo = QLabel("Siren")
        logo.setObjectName("logoSiren")
        layout.addWidget(logo)

        self._echo_pill = QLabel("verificando ECHO...")
        self._echo_pill.setObjectName("echoPill")
        layout.addWidget(self._echo_pill)
        layout.addSpacing(12)

        self._botao_home = QPushButton("⌂  Início")
        self._botao_home.setObjectName("navBotao")
        self._botao_home.setCheckable(True)
        self._botao_home.clicked.connect(lambda: self._mudar_view("home"))
        layout.addWidget(self._botao_home)

        self._botao_descoberta = QPushButton("🔍  Descoberta")
        self._botao_descoberta.setObjectName("navBotao")
        self._botao_descoberta.setCheckable(True)
        self._botao_descoberta.clicked.connect(lambda: self._mudar_view("descoberta"))
        layout.addWidget(self._botao_descoberta)

        self._botao_historico = QPushButton("🕐  Histórico")
        self._botao_historico.setObjectName("navBotao")
        self._botao_historico.setCheckable(True)
        self._botao_historico.clicked.connect(lambda: self._mudar_view("historico"))
        layout.addWidget(self._botao_historico)
        layout.addSpacing(18)

        linha_biblioteca = QHBoxLayout()
        titulo_biblioteca = QLabel("Sua biblioteca")
        titulo_biblioteca.setObjectName("tituloBiblioteca")
        botao_criar = QPushButton("+")
        botao_criar.setObjectName("botaoBiblioteca")
        botao_criar.setToolTip("Criar playlist")
        botao_criar.setFixedSize(30, 30)
        botao_criar.clicked.connect(self._criar_playlist)
        linha_biblioteca.addWidget(titulo_biblioteca)
        linha_biblioteca.addStretch()
        linha_biblioteca.addWidget(botao_criar)
        layout.addLayout(linha_biblioteca)

        self._lista_biblioteca = QListWidget()
        self._lista_biblioteca.setObjectName("listaBiblioteca")
        self._lista_biblioteca.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._lista_biblioteca.itemActivated.connect(self._abrir_playlist_item)
        layout.addWidget(self._lista_biblioteca, stretch=1)

        botao_importar = QPushButton("Importar playlist")
        botao_importar.setObjectName("navBotao")
        botao_importar.clicked.connect(lambda: self._mudar_view("playlists"))
        layout.addWidget(botao_importar)

        botao_modo_leve = QPushButton("← Modo Leve")
        botao_modo_leve.setObjectName("botaoSecundario")
        botao_modo_leve.clicked.connect(self._trocar_pro_leve)
        layout.addWidget(botao_modo_leve)

        return sidebar

    def _construir_topbar(self):
        topo = QWidget()
        topo.setObjectName("topBar")
        topo.setAttribute(Qt.WA_StyledBackground, True)
        layout = QHBoxLayout(topo)
        layout.setContentsMargins(22, 10, 22, 10)

        botao_inicio = QPushButton("⌂")
        botao_inicio.setObjectName("botaoCircular")
        botao_inicio.setFixedSize(38, 38)
        botao_inicio.setToolTip("Início")
        botao_inicio.clicked.connect(lambda: self._mudar_view("home"))

        self._campo_busca = QLineEdit()
        self._campo_busca.setObjectName("buscaGlobal")
        self._campo_busca.setPlaceholderText("O que você quer ouvir?")
        self._campo_busca.setClearButtonEnabled(True)
        self._campo_busca.setMaximumWidth(470)
        self._campo_busca.returnPressed.connect(self._buscar)

        layout.addWidget(botao_inicio)
        layout.addWidget(self._campo_busca)
        layout.addStretch()
        return topo

    def _buscar(self):
        texto = self._campo_busca.text().strip()
        if not texto:
            return
        self._mudar_view("search", atualizar=False)
        self._views["search"].buscar(texto)

    def _criar_playlist(self):
        nome, ok = QInputDialog.getText(self, "Criar playlist", "Nome da playlist:")
        if not (ok and nome.strip()):
            return
        playlists_mod.criar(nome.strip())
        self._atualizar_sidebar_playlists()
        self._abrir_playlist(nome.strip())

    def _atualizar_sidebar_playlists(self):
        self._lista_biblioteca.clear()
        especiais = [
            (playlists_mod.NOME_PLAYLIST_CURTIDAS, "♥  Músicas Curtidas"),
            (playlists_mod.NOME_PLAYLIST_NAO_CURTIDAS, "⊘  Não Curtidas"),
        ]
        especiais_nomes = {nome for nome, _rotulo in especiais}
        for nome, rotulo in especiais:
            quantidade = len(playlists_mod.obter_faixas(nome))
            item = QListWidgetItem(f"{rotulo}\n    Playlist · {quantidade} músicas")
            item.setData(Qt.UserRole, nome)
            self._lista_biblioteca.addItem(item)
        for playlist in playlists_mod.listar():
            if playlist["nome"] in especiais_nomes:
                continue
            item = QListWidgetItem(
                f"♫  {playlist['nome']}\n    Playlist · {playlist['quantidade']} músicas"
            )
            item.setData(Qt.UserRole, playlist["nome"])
            self._lista_biblioteca.addItem(item)

    @staticmethod
    def _migrar_favoritos_legados():
        """Preserva estrelas antigas ao unificar Favoritos e Curtidas."""
        for faixa in favoritos_mod.carregar():
            playlists_mod.registrar_voto(faixa["titulo"], faixa["artista"], positivo=True)

    def _sincronizar_votos_echo(self):
        self._worker_votos = ImportEchoVotesWorker(self)
        self._worker_votos.concluido.connect(self._aplicar_votos_echo)
        self._worker_votos.finished.connect(self._worker_votos.deleteLater)
        self._worker_votos.start()

    def _aplicar_votos_echo(self, aprovadas, desaprovadas):
        for faixa in aprovadas:
            playlists_mod.registrar_voto(faixa["titulo"], faixa["artista"], positivo=True)
        for faixa in desaprovadas:
            playlists_mod.registrar_voto(faixa["titulo"], faixa["artista"], positivo=False)
        if aprovadas or desaprovadas:
            self._atualizar_sidebar_playlists()
            if self._stack.currentWidget() is self._views["home"]:
                self._views["home"].atualizar_biblioteca()

    def _abrir_playlist_item(self, item):
        self._abrir_playlist(item.data(Qt.UserRole))

    def _abrir_playlist(self, nome):
        self._views["playlists"].abrir(nome)
        self._stack.setCurrentWidget(self._views["playlists"])
        self._botao_home.setChecked(False)

    def _trocar_pro_leve(self):
        mode_switch.trocar_modo(QApplication.instance(), self, "lite")

    def _construir_views(self):
        return {
            "home": ViewInicio(
                ao_tocar=self._tocar_faixa,
                ao_abrir_playlist=self._abrir_playlist,
                ao_iniciar_caos=self._pedir_caos,
            ),
            "now": ViewTocandoAgora(ao_iniciar_caos=self._pedir_caos, player=self._player),
            "playlists": ViewPlaylists(ao_tocar=self._tocar_faixa, fila=self._fila),
            "queue": ViewFila(self._fila, ao_tocar=self._tocar_faixa),
            "search": ViewBusca(ao_tocar=self._tocar_faixa),
            "descoberta": ViewDescoberta(ao_tocar=self._tocar_faixa),
            "historico": ViewHistorico(ao_tocar=self._tocar_faixa, fila=self._fila),
        }

    def _mudar_view(self, chave, atualizar=True):
        self._stack.setCurrentWidget(self._views[chave])
        if atualizar:
            self._views[chave].atualizar()
        self._botao_home.setChecked(chave == "home")
        self._botao_descoberta.setChecked(chave == "descoberta")
        self._botao_historico.setChecked(chave == "historico")
        if chave == "home":
            self._atualizar_sidebar_playlists()
        self._atualizar_pill_echo()

    def _atualizar_pill_echo(self):
        worker_atual = getattr(self, "_worker_status_echo", None)
        if worker_atual is not None and worker_atual.isRunning():
            return
        self._echo_pill.setText("○ verificando ECHO…")
        worker = EchoStatusWorker(self)
        worker.concluido.connect(self._mostrar_status_echo)
        worker.finished.connect(lambda w=worker: self._finalizar_status_echo(w))
        self._worker_status_echo = worker
        worker.start()

    def _mostrar_status_echo(self, conectado):
        self._echo_pill.setText(
            "● ECHO conectado" if conectado else "○ ECHO offline, tocando sem ele"
        )

    def _finalizar_status_echo(self, worker):
        if worker is self._worker_status_echo:
            self._worker_status_echo = None
        worker.deleteLater()

    # ---------------- barra de player ----------------

    def _construir_barra_player(self):
        barra = QWidget()
        barra.setObjectName("playerBar")
        barra.setAttribute(Qt.WA_StyledBackground, True)  # ver comentário em _construir_sidebar
        barra.setFixedHeight(92)
        layout = QHBoxLayout(barra)
        layout.setContentsMargins(16, 8, 18, 8)
        layout.setSpacing(12)

        capa = QLabel("♫")
        capa.setObjectName("capaPlayer")
        capa.setAlignment(Qt.AlignCenter)
        capa.setFixedSize(56, 56)

        self._label_faixa_atual = QLabel("Nenhuma faixa")
        self._label_faixa_atual.setStyleSheet("font-weight: 700;")
        self._label_artista_atual = QLabel("")
        self._label_artista_atual.setObjectName("legendaView")
        bloco_texto = QVBoxLayout()
        bloco_texto.setSpacing(0)
        bloco_texto.addWidget(self._label_faixa_atual)
        bloco_texto.addWidget(self._label_artista_atual)

        botao_anterior = QPushButton("⏮")
        botao_anterior.setObjectName("botaoIcone")
        botao_anterior.setFixedSize(30, 30)
        botao_anterior.clicked.connect(self._tocar_anterior)

        self._botao_play_pause = QPushButton("▶")
        self._botao_play_pause.setObjectName("botaoAccent")
        self._botao_play_pause.setFixedSize(38, 38)
        self._botao_play_pause.clicked.connect(self._alternar_play_pause)

        botao_proximo = QPushButton("⏭")
        botao_proximo.setObjectName("botaoIcone")
        botao_proximo.setFixedSize(30, 30)
        botao_proximo.clicked.connect(self._tocar_proxima)

        self._botao_dislike = QPushButton("👎")
        self._botao_dislike.setObjectName("botaoDislike")
        self._botao_dislike.setCheckable(True)
        self._botao_dislike.setFixedSize(30, 30)
        self._botao_dislike.clicked.connect(self._dislike)

        self._botao_like = QPushButton("❤️")
        self._botao_like.setObjectName("botaoLike")
        self._botao_like.setCheckable(True)
        self._botao_like.setFixedSize(30, 30)
        self._botao_like.clicked.connect(self._like)

        self._slider_progresso = _SliderSeek(Qt.Horizontal)
        self._slider_progresso.setRange(0, 0)
        self._slider_progresso.setEnabled(False)
        self._slider_progresso.seek_solicitado.connect(self._buscar_posicao)
        self._label_tempo_decorrido = QLabel("0:00")
        self._label_tempo_decorrido.setObjectName("tempoPlayer")
        self._label_tempo_total = QLabel("0:00")
        self._label_tempo_total.setObjectName("tempoPlayer")

        self._timer_progresso = QTimer(self)
        self._timer_progresso.setInterval(500)
        self._timer_progresso.timeout.connect(self._atualizar_progresso)
        self._timer_progresso.start()

        self._slider_volume = QSlider(Qt.Horizontal)
        self._slider_volume.setRange(0, 100)
        self._slider_volume.setValue(config_mod.obter("volume_inicial"))
        self._slider_volume.setFixedWidth(90)
        self._slider_volume.valueChanged.connect(self._player.definir_volume)

        controles = QHBoxLayout()
        controles.setSpacing(8)
        controles.addStretch()
        controles.addWidget(botao_anterior)
        controles.addWidget(self._botao_play_pause)
        controles.addWidget(botao_proximo)
        controles.addStretch()

        progresso = QHBoxLayout()
        progresso.setSpacing(8)
        progresso.addWidget(self._label_tempo_decorrido)
        progresso.addWidget(self._slider_progresso, stretch=1)
        progresso.addWidget(self._label_tempo_total)

        centro = QVBoxLayout()
        centro.setSpacing(1)
        centro.addLayout(controles)
        centro.addLayout(progresso)

        botao_letras = QPushButton("Letras")
        botao_letras.setObjectName("botaoPlayerTexto")
        botao_letras.clicked.connect(lambda: self._mudar_view("now"))
        botao_fila = QPushButton("Fila")
        botao_fila.setObjectName("botaoPlayerTexto")
        botao_fila.clicked.connect(lambda: self._mudar_view("queue"))

        layout.addWidget(capa)
        layout.addLayout(bloco_texto)
        layout.addWidget(self._botao_like)
        layout.addLayout(centro, stretch=1)
        layout.addWidget(self._botao_dislike)
        layout.addWidget(botao_letras)
        layout.addWidget(botao_fila)
        layout.addWidget(QLabel("🔊"))
        layout.addWidget(self._slider_volume)

        self._definir_controles_habilitados(False)
        return barra

    def _definir_controles_habilitados(self, habilitado):
        for botao in (self._botao_dislike, self._botao_like, self._botao_play_pause):
            botao.setEnabled(habilitado)

    @staticmethod
    def _id_faixa(titulo, artista):
        return f"{artista.strip().lower()}::{titulo.strip().lower()}"

    # ---------------- reprodução ----------------

    def _pedir_caos(self):
        faixa = echo_client.sugerir_semente(excluidos=self._excluidos_sessao)
        if faixa is None:
            self._label_faixa_atual.setText("ECHO indisponível ou sem sugestão agora")
            return
        self._tocar_faixa(faixa["titulo"], faixa["artista"], origem="caos")

    def _tocar_proxima(self):
        """A fila local tem prioridade (mesmo autoridade que o docs/PLANO_SIREN.md
        estabelece pro SIREN sobre o ECHO); só pede ao ECHO quando ela está
        vazia."""
        proxima = self._fila.proxima()
        if proxima:
            self._tocar_faixa(proxima["titulo"], proxima["artista"], origem=proxima.get("origem", "fila"))
            return
        if self._faixa_atual is None:
            self._pedir_caos()
            return
        faixa = echo_client.sugerir_proxima(
            self._faixa_atual["artista"], self._faixa_atual["titulo"], excluidos=self._excluidos_sessao,
        )
        if faixa is None:
            self._label_faixa_atual.setText("ECHO não encontrou continuação agora")
            return
        self._tocar_faixa(faixa["titulo"], faixa["artista"], origem="caos")

    def _ao_fim_de_faixa(self):
        self._eventos_loki.faixa_encerrada("fim")
        self._tocar_proxima()

    def _tocar_anterior(self):
        if len(self._historico_sessao) < 2:
            return
        self._historico_sessao.pop()
        anterior = self._historico_sessao.pop()
        self._tocar_faixa(anterior["titulo"], anterior["artista"], origem=anterior.get("origem", "fila"))

    def _tocar_faixa(self, titulo, artista, origem="fila"):
        resolvido = orquestrador.tocar_faixa(self._player, titulo, artista, origem=origem)
        if resolvido is None:
            self._label_faixa_atual.setText(f"Não consegui resolver \"{artista} - {titulo}\"")
            return
        self._faixa_atual = {"titulo": titulo, "artista": artista, "origem": origem}
        self._historico_sessao.append(self._faixa_atual)
        self._excluidos_sessao.append(self._id_faixa(titulo, artista))

        self._label_faixa_atual.setText(titulo)
        self._label_artista_atual.setText(artista)
        self._views["now"].definir_faixa_atual(titulo, artista, resolvido.duration)
        self._duracao_atual = max(0, int(resolvido.duration or 0))
        self._slider_progresso.setRange(0, self._duracao_atual)
        self._slider_progresso.setValue(0)
        self._slider_progresso.setEnabled(bool(self._duracao_atual))
        self._label_tempo_decorrido.setText("0:00")
        self._label_tempo_total.setText(self._formatar_tempo(self._duracao_atual))
        self._botao_play_pause.setText("⏸")
        self._definir_controles_habilitados(True)

        voto = echo_client.obter_voto(artista, titulo)
        self._botao_like.setChecked(voto == "positivo")
        self._botao_dislike.setChecked(voto == "negativo")
        self._eventos_loki.faixa_iniciada(
            titulo,
            artista,
            origem=origem,
            duracao=resolvido.duration,
        )

    def _alternar_play_pause(self):
        self._player.alternar_pausa()
        self._botao_play_pause.setText("▶" if self._player.pausado else "⏸")
        self._eventos_loki.pausa_alterada(self._player.pausado)

    @staticmethod
    def _formatar_tempo(segundos):
        segundos = max(0, int(segundos or 0))
        return f"{segundos // 60}:{segundos % 60:02d}"

    def _buscar_posicao(self, segundos):
        if self._faixa_atual:
            self._player.buscar_posicao(segundos)

    def _atualizar_progresso(self):
        if not self._faixa_atual:
            return
        duracao_player = self._player.duracao_segundos
        if duracao_player:
            self._duracao_atual = max(0, int(duracao_player))
        posicao = self._player.posicao_segundos or 0
        self._eventos_loki.progresso(posicao, self._duracao_atual)
        if self._duracao_atual:
            self._slider_progresso.setEnabled(True)
            self._slider_progresso.setRange(0, self._duracao_atual)
            if not self._slider_progresso.isSliderDown():
                self._slider_progresso.setValue(min(int(posicao), self._duracao_atual))
        self._label_tempo_decorrido.setText(self._formatar_tempo(posicao))
        self._label_tempo_total.setText(self._formatar_tempo(self._duracao_atual))

    def _like(self):
        if not self._faixa_atual:
            return
        echo_client.enviar_feedback(self._faixa_atual["artista"], self._faixa_atual["titulo"], "positivo")
        self._botao_like.setChecked(True)
        self._botao_dislike.setChecked(False)
        playlists_mod.registrar_voto(
            self._faixa_atual["titulo"], self._faixa_atual["artista"], positivo=True,
        )
        if self._faixa_atual["origem"] in ORIGENS_DESCOBERTA:
            playlists_mod.adicionar_a_descobertas(self._faixa_atual["titulo"], self._faixa_atual["artista"])
        self._atualizar_sidebar_playlists()

    def _dislike(self):
        if not self._faixa_atual:
            return
        echo_client.enviar_feedback(self._faixa_atual["artista"], self._faixa_atual["titulo"], "negativo")
        self._botao_dislike.setChecked(True)
        self._botao_like.setChecked(False)
        playlists_mod.registrar_voto(
            self._faixa_atual["titulo"], self._faixa_atual["artista"], positivo=False,
        )
        self._atualizar_sidebar_playlists()
        self._tocar_proxima()

    def closeEvent(self, event):
        self._eventos_loki.faixa_encerrada("player_fechado")
        self._player.encerrar()
        super().closeEvent(event)


def criar_aplicacao():
    app = QApplication.instance() or QApplication([])
    janela = FullWindow()
    return app, janela
