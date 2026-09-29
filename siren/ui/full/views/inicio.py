# -*- coding: utf-8 -*-
"""Home do SIREN: descoberta e biblioteca em uma única superfície.

Visual "noturno azul" (2026-09-25): cartões de playlist com capa
procedural (`ui/full/arte.py`), cartão de destaque quando o ECHO não traz
sugestões e estados vazios com ícone, em vez das prateleiras de texto puro
(`QListWidget` em grade) da primeira versão."""
import time
from datetime import datetime

from PySide6.QtCore import QRectF, QSize, Qt, QThread, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QStyle, QStyleOption, QVBoxLayout, QWidget,
)

from siren.core import playlists as playlists_mod
from siren.integrations import echo_client
from siren.ui.full import arte, icones, neon, styles

LIMITE_CARTOES_PLAYLIST = 6
LIMITE_CARTOES_FAIXA = 8


class _CarregarInicioWorker(QThread):
    concluido = Signal(list, list)

    def run(self):
        self.concluido.emit(echo_client.obter_em_alta(), echo_client.obter_redescobertas())


def _rotulo(texto, nome_objeto, parent=None):
    rotulo = QLabel(texto, parent)
    rotulo.setObjectName(nome_objeto)
    rotulo.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    return rotulo


def _rotulo_icone(nome, cor, tamanho, parent=None):
    rotulo = QLabel(parent)
    rotulo.setPixmap(icones.pixmap(nome, cor, tamanho))
    rotulo.setFixedSize(tamanho, tamanho)
    rotulo.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    return rotulo


def _botao_play(tamanho, nome_objeto="botaoPlayCartao"):
    botao = QPushButton()
    botao.setObjectName(nome_objeto)
    botao.setFixedSize(tamanho, tamanho)
    botao.setIcon(icones.icone("play", "#ffffff", 18))
    botao.setIconSize(QSize(int(tamanho * 0.42), int(tamanho * 0.42)))
    botao.setCursor(Qt.PointingHandCursor)
    return botao


def _desenhar_capa_cortada(pintor, pixmap, alvo):
    """Desenha `pixmap` preenchendo `alvo` sem distorcer (corta as sobras,
    igual `object-fit: cover`)."""
    proporcao_alvo = alvo.width() / max(1.0, alvo.height())
    largura = pixmap.width()
    altura = pixmap.height()
    if largura / max(1, altura) > proporcao_alvo:
        nova_largura = altura * proporcao_alvo
        origem = QRectF((largura - nova_largura) / 2, 0, nova_largura, altura)
    else:
        nova_altura = largura / proporcao_alvo
        origem = QRectF(0, (altura - nova_altura) / 2, largura, nova_altura)
    pintor.drawPixmap(alvo, pixmap, origem)


class _RotuloElidido(QLabel):
    """QLabel que corta com "…" quando não cabe, em vez de simplesmente
    sumir com o fim do texto (ex.: nome de playlist longo num cartão
    estreito)."""

    def __init__(self, texto, nome_objeto):
        super().__init__(texto)
        self._completo = texto
        self.setObjectName(nome_objeto)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setMinimumWidth(40)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self.setText(self.fontMetrics().elidedText(self._completo, Qt.ElideRight, self.width()))


class _Clicavel(QFrame):
    """Base dos cartões: cursor de mão, realce no hover e callback no clique."""

    def __init__(self, ao_clicar, parent=None):
        super().__init__(parent)
        self._ao_clicar = ao_clicar
        self._hover = False
        self.setCursor(Qt.PointingHandCursor)

    def enterEvent(self, evento):
        self._hover = True
        self.update()
        super().enterEvent(evento)

    def leaveEvent(self, evento):
        self._hover = False
        self.update()
        super().leaveEvent(evento)

    def mouseReleaseEvent(self, evento):
        if evento.button() == Qt.LeftButton and self.rect().contains(evento.position().toPoint()):
            self._ao_clicar()
        super().mouseReleaseEvent(evento)


class CartaoPlaylist(_Clicavel):
    ICONE_POR_TEMA = {"curtidas": "coracao_cheio", "nao_curtidas": "coracao_partido"}
    RAIO = 14

    def __init__(self, nome, rotulo, quantidade, ao_abrir, ao_tocar, parent=None):
        super().__init__(lambda: ao_abrir(nome), parent)
        self._tema = arte.tema_da_playlist(nome)
        self._nome = nome
        self.setFixedHeight(156)
        self.setMinimumWidth(220)

        titulo = _RotuloElidido(rotulo, "tituloCartao")
        titulo.setStyleSheet("font-size: 16px; font-weight: 700;")
        self.setToolTip(rotulo)
        contagem = _rotulo(f"{quantidade} músicas", "legendaCartao")
        contagem.setStyleSheet(f"color: {styles.COR_TEXTO_FRACO}; font-size: 12px;")
        textos = QVBoxLayout()
        textos.setSpacing(0)
        textos.addWidget(titulo)
        textos.addWidget(contagem)

        botao = _botao_play(44)
        botao.setToolTip(f"Tocar {rotulo}")
        botao.clicked.connect(lambda: ao_tocar(nome))

        rodape = QHBoxLayout()
        rodape.setSpacing(12)
        rodape.addWidget(_rotulo_icone(self.ICONE_POR_TEMA.get(self._tema, "nota"), "#ffffff", 22))
        rodape.addLayout(textos, stretch=1)
        rodape.addWidget(botao)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 18, 16)
        layout.addStretch()
        layout.addLayout(rodape)
        neon.aplicar(self)

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setRenderHint(QPainter.SmoothPixmapTransform)
        retangulo = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        caminho = QPainterPath()
        caminho.addRoundedRect(retangulo, self.RAIO, self.RAIO)
        pintor.setClipPath(caminho)
        _desenhar_capa_cortada(pintor, arte.capa(self._tema, 420, 170, self._nome), retangulo)
        sombra = QLinearGradient(0, retangulo.height() * 0.35, 0, retangulo.height())
        sombra.setColorAt(0, QColor(4, 8, 20, 0))
        sombra.setColorAt(1, QColor(4, 8, 20, 215))
        pintor.fillRect(retangulo, sombra)
        if self._hover:
            pintor.fillRect(retangulo, QColor(255, 255, 255, 14))
        pintor.setClipping(False)
        pintor.setPen(QPen(QColor(styles.COR_BIOLUM) if self._hover else QColor(150, 180, 255, 40), 1))
        pintor.setBrush(Qt.NoBrush)
        pintor.drawPath(caminho)


class CartaoFaixa(_Clicavel):
    """Sugestão do ECHO: capa procedural quadrada + título + artista."""

    LADO = 150

    def __init__(self, faixa, ao_tocar, parent=None):
        super().__init__(lambda: ao_tocar(faixa), parent)
        semente = f"{faixa['artista']}::{faixa['titulo']}"
        self.setFixedWidth(self.LADO + 16)
        self.setToolTip(f"{faixa['titulo']} · {faixa['artista']}")

        capa = QLabel()
        capa.setFixedSize(self.LADO, self.LADO)
        capa.setPixmap(arte.capa_arredondada("generico", self.LADO, 10, semente))
        capa.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        titulo = _rotulo(faixa["titulo"], "tituloCartaoFaixa")
        titulo.setStyleSheet("font-weight: 600;")
        artista = _rotulo(faixa["artista"], "legendaCartaoFaixa")
        artista.setStyleSheet(f"color: {styles.COR_TEXTO_FRACO}; font-size: 12px;")
        for rotulo in (titulo, artista):
            rotulo.setFixedWidth(self.LADO)
            rotulo.setText(rotulo.fontMetrics().elidedText(rotulo.text(), Qt.ElideRight, self.LADO))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 10)
        layout.setSpacing(4)
        layout.addWidget(capa)
        layout.addWidget(titulo)
        layout.addWidget(artista)
        neon.aplicar(self, raio=24, alpha=150)

    def paintEvent(self, evento):
        if not self._hover:
            return
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QColor(255, 255, 255, 16))
        pintor.drawRoundedRect(QRectF(self.rect()), 12, 12)


class _MosaicoCapas(QWidget):
    """Leque de capas sobrepostas do cartão de destaque."""

    # (deslocamento x, escala, ângulo, tema) - do fundo pra frente, centro por último
    CARTAS = [
        (-150, 0.62, -8, "generico"), (150, 0.62, 8, "generico"),
        (-82, 0.8, -5, "nao_curtidas"), (82, 0.8, 5, "descobertas"),
        (0, 1.0, 0, "curtidas"),
    ]
    LADO = 124

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(380, 132)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setRenderHint(QPainter.SmoothPixmapTransform)
        for indice, (deslocamento, escala, angulo, tema) in enumerate(self.CARTAS):
            lado = self.LADO * escala
            pintor.save()
            pintor.translate(self.width() / 2 + deslocamento, self.height() / 2)
            pintor.rotate(angulo)
            alvo = QRectF(-lado / 2, -lado / 2, lado, lado)
            caminho = QPainterPath()
            caminho.addRoundedRect(alvo, 6, 6)
            pintor.setClipPath(caminho)
            base = arte.capa(tema, self.LADO, self.LADO, f"mosaico{indice}")
            pintor.drawPixmap(alvo, base, QRectF(base.rect()))
            if escala < 1:
                pintor.fillRect(alvo, QColor(6, 11, 24, int(300 * (1 - escala))))
            pintor.setClipping(False)
            pintor.setPen(QPen(QColor(200, 220, 255, 90 if escala == 1 else 45), 1))
            pintor.setBrush(Qt.NoBrush)
            pintor.drawPath(caminho)
            pintor.restore()


class CartaoDestaque(QFrame):
    def __init__(self, sobrelinha, titulo, texto, ao_tocar, parent=None):
        super().__init__(parent)
        self.setObjectName("cartaoDestaque")
        self.setMinimumHeight(150)

        textos = QVBoxLayout()
        textos.setSpacing(4)
        textos.addStretch()
        textos.addWidget(_rotulo(sobrelinha.upper(), "rotuloSobrelinha"))
        textos.addWidget(_rotulo(titulo, "tituloDestaque"))
        corpo = _rotulo(texto, "textoDestaque")
        corpo.setWordWrap(True)
        textos.addWidget(corpo)
        textos.addStretch()

        botao = _botao_play(54, "botaoPlay")
        botao.clicked.connect(ao_tocar)
        neon.aplicar(botao, raio=28, alpha=220)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 24, 8)
        layout.setSpacing(24)
        layout.addWidget(_MosaicoCapas())
        layout.addLayout(textos, stretch=1)
        layout.addWidget(botao)


class CartaoVazio(QFrame):
    def __init__(self, titulo, texto, icone="historico_seta", parent=None):
        super().__init__(parent)
        self.setObjectName("cartaoVazio")
        self.setMinimumHeight(80)

        caixa = QLabel()
        caixa.setObjectName("caixaIconeVazio")
        caixa.setFixedSize(56, 56)
        caixa.setAlignment(Qt.AlignCenter)
        caixa.setPixmap(icones.pixmap(icone, styles.COR_TEXTO_FRACO, 26))

        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addStretch()
        textos.addWidget(_rotulo(titulo, "tituloVazio"))
        if texto:
            textos.addWidget(_rotulo(texto, "textoVazio"))
        textos.addStretch()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(24)
        layout.addWidget(caixa)
        layout.addLayout(textos, stretch=1)


class BotaoCaos(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("botaoCaos")
        self.setFixedHeight(50)
        self.setCursor(Qt.PointingHandCursor)
        texto = _rotulo("Surpreenda-me com o Caos", "textoCaos")
        texto.setStyleSheet("color: white; font-size: 14px; font-weight: 700;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 22, 0)
        layout.setSpacing(12)
        layout.addWidget(_rotulo_icone("brilho", "#ffffff", 20))
        layout.addWidget(texto)
        layout.addSpacing(8)
        layout.addWidget(_rotulo_icone("seta_direita", "#ffffff", 18))
        self.setFixedWidth(layout.sizeHint().width())
        neon.aplicar(self, raio=34, alpha=230)


class _CorpoHome(QWidget):
    """Pinta a paisagem (colinas + mar) atrás do conteúdo da Home e o
    reflexo da lua na água. Quem anima o reflexo é o relógio único de
    efeitos da janela (`avancar`), que repinta só a coluna do reflexo."""

    def _retangulo_paisagem(self):
        altura = min(self.height() * 0.5, 360)
        return QRectF(0, self.height() - altura, self.width(), altura)

    def _x_lua(self):
        janela = self.window()
        if not hasattr(janela, "posicao_lua"):
            return self.width() * 0.8
        return float(self.mapFrom(janela, janela.posicao_lua().toPoint()).x())

    def avancar(self):
        if not self.isVisible():
            return
        self.update(arte.retangulo_reflexo_lua(self._retangulo_paisagem(), self._x_lua()))

    def paintEvent(self, evento):
        opcao = QStyleOption()
        opcao.initFrom(self)
        pintor = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opcao, pintor, self)
        retangulo = self._retangulo_paisagem()
        arte.pintar_paisagem(pintor, retangulo)
        luar = getattr(self.window(), "_intensidade_luar", 0.0)
        arte.pintar_reflexo_lua(pintor, retangulo, self._x_lua(), time.monotonic(), 0.55 + 0.45 * luar)


class _Secao(QWidget):
    """Título + subtítulo + um slot de conteúdo trocável."""

    def __init__(self, titulo, parent=None):
        super().__init__(parent)
        self._subtitulo = _rotulo("", "subtituloSecao")
        self._conteudo = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self._layout.addWidget(_rotulo(titulo, "tituloSecao"))
        self._layout.addWidget(self._subtitulo)
        self._layout.addSpacing(12)

    def definir(self, subtitulo, widget):
        self._subtitulo.setText(subtitulo)
        if self._conteudo is not None:
            self._conteudo.deleteLater()
        self._conteudo = widget
        self._layout.addWidget(widget)


class ViewInicio(QWidget):
    """Equivalente à Home do Spotify, alimentada pela inteligência do ECHO."""

    def __init__(self, ao_tocar, ao_abrir_playlist, ao_iniciar_caos, ao_tocar_playlist):
        super().__init__()
        self._ao_tocar = ao_tocar
        self._ao_abrir_playlist = ao_abrir_playlist
        self._ao_iniciar_caos = ao_iniciar_caos
        self._ao_tocar_playlist = ao_tocar_playlist
        self._worker = None
        self._carregado = False

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        corpo = _CorpoHome()
        self._corpo = corpo
        corpo.setObjectName("homeBody")
        corpo.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(corpo)
        layout.setContentsMargins(32, 4, 32, 28)
        layout.setSpacing(18)

        cabecalho = QVBoxLayout()
        cabecalho.setSpacing(0)
        cabecalho.addWidget(_rotulo(self._saudacao(), "tituloHome"))
        cabecalho.addWidget(_rotulo("Que tal continuar ouvindo algo incrível?", "subtituloHome"))
        layout.addLayout(cabecalho)

        self._grade_atalhos = QGridLayout()
        self._grade_atalhos.setHorizontalSpacing(18)
        self._grade_atalhos.setVerticalSpacing(18)
        layout.addLayout(self._grade_atalhos)

        self._secao_feito = _Secao("Feito para você")
        layout.addWidget(self._secao_feito)
        self._secao_voltar = _Secao("Vale ouvir de novo")
        layout.addWidget(self._secao_voltar)

        botao_caos = BotaoCaos()
        botao_caos.clicked.connect(self._ao_iniciar_caos)
        layout.addSpacing(4)
        layout.addWidget(botao_caos)
        layout.addStretch()

        scroll.setWidget(corpo)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(scroll)

    @staticmethod
    def _saudacao():
        hora = datetime.now().hour
        if hora < 12:
            return "Bom dia"
        if hora < 18:
            return "Boa tarde"
        return "Boa noite"

    def _preencher_atalhos(self):
        while self._grade_atalhos.count():
            item = self._grade_atalhos.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        especiais = [
            (playlists_mod.NOME_PLAYLIST_CURTIDAS, "Músicas Curtidas"),
            (playlists_mod.NOME_PLAYLIST_NAO_CURTIDAS, "Não Curtidas"),
        ]
        nomes = {nome for nome, _rotulo in especiais}
        entradas = especiais + [
            (pl["nome"], pl["nome"])
            for pl in playlists_mod.listar()
            if pl["nome"] not in nomes
        ]
        entradas = entradas[:LIMITE_CARTOES_PLAYLIST]
        # Com só as 2 coleções automáticas (sem playlist do usuário), 2
        # colunas ocupam a largura toda em vez de deixar um buraco na 3ª.
        colunas = min(3, max(1, len(entradas)))
        for indice, (nome, rotulo) in enumerate(entradas):
            cartao = CartaoPlaylist(
                nome, rotulo, len(playlists_mod.obter_faixas(nome)),
                ao_abrir=self._ao_abrir_playlist, ao_tocar=self._ao_tocar_playlist,
            )
            self._grade_atalhos.addWidget(cartao, indice // colunas, indice % colunas)
        for coluna in range(3):
            self._grade_atalhos.setColumnStretch(coluna, 1 if coluna < colunas else 0)

    def _tocar_faixa(self, faixa):
        self._ao_tocar(faixa["titulo"], faixa["artista"], origem="descoberta")

    def _grade_faixas(self, faixas):
        container = QWidget()
        linha = QHBoxLayout(container)
        linha.setContentsMargins(0, 0, 0, 0)
        linha.setSpacing(10)
        for faixa in faixas[:LIMITE_CARTOES_FAIXA]:
            linha.addWidget(CartaoFaixa(faixa, self._tocar_faixa))
        linha.addStretch()
        rolagem = QScrollArea()
        rolagem.setWidgetResizable(True)
        rolagem.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        rolagem.setFixedHeight(container.sizeHint().height() + 12)
        rolagem.setWidget(container)
        return rolagem

    def _mostrar_feito(self, faixas):
        if faixas:
            self._secao_feito.definir("Selecionadas pelo ECHO a partir do que você curte.", self._grade_faixas(faixas))
            return
        self._secao_feito.definir(
            "O ECHO está offline, mas suas playlists continuam disponíveis.",
            CartaoDestaque(
                "Continue ouvindo", "ECHO offline",
                "Suas playlists continuam disponíveis, mesmo sem ele.",
                ao_tocar=lambda: self._ao_tocar_playlist(playlists_mod.NOME_PLAYLIST_CURTIDAS),
            ),
        )

    def _mostrar_redescobertas(self, faixas):
        if faixas:
            self._secao_voltar.definir("Faixas que você ouvia e andam esquecidas.", self._grade_faixas(faixas))
            return
        self._secao_voltar.definir(
            "Ainda não há músicas para redescobrir.",
            CartaoVazio("Ainda não há músicas para redescobrir.", "Suas músicas ouvidas recentemente aparecerão aqui."),
        )

    def atualizar(self):
        self._preencher_atalhos()
        if self._worker is not None and self._worker.isRunning():
            return
        if self._carregado:
            return
        self._secao_feito.definir("Consultando o ECHO…", CartaoVazio("Buscando novidades no ECHO…", "", icone="descoberta"))
        self._secao_voltar.definir("Revisitando seu histórico…", CartaoVazio("Revisitando seu histórico…", ""))
        worker = _CarregarInicioWorker(self)
        worker.concluido.connect(lambda em_alta, antigas, w=worker: self._concluir(w, em_alta, antigas))
        worker.finished.connect(lambda w=worker: self._finalizar(w))
        self._worker = worker
        worker.start()

    def avancar_efeitos(self):
        self._corpo.avancar()

    def carregando(self):
        """Consultando o ECHO agora? A janela usa pra pulsar o sonar."""
        return self._worker is not None and self._worker.isRunning()

    def atualizar_biblioteca(self):
        """Atualiza apenas os atalhos locais, sem refazer chamadas ao ECHO."""
        self._preencher_atalhos()

    def _concluir(self, worker, em_alta, redescobertas):
        if worker is not self._worker:
            return
        self._carregado = True
        self._mostrar_feito(em_alta)
        self._mostrar_redescobertas(redescobertas)

    def _finalizar(self, worker):
        if worker is self._worker:
            self._worker = None
        worker.deleteLater()
