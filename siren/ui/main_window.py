# -*- coding: utf-8 -*-
"""Modo Leve: miniplayer no estilo do Spotify (2026-09-26, pedido do
usuário: "o Spotify tem um miniplayer, é assim que deve ser o modo leve").

- Janela pequena, sem borda, sempre por cima; arrasta pela alça do topo e
  redimensiona pelo canto inferior direito.
- A capa ocupa o centro. Os controles (volume, aleatório, anterior, tocar,
  próximo, repetir, abrir o Modo Completo) só aparecem com o mouse sobre a
  capa; o controle de volume, só com o mouse sobre o botão de volume.
- Embaixo: tempo e linha do tempo, título, artista e o botão "+", que é o
  coração de curtir e o não curtir, os mesmos dos outros botões de voto do
  SIREN (Músicas Curtidas/Não Curtidas + voto pro ECHO; o não curtir pula
  pra próxima, como no player do Modo Completo).

Toda a reprodução (fila, Caos com fila, aleatório/repetir, retomar a
última faixa, troca de modo sem parar a música) é o mesmo
`playback/controlador.py` do Modo Completo. Continua leve de propósito
(docs/PLANO_SIREN.md, seção 13): sem vidro fosco, sem animação contínua,
sem as telas do Completo - só repinta quando algo muda."""
from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QPushButton, QSizeGrip, QSlider, QStyle, QVBoxLayout, QWidget,
)

from siren.core import config as config_mod
from siren.core import sessao as sessao_mod
from siren.playback.controlador import ControladorReproducao, formatar_tempo
from siren.ui import mode_switch, win32_dwm
from siren.ui.full import arte, icones, styles
from siren.ui.full.faixas import icone_curtir, icone_nao_curtir

TAMANHO_PADRAO = (320, 360)
TAMANHO_MINIMO = (260, 300)

QSS = f"""
QWidget {{ color: {styles.COR_TEXTO}; font-family: "Segoe UI Variable Text", "Segoe UI"; font-size: 12px; }}
#miniRaiz {{ background: #0b1226; }}
QPushButton#miniBotao {{ background: transparent; border: none; border-radius: 16px; }}
QPushButton#miniBotao:hover {{ background: rgba(255, 255, 255, 0.14); }}
QPushButton#miniPlay {{ background: #ffffff; border: none; border-radius: 24px; }}
QPushButton#miniPlay:hover {{ background: #dfe8ff; }}
#miniTitulo {{ font-size: 16px; font-weight: 700; }}
#miniArtista {{ color: {styles.COR_TEXTO_FRACO}; font-size: 12px; }}
#miniTempo {{ color: {styles.COR_TEXTO_FRACO}; font-size: 10px; }}
#miniVolume {{ background: #151e38; border: 1px solid rgba(130, 160, 255, 0.24); border-radius: 8px; }}
QSlider::groove:horizontal {{ height: 4px; background: rgba(255, 255, 255, 0.18); border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: #ffffff; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: #ffffff; width: 10px; height: 10px; margin: -3px 0px; border-radius: 5px; }}
QSlider::groove:vertical {{ width: 4px; background: rgba(255, 255, 255, 0.18); border-radius: 2px; }}
QSlider::add-page:vertical {{ background: {styles.COR_ACCENT_CLARO}; border-radius: 2px; }}
QSlider::handle:vertical {{ background: #ffffff; width: 12px; height: 12px; margin: 0px -4px; border-radius: 6px; }}
"""


def _botao(nome_icone, dica, tamanho=32, lado_icone=18, cor="#ffffff"):
    botao = QPushButton()
    botao.setObjectName("miniBotao")
    botao.setFixedSize(tamanho, tamanho)
    botao.setIcon(icones.icone(nome_icone, cor, lado_icone))
    botao.setIconSize(QSize(lado_icone, lado_icone))
    botao.setCursor(Qt.PointingHandCursor)
    botao.setToolTip(dica)
    return botao


class _SliderSeek(QSlider):
    """Clique pula exatamente pro ponto apontado."""

    def __init__(self, ao_buscar):
        super().__init__(Qt.Horizontal)
        self._ao_buscar = ao_buscar
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, evento):
        super().mouseReleaseEvent(evento)
        if evento.button() == Qt.LeftButton:
            valor = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), round(evento.position().x()), max(1, self.width()))
            self.setValue(valor)
            self._ao_buscar(valor)


class _BarraTopo(QWidget):
    """Abrir o Modo Completo (sempre visível, 2026-09-26 - antes só existia
    nos controles escondidos sobre a capa e o usuário não achou) + alça de
    arrastar (a barra inteira arrasta) + fechar."""

    def __init__(self, janela, ao_expandir):
        super().__init__()
        self._janela = janela
        self.setFixedHeight(28)
        alca = QLabel()
        alca.setPixmap(icones.pixmap("alca", styles.COR_TEXTO_FRACO, 20))
        alca.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        fechar = _botao("fechar", "Fechar", 26, 14, styles.COR_TEXTO_FRACO)
        fechar.clicked.connect(janela.close)
        expandir = _botao("expandir", "Abrir o Modo Completo", 26, 14, styles.COR_TEXTO_FRACO)
        expandir.clicked.connect(ao_expandir)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.addWidget(expandir)
        layout.addStretch()
        layout.addWidget(alca)
        layout.addStretch()
        layout.addWidget(fechar)

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton and self._janela.windowHandle() is not None:
            self._janela.windowHandle().startSystemMove()


class _AreaCapa(QWidget):
    """Capa centralizada; com o mouse em cima, escurece e mostra os
    controles (filho `controles`)."""

    def __init__(self, controles):
        super().__init__()
        self._capa = None
        self._faixa = None
        self._hover = False
        self._controles = controles
        controles.setParent(self)
        controles.hide()
        self.setMouseTracking(True)
        self.setMinimumHeight(140)

    def definir_capa(self, imagem, faixa):
        self._capa = imagem
        self._faixa = faixa
        self.update()

    def manter_controles(self, visivel):
        self._hover = visivel
        self._controles.setVisible(visivel)
        self.update()

    def enterEvent(self, evento):
        self.manter_controles(True)
        super().enterEvent(evento)

    def leaveEvent(self, evento):
        # O popup de volume fica fora da capa: não esconde enquanto ele está aberto.
        if not getattr(self.window(), "volume_aberto", False):
            self.manter_controles(False)
        super().leaveEvent(evento)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._controles.setGeometry(self.rect())

    def _retangulo_capa(self):
        lado = max(40, min(self.width(), self.height()) - 8)
        return QRectF((self.width() - lado) / 2, (self.height() - lado) / 2, lado, lado)

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setRenderHint(QPainter.SmoothPixmapTransform)
        alvo = self._retangulo_capa()
        caminho = QPainterPath()
        caminho.addRoundedRect(alvo, 8, 8)
        pintor.setClipPath(caminho)
        if self._capa is not None and not self._capa.isNull():
            origem = self._capa.rect()
            menor = min(origem.width(), origem.height())
            recorte = QRectF((origem.width() - menor) / 2, (origem.height() - menor) / 2, menor, menor)
            pintor.drawPixmap(alvo, self._capa, recorte)
        else:
            semente = f"{self._faixa['artista']}::{self._faixa['titulo']}" if self._faixa else "siren"
            procedural = arte.capa("generico", 240, 240, semente)
            pintor.drawPixmap(alvo, procedural, QRectF(procedural.rect()))
        if self._hover:
            pintor.fillRect(alvo, QColor(4, 8, 20, 150))


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SIREN")
        self.setObjectName("miniRaiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setMinimumSize(*TAMANHO_MINIMO)
        self.resize(*TAMANHO_PADRAO)
        geometria = sessao_mod.carregar_janela(sessao_mod.ARQUIVO_JANELA_MINI)
        telas = [t.availableGeometry().getRect() for t in QApplication.screens()]
        if sessao_mod.geometria_visivel(geometria, telas):
            self.setGeometry(geometria["x"], geometria["y"], max(geometria["largura"], TAMANHO_MINIMO[0]),
                             max(geometria["altura"], TAMANHO_MINIMO[1]))
        self.setStyleSheet(QSS)
        self.volume_aberto = False
        self._encerrado = False
        self._capa = None

        self._ctrl = ControladorReproducao(self)

        # ---- controles sobre a capa ----
        self._botao_volume = _botao("volume", "Volume")
        self._botao_aleatorio = _botao("aleatorio", "Aleatório")
        self._botao_anterior = _botao("anterior", "Anterior", 34, 20)
        self._botao_play = QPushButton()
        self._botao_play.setObjectName("miniPlay")
        self._botao_play.setFixedSize(48, 48)
        self._botao_play.setIconSize(QSize(20, 20))
        self._botao_play.setCursor(Qt.PointingHandCursor)
        self._botao_proximo = _botao("proximo", "Próxima", 34, 20)
        self._botao_repetir = _botao("repetir", "Repetir")
        self._botao_expandir = _botao("expandir", "Abrir o Modo Completo", lado_icone=16)
        self._botao_aleatorio.clicked.connect(self._ctrl.alternar_aleatorio)
        self._botao_anterior.clicked.connect(self._ctrl.anterior)
        self._botao_play.clicked.connect(self._ctrl.alternar_play_pause)
        self._botao_proximo.clicked.connect(lambda: self._ctrl.proxima())
        self._botao_repetir.clicked.connect(self._ctrl.alternar_repetir)
        self._botao_expandir.clicked.connect(self._trocar_pro_completo)
        self._botao_volume.installEventFilter(self)

        controles = QWidget()
        linha = QHBoxLayout(controles)
        linha.setContentsMargins(6, 0, 6, 0)
        linha.setSpacing(2)
        linha.addStretch()
        for botao in (self._botao_volume, self._botao_aleatorio, self._botao_anterior, self._botao_play,
                      self._botao_proximo, self._botao_repetir, self._botao_expandir):
            linha.addWidget(botao)
        linha.addStretch()
        self._area_capa = _AreaCapa(controles)

        # ---- popup de volume (só com o mouse sobre o botão de volume) ----
        self._popup_volume = QWidget(self)
        self._popup_volume.setObjectName("miniVolume")
        self._popup_volume.setAttribute(Qt.WA_StyledBackground, True)
        self._slider_volume = QSlider(Qt.Vertical)
        self._slider_volume.setRange(0, 100)
        self._slider_volume.setValue(config_mod.obter("volume_inicial"))
        self._slider_volume.valueChanged.connect(self._ao_mudar_volume)
        layout_volume = QVBoxLayout(self._popup_volume)
        layout_volume.setContentsMargins(6, 10, 6, 10)
        layout_volume.addWidget(self._slider_volume)
        self._popup_volume.setFixedSize(28, 110)
        self._popup_volume.hide()
        self._popup_volume.installEventFilter(self)
        self._timer_volume = QTimer(self)
        self._timer_volume.setSingleShot(True)
        self._timer_volume.setInterval(300)
        self._timer_volume.timeout.connect(self._talvez_fechar_volume)

        # ---- tempo, título, artista, curtir ----
        self._tempo_atual = QLabel("0:00")
        self._tempo_atual.setObjectName("miniTempo")
        self._tempo_total = QLabel("0:00")
        self._tempo_total.setObjectName("miniTempo")
        linha_tempo = QHBoxLayout()
        linha_tempo.addWidget(self._tempo_atual)
        linha_tempo.addStretch()
        linha_tempo.addWidget(self._tempo_total)
        self._slider = _SliderSeek(self._ctrl.buscar_posicao)
        self._slider.setRange(0, 0)

        self._titulo = QLabel("Nada tocando")
        self._titulo.setObjectName("miniTitulo")
        self._artista = QLabel("Toque em play para o Caos")
        self._artista.setObjectName("miniArtista")
        textos = QVBoxLayout()
        textos.setSpacing(0)
        textos.addWidget(self._titulo)
        textos.addWidget(self._artista)
        self._botao_curtir = _botao("coracao", "Curtir (adiciona em Músicas Curtidas)", 36, 22)
        self._botao_curtir.setCheckable(True)
        self._botao_curtir.setIcon(icone_curtir(22, "#ffffff"))
        self._botao_curtir.clicked.connect(self._ao_clicar_curtir)
        self._botao_nao_curtir = _botao("dislike", "Não curtir e pular", 36, 20)
        self._botao_nao_curtir.setCheckable(True)
        self._botao_nao_curtir.setIcon(icone_nao_curtir(20, "#ffffff"))
        self._botao_nao_curtir.clicked.connect(self._ao_clicar_nao_curtir)
        linha_info = QHBoxLayout()
        linha_info.setSpacing(2)
        linha_info.addLayout(textos, stretch=1)
        linha_info.addWidget(self._botao_nao_curtir, alignment=Qt.AlignVCenter)
        linha_info.addWidget(self._botao_curtir, alignment=Qt.AlignVCenter)

        grip = QSizeGrip(self)
        grip.setFixedSize(14, 14)
        linha_grip = QHBoxLayout()
        linha_grip.addStretch()
        linha_grip.addWidget(grip)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(4)
        layout.addWidget(_BarraTopo(self, self._trocar_pro_completo))
        layout.addWidget(self._area_capa, stretch=1)
        layout.addLayout(linha_tempo)
        layout.addWidget(self._slider)
        layout.addSpacing(4)
        layout.addLayout(linha_info)
        layout.addLayout(linha_grip)

        self._conectar()
        self._atualizar_modos()
        self._atualizar_play(False)
        self._ctrl.retomar_sessao()

    # ---------------- controlador ----------------

    def _conectar(self):
        ctrl = self._ctrl
        ctrl.faixa_mudou.connect(self._ao_mudar_faixa)
        ctrl.progresso.connect(self._ao_progresso)
        ctrl.tocando_mudou.connect(self._atualizar_play)
        ctrl.voto_mudou.connect(self._ao_mudar_voto)
        ctrl.capa_mudou.connect(self._ao_mudar_capa)
        ctrl.mensagem.connect(self._artista.setText)
        ctrl.modos_mudaram.connect(lambda *_: self._atualizar_modos())
        ctrl.troca_concluida.connect(self.close)

    def _elidir(self, rotulo, texto):
        rotulo.setToolTip(texto)
        rotulo.setText(rotulo.fontMetrics().elidedText(texto, Qt.ElideRight, max(60, self.width() - 80)))

    def _ao_mudar_faixa(self, faixa):
        if not faixa:
            return
        self._faixa_texto = (faixa["titulo"], faixa["artista"])
        self._elidir(self._titulo, faixa["titulo"])
        self._elidir(self._artista, faixa["artista"])
        self._area_capa.definir_capa(None, faixa)

    def _ao_mudar_capa(self, imagem):
        self._area_capa.definir_capa(imagem, self._ctrl.faixa_atual)

    def _ao_progresso(self, posicao, duracao):
        self._slider.setRange(0, int(duracao or 0))
        if not self._slider.isSliderDown():
            self._slider.setValue(int(posicao))
        self._tempo_atual.setText(formatar_tempo(posicao))
        self._tempo_total.setText(formatar_tempo(duracao))

    def _atualizar_play(self, tocando):
        self._botao_play.setIcon(icones.icone("pause" if tocando else "play", "#0b1226", 20))

    def _ao_clicar_curtir(self):
        # O clique já alterna o `checked`; quem decide o estado real é o
        # voto (sinal `voto_mudou`) - curtir de novo não desfaz o voto.
        self._botao_curtir.setChecked(self._ctrl.voto_atual == "positivo")
        self._ctrl.curtir()

    def _ao_clicar_nao_curtir(self):
        self._botao_nao_curtir.setChecked(self._ctrl.voto_atual == "negativo")
        self._ctrl.nao_curtir()

    def _ao_mudar_voto(self, voto):
        curtida = voto == "positivo"
        self._botao_curtir.setChecked(curtida)
        self._botao_nao_curtir.setChecked(voto == "negativo")
        self._botao_curtir.setToolTip("Em Músicas Curtidas" if curtida else "Curtir (adiciona em Músicas Curtidas)")

    def _atualizar_modos(self):
        aleatorio, repetir = self._ctrl.aleatorio, self._ctrl.repetir
        self._botao_aleatorio.setIcon(icones.icone("aleatorio", styles.COR_ACCENT_CLARO if aleatorio else "#ffffff", 18))
        self._botao_aleatorio.setToolTip("Aleatório: ligado" if aleatorio else "Aleatório: desligado")
        self._botao_repetir.setIcon(icones.icone("repetir_um" if repetir == "faixa" else "repetir",
                                                 styles.COR_ACCENT_CLARO if repetir != "desligado" else "#ffffff", 18))
        self._botao_repetir.setToolTip({"desligado": "Repetir: desligado", "fila": "Repetir: fila", "faixa": "Repetir: esta música"}[repetir])

    # ---------------- volume ----------------

    def _ao_mudar_volume(self, valor):
        self._ctrl.definir_volume(valor)
        self._botao_volume.setIcon(icones.icone("volume_mudo" if valor == 0 else "volume", "#ffffff", 18))

    def _abrir_volume(self):
        botao = self._botao_volume
        canto = botao.mapTo(self, QPoint(botao.width() // 2, 0))
        self._popup_volume.move(canto.x() - self._popup_volume.width() // 2, max(0, canto.y() - self._popup_volume.height() - 4))
        self._popup_volume.show()
        self._popup_volume.raise_()
        self.volume_aberto = True

    def _talvez_fechar_volume(self):
        if self._botao_volume.underMouse() or self._popup_volume.underMouse():
            return
        self._popup_volume.hide()
        self.volume_aberto = False
        if not self._area_capa.underMouse():
            self._area_capa.manter_controles(False)

    def eventFilter(self, objeto, evento):
        popup = getattr(self, "_popup_volume", None)  # eventos chegam antes de o popup existir
        if popup is not None and objeto in (self._botao_volume, popup):
            if evento.type() == evento.Type.Enter:
                self._timer_volume.stop()
                if objeto is self._botao_volume:
                    self._abrir_volume()
            elif evento.type() == evento.Type.Leave:
                self._timer_volume.start()
        return super().eventFilter(objeto, evento)

    # ---------------- janela ----------------

    def showEvent(self, evento):
        super().showEvent(evento)
        win32_dwm.aplicar_cantos_redondos(self)

    def keyPressEvent(self, evento):
        if evento.key() == Qt.Key_Space:
            self._ctrl.alternar_play_pause()
            return
        super().keyPressEvent(evento)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if getattr(self, "_faixa_texto", None):
            self._elidir(self._titulo, self._faixa_texto[0])
            self._elidir(self._artista, self._faixa_texto[1])

    def preparar_troca_de_modo(self):
        """Ver `ui/full/main_window.py::preparar_troca_de_modo`."""
        self._salvar_janela()
        return self._ctrl.iniciar_troca_de_modo()

    def _trocar_pro_completo(self):
        mode_switch.trocar_modo(QApplication.instance(), self, "full")

    def _salvar_janela(self):
        g = self.geometry()
        sessao_mod.salvar_janela(g.x(), g.y(), g.width(), g.height(), False, arquivo=sessao_mod.ARQUIVO_JANELA_MINI)

    def closeEvent(self, evento):
        if not self._encerrado:
            self._encerrado = True
            self._salvar_janela()
            self._ctrl.encerrar()
        super().closeEvent(evento)


def criar_aplicacao():
    app = QApplication.instance() or QApplication([])
    janela = MainWindow()
    return app, janela
