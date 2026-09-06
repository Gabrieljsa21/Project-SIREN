# -*- coding: utf-8 -*-
"""Janela do Modo Completo do SIREN - vidro fosco (Acrylic) tipo Argus,
biblioteca/playlists/fila/favoritos por cima do MESMO motor de reprodução
do Modo Leve (MPV + Playback Resolver + orquestrador compartilhado, ver
`playback/orquestrador.py`).

Biblioteca e Busca própria ainda mostram um aviso "em construção" (ver
TODO.md) - entregar o resto funcionando é melhor que atrasar tudo esperando
ficar completo de uma vez."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QHBoxLayout, QLabel, QPushButton,
    QSlider, QStackedWidget, QVBoxLayout, QWidget,
)

from siren.core import config as config_mod
from siren.core import favoritos as favoritos_mod
from siren.core import playlists as playlists_mod
from siren.core.fila import Fila
from siren.integrations import echo_client
from siren.playback import orquestrador
from siren.playback.player import Player
from siren.ui import chrome
from siren.ui import mode_switch
from siren.ui.full import styles
from siren.ui.full.views.descoberta import ViewDescoberta
from siren.ui.full.views.em_construcao import ViewEmConstrucao
from siren.ui.full.views.favoritos import ViewFavoritos
from siren.ui.full.views.fila import ViewFila
from siren.ui.full.views.historico import ViewHistorico
from siren.ui.full.views.playlists import ViewPlaylists
from siren.ui.full.views.tocando_agora import ViewTocandoAgora

# Origens que contam como "descoberta do ECHO" pra fins da playlist
# automática "Descobertas do SIREN" (seção 11 do ECHO_SPEC original,
# adaptada - ver core/playlists.py::adicionar_a_descobertas). Faixa que veio
# de playlist/favoritos/histórico/busca própria NUNCA entra aqui - só o que
# o ECHO de fato descobriu pra você.
ORIGENS_DESCOBERTA = {"caos", "descoberta"}

NAVEGACAO = [
    ("now", "Tocando agora"),
    ("discover", "Descoberta"),
    ("library", "Biblioteca"),
    ("playlists", "Playlists"),
    ("favorites", "Favoritos"),
    ("queue", "Fila"),
    ("history", "Histórico"),
    ("search", "Busca"),
]


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
        self._player.definir_volume(config_mod.obter("volume_inicial"))
        self._player.observar_fim_de_faixa(self.sinal_fim_de_faixa.emit)
        self.sinal_fim_de_faixa.connect(self._tocar_proxima)
        self._faixa_atual = None
        self._historico_sessao = []  # pilha simples pro ⏮ - mesma ideia do Modo Leve, sem persistência
        self._excluidos_sessao = []
        self._fila = Fila()

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
        self._sidebar, self._botoes_nav = self._construir_sidebar()
        self._stack = QStackedWidget()
        self._views = self._construir_views()
        for view in self._views.values():
            self._stack.addWidget(view)

        conteudo = QWidget()
        layout_conteudo = QHBoxLayout(conteudo)
        layout_conteudo.setContentsMargins(0, 0, 0, 0)
        layout_conteudo.setSpacing(0)
        layout_conteudo.addWidget(self._sidebar)
        layout_conteudo.addWidget(self._stack, stretch=1)

        self._barra_player = self._construir_barra_player()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._barra_titulo)
        layout.addWidget(conteudo, stretch=1)
        layout.addWidget(self._barra_player)

        self._mudar_view("now")

    # ---------------- sidebar ----------------

    def _construir_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        # QWidget puro não pinta o próprio "background" do QSS sozinho -
        # sem isso o tom mais escuro de #sidebar (ver styles.py) nunca
        # aparecia, ficava indistinguível do resto do vidro fosco (mesmo
        # motivo do fix de clique-através em chrome.py::BarraTitulo).
        sidebar.setAttribute(Qt.WA_StyledBackground, True)
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(2)

        logo = QLabel("Siren")
        logo.setObjectName("logoSiren")
        layout.addWidget(logo)

        self._echo_pill = QLabel("verificando ECHO...")
        self._echo_pill.setObjectName("echoPill")
        layout.addWidget(self._echo_pill)
        layout.addSpacing(10)

        grupo_nav = QButtonGroup(sidebar)
        grupo_nav.setExclusive(True)
        botoes = {}
        for chave, rotulo in NAVEGACAO:
            botao = QPushButton(rotulo)
            botao.setObjectName("navBotao")
            botao.setCheckable(True)
            botao.clicked.connect(lambda _checked=False, c=chave: self._mudar_view(c))
            grupo_nav.addButton(botao)
            layout.addWidget(botao)
            botoes[chave] = botao
        layout.addStretch()

        botao_modo_leve = QPushButton("← Modo Leve")
        botao_modo_leve.setObjectName("botaoSecundario")
        botao_modo_leve.clicked.connect(self._trocar_pro_leve)
        layout.addWidget(botao_modo_leve)

        return sidebar, botoes

    def _trocar_pro_leve(self):
        mode_switch.trocar_modo(QApplication.instance(), self, "lite")

    def _construir_views(self):
        return {
            "now": ViewTocandoAgora(ao_iniciar_caos=self._pedir_caos, player=self._player),
            "discover": ViewDescoberta(ao_tocar=self._tocar_faixa),
            "library": ViewEmConstrucao("Biblioteca"),
            "playlists": ViewPlaylists(ao_tocar=self._tocar_faixa, fila=self._fila),
            "favorites": ViewFavoritos(ao_tocar=self._tocar_faixa, fila=self._fila),
            "queue": ViewFila(self._fila, ao_tocar=self._tocar_faixa),
            "history": ViewHistorico(ao_tocar=self._tocar_faixa, fila=self._fila),
            "search": ViewEmConstrucao("Busca"),
        }

    def _mudar_view(self, chave):
        self._stack.setCurrentWidget(self._views[chave])
        self._views[chave].atualizar()
        self._botoes_nav[chave].setChecked(True)
        self._atualizar_pill_echo()

    def _atualizar_pill_echo(self):
        if echo_client.esta_disponivel():
            self._echo_pill.setText("● ECHO conectado")
        else:
            self._echo_pill.setText("○ ECHO offline, tocando sem ele")

    # ---------------- barra de player ----------------

    def _construir_barra_player(self):
        barra = QWidget()
        barra.setObjectName("playerBar")
        barra.setAttribute(Qt.WA_StyledBackground, True)  # ver comentário em _construir_sidebar
        barra.setFixedHeight(78)
        layout = QHBoxLayout(barra)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(16)

        self._label_faixa_atual = QLabel("Nenhuma faixa")
        self._label_faixa_atual.setStyleSheet("font-weight: 700;")
        self._label_artista_atual = QLabel("")
        self._label_artista_atual.setObjectName("legendaView")
        bloco_texto = QVBoxLayout()
        bloco_texto.setSpacing(0)
        bloco_texto.addWidget(self._label_faixa_atual)
        bloco_texto.addWidget(self._label_artista_atual)

        self._botao_favorito = QPushButton("⭐")
        self._botao_favorito.setObjectName("botaoIcone")
        self._botao_favorito.setCheckable(True)
        self._botao_favorito.setFixedSize(30, 30)
        self._botao_favorito.clicked.connect(self._alternar_favorito)

        botao_anterior = QPushButton("⏮")
        botao_anterior.setObjectName("botaoIcone")
        botao_anterior.setFixedSize(30, 30)
        botao_anterior.clicked.connect(self._tocar_anterior)

        self._botao_play_pause = QPushButton("▶")
        self._botao_play_pause.setObjectName("botaoAccent")
        self._botao_play_pause.setFixedSize(34, 34)
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

        botao_caos = QPushButton("🎲 Caos")
        botao_caos.setObjectName("botaoSecundario")
        botao_caos.clicked.connect(self._pedir_caos)

        self._slider_volume = QSlider(Qt.Horizontal)
        self._slider_volume.setRange(0, 100)
        self._slider_volume.setValue(config_mod.obter("volume_inicial"))
        self._slider_volume.setFixedWidth(90)
        self._slider_volume.valueChanged.connect(self._player.definir_volume)

        layout.addLayout(bloco_texto)
        layout.addWidget(self._botao_favorito)
        layout.addStretch()
        layout.addWidget(botao_anterior)
        layout.addWidget(self._botao_play_pause)
        layout.addWidget(botao_proximo)
        layout.addStretch()
        layout.addWidget(botao_caos)
        layout.addWidget(self._botao_dislike)
        layout.addWidget(self._botao_like)
        layout.addWidget(QLabel("🔊"))
        layout.addWidget(self._slider_volume)

        self._definir_controles_habilitados(False)
        return barra

    def _definir_controles_habilitados(self, habilitado):
        for botao in (self._botao_favorito, self._botao_dislike, self._botao_like, self._botao_play_pause):
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
        """A fila local tem prioridade (mesmo autoridade que o PLANO_SIREN.md
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
        self._botao_play_pause.setText("⏸")
        self._definir_controles_habilitados(True)
        self._botao_favorito.setChecked(favoritos_mod.esta_favoritada(titulo, artista))

        voto = echo_client.obter_voto(artista, titulo)
        self._botao_like.setChecked(voto == "positivo")
        self._botao_dislike.setChecked(voto == "negativo")

    def _alternar_play_pause(self):
        self._player.alternar_pausa()
        self._botao_play_pause.setText("▶" if self._player.pausado else "⏸")

    def _alternar_favorito(self):
        if not self._faixa_atual:
            return
        novo_estado = favoritos_mod.alternar(self._faixa_atual["titulo"], self._faixa_atual["artista"])
        self._botao_favorito.setChecked(novo_estado)

    def _like(self):
        if not self._faixa_atual:
            return
        echo_client.enviar_feedback(self._faixa_atual["artista"], self._faixa_atual["titulo"], "positivo")
        self._botao_like.setChecked(True)
        self._botao_dislike.setChecked(False)
        if self._faixa_atual["origem"] in ORIGENS_DESCOBERTA:
            playlists_mod.adicionar_a_descobertas(self._faixa_atual["titulo"], self._faixa_atual["artista"])

    def _dislike(self):
        if not self._faixa_atual:
            return
        echo_client.enviar_feedback(self._faixa_atual["artista"], self._faixa_atual["titulo"], "negativo")
        self._botao_dislike.setChecked(True)
        self._botao_like.setChecked(False)
        self._tocar_proxima()

    def closeEvent(self, event):
        self._player.encerrar()
        super().closeEvent(event)


def criar_aplicacao():
    app = QApplication.instance() or QApplication([])
    janela = FullWindow()
    return app, janela
