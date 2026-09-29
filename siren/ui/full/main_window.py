# -*- coding: utf-8 -*-
"""Janela do Modo Completo do SIREN - vidro fosco (Acrylic) tipo Argus,
biblioteca/playlists/fila/favoritos por cima do MESMO motor de reprodução
do Modo Leve (MPV + Playback Resolver + orquestrador compartilhado, ver
`playback/orquestrador.py`).

Visual "noturno azul" (2026-09-25): fundo azul marinho com brilho difuso
pintado aqui mesmo (`paintEvent`), sidebar/conteúdo/player como painéis
flutuantes arredondados, ícones vetoriais (`icones.py`) no lugar de emojis e
capa real da faixa tocando (thumbnail do YouTube, baixada em background).

Biblioteca ainda mostra um aviso "em construção" (ver docs/TODO.md)."""
import time

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor, QConicalGradient, QCursor, QFont, QLinearGradient, QPainter, QPen,
    QPolygonF, QRadialGradient, QRegion,
)
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QSlider, QStackedWidget,
    QSizePolicy, QStyle, QStyledItemDelegate, QVBoxLayout, QWidget,
)

from siren.core import config as config_mod
from siren.core import favoritos as favoritos_mod
from siren.core import playlists as playlists_mod
from siren.core import sessao as sessao_mod
from siren.playback.controlador import ControladorReproducao, formatar_tempo
from siren.ui import chrome
from siren.ui import mode_switch
from siren.ui.full import arte, icones, neon, styles
from siren.ui.full import faixas as faixas_ui
from siren.ui.full.import_worker import EchoStatusWorker, ImportEchoVotesWorker
from siren.ui.full.ondas import CamadaOndas
from siren.ui.full.views.artista import ViewArtista
from siren.ui.full.views.artistas import ViewArtistas
from siren.ui.full.views.busca import ViewBusca
from siren.ui.full.views.descoberta import ViewDescoberta
from siren.ui.full.views.fila import ViewFila
from siren.ui.full.views.historico import ViewHistorico
from siren.ui.full.views.inicio import ViewInicio
from siren.ui.full.views.playlists import ViewPlaylists
from siren.ui.full.views.tocando_agora import ViewTocandoAgora

LADO_CAPA_PLAYER = 64
LADO_CAPA_BIBLIOTECA = 48
MARGEM_PAINEIS = 10

# Efeitos de água/luar (ver FullWindow._animar_efeitos). Achado medindo
# (2026-09-25): a janela é translúcida (vidro fosco), e no Windows CADA
# atualização de tela reenvia a janela inteira ao compositor - ~8 ms fixos,
# por menor que seja o efeito. Por isso: um relógio só pra tudo (uma
# atualização por quadro, nunca várias) e taxa adaptativa - rápido só
# durante ondas curtas, lento pro que é contínuo, e o contínuo pausa sem
# foco ou sem música.
INTERVALO_RAPIDO_MS = 33  # ondas (gota, sonar) e transição do luar
INTERVALO_LENTO_MS = 90  # ambiente: reflexo da lua, cáusticas
CAUSTICAS_A_CADA = 3  # quadros lentos (~4 fps): é o efeito mais caro (~7 ms extras)
# Janela redimensionável (2026-09-26): sem a borda nativa do Windows (a
# janela é frameless), o redimensionamento pelas bordas precisa ser feito à
# mão - `startSystemResize` num clique perto da borda. Tamanho mínimo e
# modos compactos seguem o Spotify: janela estreita vira sidebar só com
# ícones e botões do player sem texto.
MARGEM_REDIMENSIONAR = 6
TAMANHO_MINIMO = (900, 620)
LARGURA_SIDEBAR = 284
LARGURA_SIDEBAR_COMPACTA = 76
LIMITE_SIDEBAR_COMPACTA = 1120  # largura da janela abaixo da qual a sidebar vira só ícones
LIMITE_PLAYER_COMPACTO = 1060
LARGURA_MAX_CENTRO = 720  # controles + linha do tempo, igual ao limite do Spotify
LARGURA_MIN_CENTRO = 320
LARGURA_MIN_CENTRO_COMPACTO = 250
DICA_REPETIR = {
    "desligado": "Repetir: desligado",
    "fila": "Repetir: fila (cada música que termina volta para o fim da fila)",
    "faixa": "Repetir: esta música",
}
INTERVALO_SONAR = 0.8  # s entre pulsos enquanto o ECHO está sendo consultado
# Raios reduzidos em 2026-09-26 (eram 70 e 48 - "estão muito grandes"): o
# sonar agora fica em volta do pontinho do indicador do ECHO.
RAIO_GOTA = 26
RAIO_SONAR = 16
RAIO_LUAR = 0.27  # fração da largura da janela

# Coleções mantidas pelo próprio SIREN a partir dos votos - ficam num grupo
# próprio da sidebar, fora de "Sua biblioteca" (só playlists do usuário).
COLECOES_AUTOMATICAS = [
    (playlists_mod.NOME_PLAYLIST_CURTIDAS, "coracao"),
    (playlists_mod.NOME_PLAYLIST_NAO_CURTIDAS, "coracao_partido"),
]


class _DelegateBiblioteca(QStyledItemDelegate):
    """Linha da biblioteca lateral: capa procedural + nome + "Playlist · N
    músicas" em cor mais fraca (um `QListWidgetItem` comum só tem uma cor de
    texto por item)."""

    ALTURA = 66

    def sizeHint(self, opcao, indice):
        return QSize(opcao.rect.width(), self.ALTURA)

    def paint(self, pintor, opcao, indice):
        dado = indice.data(Qt.UserRole + 1) or {}
        pintor.save()
        pintor.setRenderHint(QPainter.Antialiasing)
        retangulo = QRectF(opcao.rect).adjusted(0, 2, 0, -2)
        if opcao.state & QStyle.State_MouseOver:
            pintor.setPen(Qt.NoPen)
            pintor.setBrush(QColor(255, 255, 255, 14))
            pintor.drawRoundedRect(retangulo, 10, 10)

        capa = arte.capa_arredondada(dado.get("tema", "generico"), LADO_CAPA_BIBLIOTECA, 8, dado.get("nome", ""))
        topo_capa = retangulo.top() + (retangulo.height() - LADO_CAPA_BIBLIOTECA) / 2
        pintor.drawPixmap(QPointF(retangulo.left() + 4, topo_capa), capa)

        x_texto = retangulo.left() + 4 + LADO_CAPA_BIBLIOTECA + 14
        largura_texto = retangulo.right() - x_texto - 4
        centro = retangulo.center().y()
        fonte = QApplication.font()
        fonte.setFamily("Segoe UI")
        fonte.setPixelSize(14)
        pintor.setFont(fonte)
        pintor.setPen(QColor(styles.COR_TEXTO))
        nome = pintor.fontMetrics().elidedText(dado.get("nome", ""), Qt.ElideRight, int(largura_texto))
        pintor.drawText(QRectF(x_texto, centro - 20, largura_texto, 20), Qt.AlignLeft | Qt.AlignVCenter, nome)
        fonte.setPixelSize(12)
        pintor.setFont(fonte)
        pintor.setPen(QColor(styles.COR_TEXTO_FRACO))
        pintor.drawText(
            QRectF(x_texto, centro + 1, largura_texto, 18), Qt.AlignLeft | Qt.AlignVCenter,
            f"Playlist · {dado.get('quantidade', 0)} músicas",
        )
        pintor.restore()


class _PainelVidro(QFrame):
    """Painel translúcido (sidebar/conteúdo/player) cuja borda ondula como
    luz filtrada pela superfície da água (cáusticas): manchas de luz que
    percorrem a aresta devagar. A janela chama `avancar` a ~10 fps e só a
    faixa da borda é repintada."""

    RAIO_CANTO = 16
    ESPESSURA_FAIXA = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angulo = 0.0

    def avancar(self, angulo):
        self._angulo = angulo
        faixa = QRegion(self.rect()).subtracted(QRegion(self.rect().adjusted(
            self.ESPESSURA_FAIXA, self.ESPESSURA_FAIXA, -self.ESPESSURA_FAIXA, -self.ESPESSURA_FAIXA,
        )))
        self.update(faixa)

    def paintEvent(self, evento):
        super().paintEvent(evento)
        gradiente = QConicalGradient(QPointF(self.rect().center()), self._angulo)
        for posicao, alpha in ((0, 150), (0.1, 18), (0.27, 95), (0.4, 14), (0.58, 125), (0.74, 20), (0.88, 80), (1, 150)):
            gradiente.setColorAt(posicao, QColor(150, 225, 255, alpha))
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setPen(QPen(gradiente, 1.3))
        pintor.setBrush(Qt.NoBrush)
        pintor.drawRoundedRect(QRectF(self.rect()).adjusted(0.7, 0.7, -0.7, -0.7), self.RAIO_CANTO, self.RAIO_CANTO)


class _BotaoModo(QPushButton):
    """Botão de modo do player (Aleatório/Repetir): azul quando ligado, com
    um pontinho embaixo, como no Spotify."""

    def __init__(self):
        super().__init__()
        self.setObjectName("botaoModo")
        self.setFixedSize(32, 32)
        self.setIconSize(QSize(17, 17))
        self.setCursor(Qt.PointingHandCursor)
        self._ativo = False

    def definir(self, nome_icone, ativo, dica):
        self._ativo = ativo
        self.setIcon(icones.icone(nome_icone, styles.COR_ACCENT_CLARO if ativo else styles.COR_TEXTO_FRACO, 17))
        self.setToolTip(dica)
        self.update()

    def paintEvent(self, evento):
        super().paintEvent(evento)
        if not self._ativo:
            return
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QColor(styles.COR_ACCENT_CLARO))
        pintor.drawEllipse(QPointF(self.width() / 2, self.height() - 3), 2, 2)


class _BotaoNav(QPushButton):
    """Item da sidebar; quando ativo, ganha um pequeno cristal dourado à
    direita - os cristais azuis e dourados da logo do SIREN. `contador`
    (coleções Curtidas/Não Curtidas, 2026-09-26) mostra o número de músicas
    alinhado à direita."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._contador = None
        self._texto_completo = self.text()
        self._compacto = False

    def definir_compacto(self, compacto):
        """Só o ícone (sidebar estreita); o nome vira tooltip."""
        self._compacto = compacto
        self.setText("" if compacto else self._texto_completo)
        self.setToolTip(self._texto_completo.strip() if compacto else self.toolTip())
        self.update()

    def definir_contador(self, valor):
        self._contador = valor
        self.update()

    def paintEvent(self, evento):
        super().paintEvent(evento)
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        direita = self.width() - 14.0
        if self._compacto:
            if self.isChecked():
                # No modo compacto o cristal vai pro canto, sem disputar espaço com o ícone.
                direita = self.width() - 4.0
            else:
                return
        elif self._contador is not None:
            fonte = self.font()
            fonte.setPixelSize(12)
            pintor.setFont(fonte)
            texto = str(self._contador)
            largura = pintor.fontMetrics().horizontalAdvance(texto)
            pintor.setPen(QColor(styles.COR_TEXTO_FRACO))
            pintor.drawText(QRectF(direita - largura, 0, largura, self.height()), Qt.AlignRight | Qt.AlignVCenter, texto)
            direita -= largura + 12
        if not self.isChecked():
            return
        cx, cy, r = direita - 4.0, self.height() / 2, 4.5
        cristal = QPolygonF([QPointF(cx, cy - r * 1.35), QPointF(cx + r, cy), QPointF(cx, cy + r * 1.35), QPointF(cx - r, cy)])
        brilho = QRadialGradient(QPointF(cx, cy), r * 3.2)
        brilho.setColorAt(0, QColor(232, 194, 106, 90))
        brilho.setColorAt(1, QColor(232, 194, 106, 0))
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(brilho)
        pintor.drawEllipse(QPointF(cx, cy), r * 3.2, r * 3.2)
        pintor.setBrush(QColor(styles.COR_OURO))
        pintor.drawPolygon(cristal)


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


def _botao_icone(nome_icone, nome_objeto, tamanho, tamanho_icone, cor=styles.COR_TEXTO, cor_ativa=None, dica=""):
    botao = QPushButton()
    botao.setObjectName(nome_objeto)
    botao.setIcon(icones.icone(nome_icone, cor, tamanho_icone, cor_ativa=cor_ativa))
    botao.setIconSize(QSize(tamanho_icone, tamanho_icone))
    botao.setFixedSize(tamanho, tamanho)
    botao.setCursor(Qt.PointingHandCursor)
    if dica:
        botao.setToolTip(dica)
    return botao


def _botao_texto_icone(texto, nome_icone, nome_objeto, cor_icone=styles.COR_TEXTO, tamanho_icone=18):
    botao = QPushButton(f"  {texto}")
    botao.setObjectName(nome_objeto)
    botao.setIcon(icones.icone(nome_icone, cor_icone, tamanho_icone))
    botao.setIconSize(QSize(tamanho_icone, tamanho_icone))
    botao.setCursor(Qt.PointingHandCursor)
    return botao


class FullWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SIREN")
        self.resize(1280, 820)
        self.setMinimumSize(*TAMANHO_MINIMO)
        self._maximizar_ao_mostrar = False
        self._cursor_borda = None
        self._sidebar_compacta = False
        self._player_compacto = False
        self._encerrado = False
        geometria = sessao_mod.carregar_janela()
        telas = [t.availableGeometry().getRect() for t in QApplication.screens()]
        if sessao_mod.geometria_visivel(geometria, telas):
            self.setGeometry(geometria["x"], geometria["y"], max(geometria["largura"], TAMANHO_MINIMO[0]),
                             max(geometria["altura"], TAMANHO_MINIMO[1]))
            self._maximizar_ao_mostrar = geometria.get("maximizada", False)

        # Toda a lógica de reprodução (fila, Caos, aleatório/repetir, votos,
        # sessão) mora no controlador, compartilhado com o miniplayer do Modo
        # Leve (2026-09-26); esta janela só mostra e reage aos sinais dele.
        self._ctrl = ControladorReproducao(self)
        self._player = self._ctrl.player
        self._fila = self._ctrl.fila
        self._tocando = False
        self._migrar_favoritos_legados()
        playlists_mod.remover_descobertas_legada()

        cor_fundo = styles.COR_FUNDO
        estado = chrome.configurar_janela_vidro_fosco(
            self, cor_fundo, alpha=130, acrylic_ativado=config_mod.obter("acrylic_ativado"),
            translucida=bool(config_mod.obter("janela_translucida")),
        )
        self._translucida = bool(config_mod.obter("janela_translucida"))
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

        corpo = _PainelVidro()
        corpo.setObjectName("painelConteudo")
        self._painel_conteudo = corpo
        layout_corpo = QVBoxLayout(corpo)
        layout_corpo.setContentsMargins(1, 1, 1, 1)
        layout_corpo.setSpacing(0)
        layout_corpo.addWidget(self._construir_topbar())
        layout_corpo.addWidget(self._stack, stretch=1)

        conteudo = QWidget()
        layout_conteudo = QHBoxLayout(conteudo)
        layout_conteudo.setContentsMargins(MARGEM_PAINEIS, 0, MARGEM_PAINEIS, 0)
        layout_conteudo.setSpacing(MARGEM_PAINEIS)
        layout_conteudo.addWidget(self._sidebar)
        layout_conteudo.addWidget(corpo, stretch=1)
        # Rastreamento de mouse nas áreas que encostam na borda da janela
        # (fundo, barra de título, moldura do conteúdo): sem ele o Qt não
        # manda MouseMove sem botão apertado, e o cursor de redimensionar
        # nunca aparecia (achado do usuário, 2026-09-26).
        for widget in (self, self._barra_titulo, conteudo):
            widget.setMouseTracking(True)

        self._barra_player = self._construir_barra_player()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, MARGEM_PAINEIS)
        layout.setSpacing(MARGEM_PAINEIS)
        layout.addWidget(self._barra_titulo)
        layout.addWidget(conteudo, stretch=1)
        player_com_margem = QHBoxLayout()
        player_com_margem.setContentsMargins(MARGEM_PAINEIS, 0, MARGEM_PAINEIS, 0)
        player_com_margem.addWidget(self._barra_player)
        layout.addLayout(player_com_margem)

        self._atualizar_sidebar_playlists()
        self._mudar_view("home")
        self._sincronizar_votos_echo()
        self._conectar_controlador()
        self._ctrl.retomar_sessao()

        self._intensidade_luar = 0.0
        self._efeitos_mouse = bool(config_mod.obter("efeitos_mouse_ativados"))
        self._ultimo_sonar = 0.0
        self._ultimo_clique = None
        self._tick_efeitos = 0
        self._camada_ondas = CamadaOndas(self)
        self._camada_ondas.setGeometry(self.rect())
        self._camada_ondas.raise_()
        self._efeitos_ambiente = bool(config_mod.obter("efeitos_ambiente_ativados"))
        self._ultimo_ambiente = 0.0
        self._quadros_ambiente = 0
        self._timer_efeitos = QTimer(self)
        self._timer_efeitos.setInterval(INTERVALO_LENTO_MS)
        self._timer_efeitos.timeout.connect(self._animar_efeitos)
        self._timer_efeitos.start()
        # Cliques vão pros widgets-filhos, nunca pra janela - só um filtro no
        # nível da aplicação enxerga todos (gota d'água e redimensionar pela borda).
        QApplication.instance().installEventFilter(self)
        self._aplicar_layout_responsivo()

    def paintEvent(self, evento):
        """Fundo da janela inteira: azul marinho e uma lua cheia difusa no canto superior
        direito, atrás do vidro - a lua da logo do SIREN. O luar fica mais
        forte enquanto a música toca e esmaece no pause."""
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        altura = self.height()
        # Janela opaca (padrão): fundo 100% opaco. Translúcida: deixa o
        # Acrylic "respirar" um pouco por trás.
        opaco = not self._translucida
        base = QLinearGradient(0, 0, 0, altura)
        base.setColorAt(0, QColor(10, 20, 48, 255 if opaco else 246))
        base.setColorAt(0.5, QColor(6, 12, 30, 255 if opaco else 248))
        base.setColorAt(1, QColor(4, 8, 20, 255 if opaco else 250))
        pintor.fillRect(self.rect(), base)

        intensidade = 0.55 + 0.45 * self._intensidade_luar
        centro = self.posicao_lua()
        raio = self.width() * RAIO_LUAR
        luar = QRadialGradient(centro, raio)
        luar.setColorAt(0, QColor(190, 212, 255, int(95 * intensidade)))
        luar.setColorAt(0.25, QColor(96, 140, 230, int(50 * intensidade)))
        luar.setColorAt(1, QColor(59, 100, 200, 0))
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(luar)
        pintor.drawEllipse(centro, raio, raio)
        disco = QRadialGradient(centro, 36)
        disco.setColorAt(0, QColor(240, 244, 255, int(150 * intensidade)))
        disco.setColorAt(0.8, QColor(225, 234, 255, int(120 * intensidade)))
        disco.setColorAt(1, QColor(225, 234, 255, 0))
        pintor.setBrush(disco)
        pintor.drawEllipse(centro, 36, 36)

    def posicao_lua(self):
        """Onde a lua fica, em coordenadas da janela - a Home usa pra alinhar
        o reflexo no mar da paisagem."""
        return QPointF(self.width() * 0.86, 70)

    def _retangulo_luar(self):
        raio = self.width() * RAIO_LUAR
        centro = self.posicao_lua()
        return QRectF(centro.x() - raio, centro.y() - raio, raio * 2, raio * 2).toAlignedRect()

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if hasattr(self, "_botoes_player_texto"):
            self._aplicar_layout_responsivo()
            self._ajustar_centro_player()
        if hasattr(self, "_camada_ondas"):
            self._camada_ondas.setGeometry(self.rect())
            self._camada_ondas.raise_()

    # ---------------- efeitos de água ----------------

    def _centro_em_janela(self, widget, ponto=None):
        ponto = ponto if ponto is not None else widget.rect().center()
        return QPointF(widget.mapTo(self, ponto))

    def _ponto_sonar(self):
        return self._centro_em_janela(self._echo_pill, QPoint(18, self._echo_pill.height() // 2))

    def _sonar_necessario(self, agora):
        if not self._echo_pill.isVisible():
            return False  # sidebar compacta esconde o indicador do ECHO, de onde o sonar sai
        worker_status = getattr(self, "_worker_status_echo", None)
        return (
            self._ctrl.aguardando_caos
            or (worker_status is not None and worker_status.isRunning())
            or self._views["home"].carregando()
        )

    def _animar_efeitos(self):
        """Relógio único de todos os efeitos: sonar do ECHO, avanço das
        ondas, transição do luar e o ambiente (reflexo da lua, cáusticas nas
        bordas)."""
        if not self.isVisible() or self.isMinimized():
            return
        agora = time.monotonic()
        self._tick_efeitos += 1

        # Cursor de redimensionar por polling: eventos de movimento sem botão
        # apertado não chegam de forma confiável nas áreas da borda (testado
        # em 2026-09-26 - só com mouseTracking o cursor não mudava).
        self._atualizar_cursor_borda(QCursor.pos())

        if self._sonar_necessario(agora) and agora - self._ultimo_sonar > INTERVALO_SONAR:
            self._camada_ondas.adicionar(self._ponto_sonar(), RAIO_SONAR, 1.2, "sonar")
            self._ultimo_sonar = agora

        self._camada_ondas.avancar()

        alvo_luar = 1.0 if self._tocando else 0.0
        luar_em_transicao = abs(alvo_luar - self._intensidade_luar) > 0.005
        if luar_em_transicao:
            # Transição curta (~1 s) e repintada a ~8 fps: a área do luar é
            # grande, e ninguém percebe degrau num brilho tão difuso.
            self._intensidade_luar += (alvo_luar - self._intensidade_luar) * 0.12
            if abs(alvo_luar - self._intensidade_luar) <= 0.02:
                self._intensidade_luar = alvo_luar
            if self._tick_efeitos % 4 == 0 or self._intensidade_luar == alvo_luar:
                self.update(self._retangulo_luar())

        ambiente_ativo = self._efeitos_ambiente and self.isActiveWindow() and self._tocando
        if ambiente_ativo and agora - self._ultimo_ambiente >= (INTERVALO_LENTO_MS - 5) / 1000:
            self._ultimo_ambiente = agora
            self._quadros_ambiente += 1
            self._views["home"].avancar_efeitos()
            if self._quadros_ambiente % CAUSTICAS_A_CADA == 0:
                angulo = (agora * 14) % 360
                for painel in (self._sidebar, self._painel_conteudo, self._barra_player):
                    painel.avancar(angulo)

        rapido = self._camada_ondas.ativa or luar_em_transicao or self._sonar_necessario(agora)
        intervalo = INTERVALO_RAPIDO_MS if rapido else INTERVALO_LENTO_MS
        if self._timer_efeitos.interval() != intervalo:
            self._timer_efeitos.setInterval(intervalo)

    def eventFilter(self, objeto, evento):
        """Gota d'água em qualquer clique dentro da janela. O mesmo clique
        pode chegar várias vezes (propaga do filho pro pai) - o carimbo de
        tempo do evento evita gotas duplicadas."""
        tipo = evento.type()
        if tipo in (QEvent.MouseMove, QEvent.HoverMove) and isinstance(objeto, QWidget) and objeto.window() is self:
            self._atualizar_cursor_borda(QCursor.pos())
        elif tipo == QEvent.Leave and objeto is self:
            self._atualizar_cursor_borda(QPoint(-100000, -100000))  # saiu da janela: cursor normal
        if tipo == QEvent.MouseButtonPress and isinstance(objeto, QWidget) and objeto.window() is self:
            if evento.button() == Qt.LeftButton:
                bordas = self._bordas_em(evento.globalPosition().toPoint())
                if bordas:
                    self.windowHandle().startSystemResize(bordas)
                    return True
        if tipo == QEvent.MouseButtonPress and self._efeitos_mouse and isinstance(objeto, QWidget) and objeto.window() is self:
            chave = (evento.timestamp(), evento.globalPosition().toPoint())
            if chave != self._ultimo_clique:
                self._ultimo_clique = chave
                centro = QPointF(self.mapFromGlobal(evento.globalPosition().toPoint()))
                self._camada_ondas.adicionar(centro, RAIO_GOTA, 0.6, "gota")
                self._camada_ondas.adicionar(centro, RAIO_GOTA * 0.55, 0.6, "gota", atraso=0.1)
                self._timer_efeitos.setInterval(INTERVALO_RAPIDO_MS)
        return False

    # ---------------- janela redimensionável ----------------

    def _bordas_em(self, ponto_global):
        """Quais bordas estão sob o ponto (vazio = nenhuma). Desligado com a
        janela maximizada, como no Windows."""
        if self.isMaximized() or self.isFullScreen():
            return Qt.Edges()
        ponto = self.mapFromGlobal(ponto_global)
        if not self.rect().contains(ponto):
            return Qt.Edges()
        bordas = Qt.Edges()
        if ponto.x() <= MARGEM_REDIMENSIONAR:
            bordas |= Qt.LeftEdge
        elif ponto.x() >= self.width() - MARGEM_REDIMENSIONAR - 1:
            bordas |= Qt.RightEdge
        if ponto.y() <= MARGEM_REDIMENSIONAR:
            bordas |= Qt.TopEdge
        elif ponto.y() >= self.height() - MARGEM_REDIMENSIONAR - 1:
            bordas |= Qt.BottomEdge
        return bordas

    def _atualizar_cursor_borda(self, ponto_global):
        bordas = self._bordas_em(ponto_global)
        formato = None
        if bordas in (Qt.LeftEdge | Qt.TopEdge, Qt.RightEdge | Qt.BottomEdge):
            formato = Qt.SizeFDiagCursor
        elif bordas in (Qt.RightEdge | Qt.TopEdge, Qt.LeftEdge | Qt.BottomEdge):
            formato = Qt.SizeBDiagCursor
        elif bordas & (Qt.LeftEdge | Qt.RightEdge):
            formato = Qt.SizeHorCursor
        elif bordas & (Qt.TopEdge | Qt.BottomEdge):
            formato = Qt.SizeVerCursor
        if formato == self._cursor_borda:
            return
        if self._cursor_borda is not None:
            QApplication.restoreOverrideCursor()
        if formato is not None:
            QApplication.setOverrideCursor(formato)
        self._cursor_borda = formato

    def _aplicar_layout_responsivo(self):
        """Sidebar só com ícones e botões do player sem texto quando a
        janela fica estreita."""
        compacta = self.width() < LIMITE_SIDEBAR_COMPACTA
        if compacta != self._sidebar_compacta:
            self._sidebar_compacta = compacta
            self._sidebar.setFixedWidth(LARGURA_SIDEBAR_COMPACTA if compacta else LARGURA_SIDEBAR)
            margem = 10 if compacta else 16
            self._layout_sidebar.setContentsMargins(margem, 18, margem, 16)
            for widget in self._so_expandido + [self._echo_pill]:
                widget.setVisible(not compacta)
            for botao in list(self._botoes_nav.values()) + list(self._botoes_colecao.values()):
                botao.definir_compacto(compacta)
            self._atualizar_sidebar_playlists()
        player_compacto = self.width() < LIMITE_PLAYER_COMPACTO
        if player_compacto != self._player_compacto:
            self._player_compacto = player_compacto
            for botao, texto in self._botoes_player_texto.items():
                botao.setText("" if player_compacto else texto)
                botao.setToolTip(texto.strip() if player_compacto else "")
            self._area_texto_player.setFixedWidth(120 if player_compacto else 210)
            self._slider_volume.setFixedWidth(70 if player_compacto else 110)
            espacamento = 10 if player_compacto else 14
            self._linha_esquerda_player.setSpacing(espacamento)
            self._linha_direita_player.setSpacing(espacamento)
            self._linha_controles.setSpacing(10 if player_compacto else 18)
            self._ajustar_centro_player()

    def _ajustar_centro_player(self):
        """Centro = o que sobra depois de reservar a MESMA largura pros dois
        lados (a do maior deles), limitado a `LARGURA_MAX_CENTRO` - assim ele
        fica exatamente no meio da janela."""
        esquerdo, centro, direito = self._blocos_player
        espacamento = self._barra_player.layout().spacing() * 2
        margens = self._barra_player.layout().contentsMargins()
        disponivel = self._barra_player.width() - margens.left() - margens.right() - espacamento
        largura_esquerda = esquerdo.minimumSizeHint().width()
        largura_direita = direito.minimumSizeHint().width()
        minimo = LARGURA_MIN_CENTRO_COMPACTO if self._player_compacto else LARGURA_MIN_CENTRO
        simetrico = disponivel - 2 * max(largura_esquerda, largura_direita)
        if simetrico >= minimo:
            largura = min(LARGURA_MAX_CENTRO, simetrico)
        else:
            # Janela estreita: não dá pra centralizar exato sem sobrepor os
            # blocos - usa o espaço real que sobra entre eles.
            largura = max(minimo, disponivel - largura_esquerda - largura_direita)
        centro.setFixedWidth(largura)

    def showEvent(self, evento):
        super().showEvent(evento)
        self._ajustar_centro_player()
        if self._maximizar_ao_mostrar:
            self._maximizar_ao_mostrar = False
            QTimer.singleShot(0, self.showMaximized)

    def _salvar_janela(self):
        geometria = self.normalGeometry() if self.isMaximized() else self.geometry()
        sessao_mod.salvar_janela(geometria.x(), geometria.y(), geometria.width(), geometria.height(), self.isMaximized())

    def _definir_tocando(self, tocando):
        self._tocando = tocando

    # ---------------- sidebar ----------------

    def _construir_sidebar(self):
        """Três grupos, de cima pra baixo (2026-09-25): navegação, coleções
        automáticas (Curtidas/Não Curtidas - o SIREN mantém
        sozinho, a partir dos votos) e "Sua biblioteca", só com playlists
        criadas ou importadas pelo usuário. Antes as automáticas ficavam
        misturadas na biblioteca, como se fossem playlists comuns."""
        sidebar = _PainelVidro()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(LARGURA_SIDEBAR)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 18, 16, 16)
        self._layout_sidebar = layout
        layout.setSpacing(3)

        linha_logo = QHBoxLayout()
        linha_logo.setContentsMargins(4, 0, 0, 0)
        logo = QLabel("Siren")
        logo.setObjectName("logoSiren")
        equalizador = QLabel()
        equalizador.setPixmap(icones.pixmap("equalizador", styles.COR_ACCENT_CLARO, 24, espessura=2.4))
        botao_modo_leve = _botao_icone("lua", "botaoPequeno", 30, 16, dica="Trocar para o Modo Leve")
        botao_modo_leve.clicked.connect(self._trocar_pro_leve)
        linha_logo.addWidget(logo)
        linha_logo.addSpacing(8)
        linha_logo.addWidget(equalizador)
        linha_logo.addStretch()
        linha_logo.addWidget(botao_modo_leve)
        layout.addLayout(linha_logo)
        self._so_expandido = [logo, botao_modo_leve]
        layout.addSpacing(6)

        self._echo_pill = QLabel("verificando ECHO...")
        self._echo_pill.setObjectName("echoPill")
        self._echo_pill.setTextFormat(Qt.RichText)
        layout.addWidget(self._echo_pill)
        layout.addSpacing(14)

        self._botoes_nav = {
            "home": self._criar_botao_nav("Início", "inicio", lambda: self._mudar_view("home")),
            "descoberta": self._criar_botao_nav("Descoberta", "descoberta", lambda: self._mudar_view("descoberta")),
            "historico": self._criar_botao_nav("Histórico", "historico", lambda: self._mudar_view("historico")),
            "artistas": self._criar_botao_nav("Artistas", "pessoa", lambda: self._mudar_view("artistas")),
        }
        for botao in self._botoes_nav.values():
            layout.addWidget(botao)

        layout.addSpacing(8)
        layout.addWidget(self._criar_divisor())
        layout.addSpacing(8)

        self._botoes_colecao = {}
        for nome, nome_icone in COLECOES_AUTOMATICAS:
            botao = self._criar_botao_nav(nome, nome_icone, lambda _=False, n=nome: self._abrir_playlist(n))
            self._botoes_colecao[nome] = botao
            layout.addWidget(botao)

        layout.addSpacing(8)
        layout.addWidget(self._criar_divisor())
        layout.addSpacing(10)

        linha_biblioteca = QHBoxLayout()
        linha_biblioteca.setContentsMargins(4, 0, 0, 0)
        linha_biblioteca.setSpacing(6)
        titulo_biblioteca = QLabel("SUA BIBLIOTECA")
        titulo_biblioteca.setObjectName("rotuloGrupo")
        fonte = titulo_biblioteca.font()
        fonte.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        titulo_biblioteca.setFont(fonte)
        botao_importar = _botao_icone("baixar", "botaoPequeno", 30, 15, dica="Importar playlist")
        botao_importar.clicked.connect(lambda: self._mudar_view("playlists"))
        botao_criar = _botao_icone("mais", "botaoPequeno", 30, 16, dica="Criar playlist")
        botao_criar.clicked.connect(self._criar_playlist)
        linha_biblioteca.addWidget(titulo_biblioteca)
        linha_biblioteca.addStretch()
        linha_biblioteca.addWidget(botao_importar)
        linha_biblioteca.addWidget(botao_criar)
        layout.addLayout(linha_biblioteca)
        self._so_expandido += [titulo_biblioteca, botao_importar]
        layout.addSpacing(4)

        self._lista_biblioteca = QListWidget()
        self._lista_biblioteca.setObjectName("listaBiblioteca")
        self._lista_biblioteca.setItemDelegate(_DelegateBiblioteca(self._lista_biblioteca))
        self._lista_biblioteca.setMouseTracking(True)
        self._lista_biblioteca.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._lista_biblioteca.setCursor(Qt.PointingHandCursor)
        self._lista_biblioteca.itemClicked.connect(self._abrir_playlist_item)
        layout.addWidget(self._lista_biblioteca, stretch=1)

        self._biblioteca_vazia = QLabel("Crie (+) ou importe uma playlist para ela aparecer aqui.")
        self._biblioteca_vazia.setObjectName("bibliotecaVazia")
        self._biblioteca_vazia.setWordWrap(True)
        self._biblioteca_vazia.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self._biblioteca_vazia, stretch=1)

        return sidebar

    @staticmethod
    def _criar_divisor():
        divisor = QFrame()
        divisor.setObjectName("divisorSidebar")
        divisor.setFixedHeight(1)
        return divisor

    def _criar_botao_nav(self, texto, nome_icone, ao_clicar):
        botao = _BotaoNav(f"  {texto}")
        botao.setObjectName("navBotao")
        botao.setIcon(icones.icone(nome_icone, styles.COR_TEXTO, 20))
        botao.setIconSize(QSize(20, 20))
        botao.setCursor(Qt.PointingHandCursor)
        botao.setCheckable(True)
        botao.clicked.connect(ao_clicar)
        return botao

    def _construir_topbar(self):
        topo = QWidget()
        topo.setObjectName("topBar")
        topo.setAttribute(Qt.WA_StyledBackground, True)
        layout = QHBoxLayout(topo)
        layout.setContentsMargins(22, 14, 22, 8)
        layout.setSpacing(16)

        botao_inicio = _botao_icone("inicio", "botaoCircular", 46, 20, dica="Início")
        botao_inicio.setStyleSheet("border-radius: 14px;")
        botao_inicio.clicked.connect(lambda: self._mudar_view("home"))

        self._campo_busca = QLineEdit()
        self._campo_busca.setObjectName("buscaGlobal")
        self._campo_busca.setPlaceholderText("O que você quer ouvir?")
        self._campo_busca.setClearButtonEnabled(True)
        self._campo_busca.setMaximumWidth(660)
        self._campo_busca.setFixedHeight(44)
        self._campo_busca.addAction(icones.icone("busca", styles.COR_TEXTO, 18), QLineEdit.LeadingPosition)
        self._campo_busca.returnPressed.connect(self._buscar)

        layout.addWidget(botao_inicio)
        layout.addWidget(self._campo_busca, stretch=1)
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
        automaticas = {nome for nome, _icone in COLECOES_AUTOMATICAS}
        for nome, botao in self._botoes_colecao.items():
            quantidade = len(playlists_mod.obter_faixas(nome))
            botao.definir_contador(quantidade)
            botao.setToolTip(f"{nome} · {quantidade} músicas")
        self._lista_biblioteca.clear()
        for playlist in playlists_mod.listar():
            if playlist["nome"] in automaticas:
                continue
            item = QListWidgetItem()
            item.setData(Qt.UserRole, playlist["nome"])
            item.setData(Qt.UserRole + 1, {
                "nome": playlist["nome"], "quantidade": playlist["quantidade"],
                "tema": arte.tema_da_playlist(playlist["nome"]),
            })
            item.setToolTip(playlist["nome"])
            self._lista_biblioteca.addItem(item)
        vazia = self._lista_biblioteca.count() == 0
        self._lista_biblioteca.setVisible(not vazia)
        self._biblioteca_vazia.setVisible(vazia)
        if getattr(self, "_sidebar_compacta", False):
            self._lista_biblioteca.hide()
            self._biblioteca_vazia.hide()

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
        self._marcar_navegacao(colecao=nome)

    def _tocar_playlist(self, nome):
        """Botão ▶ dos cartões da Home."""
        faixas = playlists_mod.obter_faixas(nome)
        if not faixas:
            self._label_faixa_atual.setText(f"\"{nome}\" ainda está vazia")
            return
        self._tocar_lista(faixas, f"playlist:{nome}")

    def _tocar_lista(self, faixas, origem):
        self._ctrl.tocar_lista(faixas, origem)

    def _enfileirar(self, faixa, origem):
        self._ctrl.enfileirar(faixa, origem)

    def _abrir_artista(self, nome):
        """Clique no nome do artista (Fila, player) - tela do artista."""
        if not nome:
            return
        self._views["artista"].abrir(nome)
        self._stack.setCurrentWidget(self._views["artista"])
        self._marcar_navegacao()

    def _trocar_pro_leve(self):
        mode_switch.trocar_modo(QApplication.instance(), self, "lite")

    def preparar_troca_de_modo(self):
        """`mode_switch`: tocando, esta janela segue tocando até o outro
        modo assumir (`troca_concluida` fecha esta janela); parada, devolve
        False e pode fechar na hora."""
        self._salvar_janela()
        return self._ctrl.iniciar_troca_de_modo()

    def _construir_views(self):
        return {
            "home": ViewInicio(
                ao_tocar=self._tocar_faixa,
                ao_abrir_playlist=self._abrir_playlist,
                ao_iniciar_caos=self._iniciar_caos,
                ao_tocar_playlist=self._tocar_playlist,
            ),
            "now": ViewTocandoAgora(ao_iniciar_caos=self._iniciar_caos, player=self._player),
            "playlists": ViewPlaylists(ao_tocar=self._tocar_faixa, fila=self._fila),
            "queue": ViewFila(
                self._fila, ao_tocar=self._tocar_faixa, ao_votar=self._votar_faixa_da_fila,
                ao_abrir_artista=self._abrir_artista,
            ),
            "artista": ViewArtista(
                ao_tocar=self._tocar_faixa, ao_tocar_lista=self._tocar_lista,
                ao_votar=self._votar_faixa_da_fila, ao_enfileirar=self._enfileirar,
            ),
            "search": ViewBusca(ao_tocar=self._tocar_faixa),
            "artistas": ViewArtistas(ao_abrir_artista=self._abrir_artista),
            "descoberta": ViewDescoberta(ao_tocar=self._tocar_faixa),
            "historico": ViewHistorico(ao_tocar=self._tocar_faixa, fila=self._fila),
        }

    def _mudar_view(self, chave, atualizar=True):
        self._stack.setCurrentWidget(self._views[chave])
        if atualizar:
            self._views[chave].atualizar()
        self._marcar_navegacao(view=chave)
        if chave == "home":
            self._atualizar_sidebar_playlists()
        self._atualizar_pill_echo()

    def _marcar_navegacao(self, view=None, colecao=None):
        """Só um item da sidebar aceso por vez - aba de navegação OU coleção
        automática aberta (playlist comum da biblioteca não acende nenhum)."""
        for chave, botao in self._botoes_nav.items():
            botao.setChecked(chave == view)
        for nome, botao in self._botoes_colecao.items():
            botao.setChecked(nome == colecao)

    def _atualizar_pill_echo(self):
        worker_atual = getattr(self, "_worker_status_echo", None)
        if worker_atual is not None and worker_atual.isRunning():
            return
        self._definir_pill_echo(styles.COR_TEXTO_FRACO, "verificando ECHO…")
        worker = EchoStatusWorker(self)
        worker.concluido.connect(self._mostrar_status_echo)
        worker.finished.connect(lambda w=worker: self._finalizar_status_echo(w))
        self._worker_status_echo = worker
        worker.start()

    def _definir_pill_echo(self, cor_ponto, texto):
        self._echo_pill.setText(f'<span style="color:{cor_ponto}; font-size:13px;">●</span>&nbsp; {texto}')

    def _mostrar_status_echo(self, conectado):
        if conectado:
            self._definir_pill_echo(styles.COR_ONLINE, "ECHO conectado")
        else:
            self._definir_pill_echo(styles.COR_OFFLINE, "ECHO offline, tocando sem ele")

    def _finalizar_status_echo(self, worker):
        if worker is self._worker_status_echo:
            self._worker_status_echo = None
        worker.deleteLater()

    # ---------------- barra de player ----------------

    def _construir_barra_player(self):
        barra = _PainelVidro()
        barra.setObjectName("playerBar")
        barra.setFixedHeight(100)
        layout = QHBoxLayout(barra)
        layout.setContentsMargins(18, 10, 22, 10)
        layout.setSpacing(14)

        self._capa_player = QLabel()
        self._capa_player.setObjectName("capaPlayer")
        self._capa_player.setAlignment(Qt.AlignCenter)
        self._capa_player.setFixedSize(LADO_CAPA_PLAYER, LADO_CAPA_PLAYER)
        self._capa_player.setPixmap(icones.pixmap("nota", styles.COR_TEXTO_FRACO, 26))

        self._label_faixa_atual = QLabel("Nenhuma faixa")
        self._label_faixa_atual.setObjectName("tituloFaixaPlayer")
        self._label_artista_atual = faixas_ui.RotuloLink("")
        self._label_artista_atual.setToolTip("Abrir o artista")
        self._label_artista_atual.clicado.connect(
            lambda: self._abrir_artista(self._ctrl.faixa_atual["artista"] if self._ctrl.faixa_atual else "")
        )
        bloco_texto = QVBoxLayout()
        bloco_texto.setSpacing(2)
        bloco_texto.addStretch()
        bloco_texto.addWidget(self._label_faixa_atual)
        bloco_texto.addWidget(self._label_artista_atual)
        bloco_texto.addStretch()
        area_texto = QWidget()
        area_texto.setLayout(bloco_texto)
        area_texto.setFixedWidth(210)
        self._area_texto_player = area_texto

        self._botao_like = _botao_icone(
            "coracao", "botaoLike", 38, 18, cor=styles.COR_TEXTO_FRACO, cor_ativa=styles.COR_LIKE, dica="Curtir",
        )
        self._botao_like.setIcon(self._icone_like())
        self._botao_like.setCheckable(True)
        self._botao_like.clicked.connect(self._ctrl.curtir)

        self._botao_dislike = _botao_icone(
            "dislike", "botaoDislike", 38, 17, cor=styles.COR_TEXTO_FRACO, cor_ativa=styles.COR_DISLIKE,
            dica="Não curtir e pular",
        )
        self._botao_dislike.setCheckable(True)
        self._botao_dislike.setIcon(faixas_ui.icone_nao_curtir(17))
        self._botao_dislike.clicked.connect(self._ctrl.nao_curtir)

        botao_anterior = _botao_icone("anterior", "botaoIcone", 40, 20, dica="Anterior")
        botao_anterior.clicked.connect(self._ctrl.anterior)

        self._botao_play_pause = _botao_icone("play", "botaoPlayPlayer", 40, 16, cor="#ffffff", dica="Tocar/pausar")
        self._botao_play_pause.clicked.connect(self._ctrl.alternar_play_pause)
        neon.aplicar(self._botao_play_pause, raio=26, alpha=220)

        botao_proximo = _botao_icone("proximo", "botaoIcone", 40, 20, dica="Próxima")
        botao_proximo.clicked.connect(lambda: self._ctrl.proxima())

        self._slider_progresso = _SliderSeek(Qt.Horizontal)
        self._slider_progresso.setRange(0, 0)
        self._slider_progresso.setEnabled(False)
        self._slider_progresso.setCursor(Qt.PointingHandCursor)
        self._slider_progresso.seek_solicitado.connect(self._ctrl.buscar_posicao)
        self._label_tempo_decorrido = QLabel("0:00")
        self._label_tempo_decorrido.setObjectName("tempoPlayer")
        self._label_tempo_total = QLabel("0:00")
        self._label_tempo_total.setObjectName("tempoPlayer")

        self._slider_volume = QSlider(Qt.Horizontal)
        self._slider_volume.setRange(0, 100)
        self._slider_volume.setValue(config_mod.obter("volume_inicial"))
        self._slider_volume.setFixedWidth(110)
        self._slider_volume.setCursor(Qt.PointingHandCursor)
        self._slider_volume.valueChanged.connect(self._ctrl.definir_volume)

        # Aleatório e Repetir nas mesmas posições do Spotify (2026-09-26).
        self._botao_aleatorio = _BotaoModo()
        self._botao_aleatorio.clicked.connect(self._ctrl.alternar_aleatorio)
        self._botao_repetir = _BotaoModo()
        self._botao_repetir.clicked.connect(self._ctrl.alternar_repetir)
        self._atualizar_botoes_modo()

        controles = QHBoxLayout()
        controles.setSpacing(18)
        self._linha_controles = controles
        controles.addStretch()
        controles.addWidget(self._botao_aleatorio)
        controles.addWidget(botao_anterior)
        controles.addWidget(self._botao_play_pause)
        controles.addWidget(botao_proximo)
        controles.addWidget(self._botao_repetir)
        controles.addStretch()

        progresso = QHBoxLayout()
        progresso.setSpacing(10)
        progresso.addWidget(self._label_tempo_decorrido)
        progresso.addWidget(self._slider_progresso, stretch=1)
        progresso.addWidget(self._label_tempo_total)

        centro = QVBoxLayout()
        centro.setSpacing(6)
        centro.addLayout(controles)
        centro.addLayout(progresso)
        area_centro = QWidget()
        area_centro.setLayout(centro)

        botao_letras = _botao_texto_icone("Letras", "letras", "botaoPlayerTexto", tamanho_icone=17)
        botao_letras.clicked.connect(lambda: self._mudar_view("now"))
        botao_fila = _botao_texto_icone("Fila", "fila", "botaoPlayerTexto", tamanho_icone=17)
        botao_fila.clicked.connect(lambda: self._mudar_view("queue"))
        self._botoes_player_texto = {botao_letras: botao_letras.text(), botao_fila: botao_fila.text()}
        # Como no Spotify (pedido do usuário, 2026-09-26): botões sempre do
        # mesmo tamanho, só a linha do tempo cresce com a janela. Antes a
        # área central tinha largura máxima e a sobra esticava Letras/Fila.
        for botao in (botao_letras, botao_fila):
            botao.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        for botao in (botao_letras, botao_fila, self._botao_like, self._botao_dislike):
            neon.aplicar(botao, raio=20, alpha=130)

        separador = QFrame()
        separador.setObjectName("separadorVertical")
        separador.setFixedSize(1, 30)

        icone_volume = QLabel()
        icone_volume.setPixmap(icones.pixmap("volume", styles.COR_TEXTO, 20))

        # Três blocos, como no Spotify: esquerda (capa, título, votos) e
        # direita (Letras, Fila, volume) encostados nas bordas e com a mesma
        # "fatia" de espaço (stretch 1 cada), e o centro com largura fixa,
        # recalculada em `_ajustar_centro_player` até `LARGURA_MAX_CENTRO`
        # - fica sempre no meio da janela, e a sobra vira espaço vazio nos
        # lados, nunca botão ou barra esticados.
        bloco_esquerdo = QWidget()
        linha_esquerda = QHBoxLayout(bloco_esquerdo)
        linha_esquerda.setContentsMargins(0, 0, 0, 0)
        linha_esquerda.setSpacing(14)
        self._linha_esquerda_player = linha_esquerda
        for widget in (self._capa_player, area_texto, self._botao_like, self._botao_dislike):
            linha_esquerda.addWidget(widget)
        linha_esquerda.addStretch()

        bloco_direito = QWidget()
        linha_direita = QHBoxLayout(bloco_direito)
        linha_direita.setContentsMargins(0, 0, 0, 0)
        linha_direita.setSpacing(14)
        self._linha_direita_player = linha_direita
        linha_direita.addStretch()
        linha_direita.addWidget(botao_letras)
        linha_direita.addWidget(botao_fila)
        linha_direita.addSpacing(4)
        linha_direita.addWidget(separador)
        linha_direita.addSpacing(4)
        linha_direita.addWidget(icone_volume)
        linha_direita.addWidget(self._slider_volume)

        layout.addWidget(bloco_esquerdo, stretch=1)
        layout.addWidget(area_centro)
        layout.addWidget(bloco_direito, stretch=1)
        self._blocos_player = (bloco_esquerdo, area_centro, bloco_direito)

        self._definir_controles_habilitados(False)
        return barra

    @staticmethod
    def _icone_like():
        return faixas_ui.icone_curtir(18)

    def _definir_icone_play_pause(self, tocando):
        self._botao_play_pause.setIcon(icones.icone("pause" if tocando else "play", "#ffffff", 16))

    def _definir_controles_habilitados(self, habilitado):
        for botao in (self._botao_dislike, self._botao_like, self._botao_play_pause):
            botao.setEnabled(habilitado)

    def _mostrar_capa_padrao(self, titulo, artista):
        capa = arte.capa_arredondada("generico", LADO_CAPA_PLAYER, 8, f"{artista}::{titulo}")
        self._capa_player.setPixmap(capa)

    def _atualizar_view_fila(self):
        if self._stack.currentWidget() is self._views["queue"]:
            self._views["queue"].atualizar()

    def _atualizar_botoes_modo(self):
        aleatorio, repetir = self._ctrl.aleatorio, self._ctrl.repetir
        self._botao_aleatorio.definir(
            "aleatorio", aleatorio,
            "Aleatório: ligado (sorteia a próxima entre as da fila)" if aleatorio else "Aleatório: desligado",
        )
        self._botao_repetir.definir("repetir_um" if repetir == "faixa" else "repetir", repetir != "desligado", DICA_REPETIR[repetir])

    # ---------------- reprodução (controlador compartilhado) ----------------

    def _conectar_controlador(self):
        ctrl = self._ctrl
        ctrl.faixa_mudou.connect(self._ao_mudar_faixa)
        ctrl.progresso.connect(self._ao_progresso)
        ctrl.tocando_mudou.connect(self._ao_mudar_tocando)
        ctrl.voto_mudou.connect(self._ao_mudar_voto)
        ctrl.capa_mudou.connect(self._ao_mudar_capa)
        ctrl.mensagem.connect(self._label_faixa_atual.setText)
        ctrl.fila_mudou.connect(self._atualizar_view_fila)
        ctrl.modos_mudaram.connect(lambda *_: self._atualizar_botoes_modo())
        ctrl.votos_mudaram.connect(self._atualizar_sidebar_playlists)
        ctrl.troca_concluida.connect(self.close)

    def _ao_mudar_faixa(self, faixa):
        if not faixa:
            return
        titulo, artista = faixa["titulo"], faixa["artista"]
        self._label_faixa_atual.setText(self._label_faixa_atual.fontMetrics().elidedText(titulo, Qt.ElideRight, 210))
        self._label_faixa_atual.setToolTip(titulo)
        self._label_artista_atual.setText(artista)
        self._mostrar_capa_padrao(titulo, artista)
        self._views["now"].definir_faixa_atual(titulo, artista, self._ctrl.duracao or None)
        self._definir_controles_habilitados(True)

    def _ao_progresso(self, posicao, duracao):
        if duracao:
            self._slider_progresso.setEnabled(True)
            self._slider_progresso.setRange(0, int(duracao))
            if not self._slider_progresso.isSliderDown():
                self._slider_progresso.setValue(min(int(posicao), int(duracao)))
        self._label_tempo_decorrido.setText(formatar_tempo(posicao))
        self._label_tempo_total.setText(formatar_tempo(duracao))

    def _ao_mudar_tocando(self, tocando):
        self._definir_icone_play_pause(tocando)
        self._definir_tocando(tocando)

    def _ao_mudar_voto(self, voto):
        self._botao_like.setChecked(voto == "positivo")
        self._botao_dislike.setChecked(voto == "negativo")

    def _ao_mudar_capa(self, imagem):
        faixa = self._ctrl.faixa_atual
        if imagem is None:
            if faixa:
                self._mostrar_capa_padrao(faixa["titulo"], faixa["artista"])
            return
        self._capa_player.setPixmap(arte.recortar_quadrado_arredondado(imagem, LADO_CAPA_PLAYER, 8))

    # Atalhos usados pelas telas (Início, Fila, Artista...): tudo vai pro controlador.
    def _tocar_faixa(self, titulo, artista, origem="fila"):
        self._ctrl.tocar_faixa(titulo, artista, origem=origem)

    def _iniciar_caos(self, *_):
        """Botões de Caos (o `clicked` do Qt manda um `checked` junto)."""
        self._ctrl.iniciar_caos()

    def _votar_faixa_da_fila(self, faixa, positivo):
        self._ctrl.votar_faixa(faixa, positivo)

    def closeEvent(self, event):
        if self._encerrado:
            # Achado em teste (2026-09-26): o closeEvent pode chegar 2x
            # (close() + saída da aplicação); na 2ª o MPV já foi encerrado.
            super().closeEvent(event)
            return
        self._encerrado = True
        self._salvar_janela()
        if self._cursor_borda is not None:
            QApplication.restoreOverrideCursor()
        QApplication.instance().removeEventFilter(self)
        self._timer_efeitos.stop()
        self._ctrl.encerrar()
        super().closeEvent(event)


def criar_aplicacao():
    app = QApplication.instance() or QApplication([])
    janela = FullWindow()
    return app, janela
