# -*- coding: utf-8 -*-
"""Peças compartilhadas das listas de faixas em tabela (tela Fila e tela do
artista, 2026-09-26): célula de título com capa e artista clicável, botões
de ação por linha e o worker que busca álbum/duração no ECHO."""
from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from siren.core import cache_faixas as cache_mod
from siren.integrations import echo_client
from siren.ui.full import arte, icones, styles

LADO_CAPA = 40
ALTURA_LINHA = 58
LARGURA_MINIMA_TITULO = 260  # abaixo disso a tabela ganha barra de rolagem horizontal


class RotuloElidido(QLabel):
    """Corta com "…" quando não cabe, em vez de vazar pra cima da coluna
    vizinha."""

    def __init__(self, texto, estilo=""):
        super().__init__(texto)
        self._completo = texto
        self.setStyleSheet(estilo)
        self.setMinimumWidth(20)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setToolTip(texto)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self.setText(self.fontMetrics().elidedText(self._completo, Qt.ElideRight, max(0, self.width())))


class RotuloLink(QLabel):
    """Texto clicável (nome do artista): sublinha no hover e emite
    `clicado`, como no Spotify."""

    clicado = Signal()

    def __init__(self, texto, cor=styles.COR_TEXTO_FRACO, tamanho=12):
        super().__init__(texto)
        self._estilo = f"font-size: {tamanho}px; color: {cor};"
        self.setStyleSheet(self._estilo)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

    def enterEvent(self, evento):
        self.setStyleSheet(self._estilo.replace(f"color: {styles.COR_TEXTO_FRACO}", f"color: {styles.COR_TEXTO}") + " text-decoration: underline;")
        super().enterEvent(evento)

    def leaveEvent(self, evento):
        self.setStyleSheet(self._estilo)
        super().leaveEvent(evento)

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            evento.accept()
            return
        super().mousePressEvent(evento)

    def mouseReleaseEvent(self, evento):
        if evento.button() == Qt.LeftButton and self.rect().contains(evento.position().toPoint()):
            self.clicado.emit()
            evento.accept()
            return
        super().mouseReleaseEvent(evento)


class CelulaTitulo(QWidget):
    """Capa + título + artista. Com `ao_abrir_artista`, o nome do artista é
    clicável. Só o nome recebe clique: o resto deixa o mouse passar pra
    tabela (arrastar a linha, duplo clique pra tocar)."""

    def __init__(self, faixa, ao_abrir_artista=None, pulada=False):
        super().__init__()
        capa = QLabel()
        capa.setFixedSize(LADO_CAPA, LADO_CAPA)
        capa.setPixmap(arte.capa_arredondada("generico", LADO_CAPA, 6, f"{faixa['artista']}::{faixa['titulo']}"))
        capa.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        cor_titulo = styles.COR_TEXTO_FRACO if pulada else styles.COR_TEXTO
        titulo = RotuloElidido(faixa["titulo"], f"font-size: 14px; color: {cor_titulo};")
        titulo.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        linha_artista = QHBoxLayout()
        linha_artista.setSpacing(0)
        if ao_abrir_artista is not None:
            artista = RotuloLink(faixa["artista"])
            artista.setToolTip(f"Abrir {faixa['artista']}")
            artista.clicado.connect(lambda: ao_abrir_artista(faixa["artista"]))
        else:
            artista = QLabel(faixa["artista"])
            artista.setStyleSheet(f"font-size: 12px; color: {styles.COR_TEXTO_FRACO};")
            artista.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        linha_artista.addWidget(artista)
        if pulada:
            aviso = QLabel("  ·  não curtida, será pulada")
            aviso.setStyleSheet(f"font-size: 12px; color: {styles.COR_TEXTO_FRACO};")
            aviso.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            linha_artista.addWidget(aviso)
        linha_artista.addStretch()

        textos = QVBoxLayout()
        textos.setSpacing(1)
        textos.addStretch()
        textos.addWidget(titulo)
        textos.addLayout(linha_artista)
        textos.addStretch()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 8, 0)
        layout.setSpacing(12)
        layout.addWidget(capa)
        layout.addLayout(textos, stretch=1)


def botao_acao(nome_icone, dica, cor=styles.COR_TEXTO_FRACO, icone_ativo=None):
    botao = QPushButton()
    botao.setObjectName("botaoAcaoLinha")
    botao.setFixedSize(30, 30)
    botao.setIconSize(QSize(16, 16))
    botao.setCursor(Qt.PointingHandCursor)
    botao.setToolTip(dica)
    if icone_ativo is not None:
        icone = QIcon()
        icone.addPixmap(icones.pixmap(nome_icone, cor, 16), QIcon.Normal, QIcon.Off)
        icone.addPixmap(icone_ativo, QIcon.Normal, QIcon.On)
        botao.setIcon(icone)
        botao.setCheckable(True)
    else:
        botao.setIcon(icones.icone(nome_icone, cor, 16))
    return botao


def icone_curtir(tamanho=16, cor_contorno=styles.COR_TEXTO_FRACO):
    """O MESMO coração em todo botão de curtir do SIREN (player do Completo,
    Fila, tela do artista, miniplayer - 2026-09-26, pedido do usuário):
    contorno quando não curtido, cheio e rosa (`COR_LIKE`) quando curtido
    (estado `checked` do botão). Todos chamam o mesmo voto no controlador
    (`curtir`/`votar_faixa`)."""
    icone = QIcon()
    icone.addPixmap(icones.pixmap("coracao", cor_contorno, tamanho), QIcon.Normal, QIcon.Off)
    icone.addPixmap(icones.pixmap("coracao_cheio", styles.COR_LIKE, tamanho), QIcon.Normal, QIcon.On)
    return icone


def icone_nao_curtir(tamanho=16, cor_contorno=styles.COR_TEXTO_FRACO):
    """O MESMO polegar pra baixo em todo botão de não curtir (mesma ideia de
    `icone_curtir`): cor normal quando não votado, `COR_DISLIKE` quando
    marcado."""
    icone = QIcon()
    icone.addPixmap(icones.pixmap("dislike", cor_contorno, tamanho), QIcon.Normal, QIcon.Off)
    icone.addPixmap(icones.pixmap("dislike", styles.COR_DISLIKE, tamanho), QIcon.Normal, QIcon.On)
    return icone


def botoes_voto(voto, ao_votar):
    """Par curtir/não curtir, já marcado conforme `voto`."""
    curtir = botao_acao("coracao", "Curtir")
    curtir.setCheckable(True)
    curtir.setIcon(icone_curtir(16))
    curtir.setChecked(voto == "positivo")
    curtir.clicked.connect(lambda _=False: ao_votar("positivo"))
    nao_curtir = botao_acao("dislike", "Não curtir")
    nao_curtir.setCheckable(True)
    nao_curtir.setIcon(icone_nao_curtir(16))
    nao_curtir.setChecked(voto == "negativo")
    nao_curtir.clicked.connect(lambda _=False: ao_votar("negativo"))
    return curtir, nao_curtir


def texto_album(faixa):
    info = cache_mod.obter(faixa["titulo"], faixa["artista"]) or {}
    return info.get("album") or ("…" if cache_mod.precisa_consultar(faixa["titulo"], faixa["artista"]) else "-")


def texto_duracao(faixa):
    info = cache_mod.obter(faixa["titulo"], faixa["artista"]) or {}
    if info.get("duracao"):
        return cache_mod.formatar_duracao(info["duracao"])
    return "…" if cache_mod.precisa_consultar(faixa["titulo"], faixa["artista"]) else "-"


class InfoFaixasWorker(QThread):
    """Pede ao ECHO álbum/duração das faixas que o cache ainda não
    consultou, uma por vez, e grava no cache. Emite `info_pronta(titulo,
    artista)` a cada uma - a tela só atualiza as duas células daquela
    linha."""

    info_pronta = Signal(str, str)

    def __init__(self, faixas, parent=None):
        super().__init__(parent)
        self.falhou = False
        vistas = set()
        self._faixas = []
        for faixa in faixas:
            chave = (faixa["titulo"], faixa["artista"])
            if chave not in vistas and cache_mod.precisa_consultar(*chave):
                vistas.add(chave)
                self._faixas.append(chave)

    @property
    def tem_trabalho(self):
        return bool(self._faixas)

    def run(self):
        for titulo, artista in self._faixas:
            info = echo_client.obter_info_faixa(artista, titulo)
            if info is None:
                self.falhou = True
                return  # ECHO fora do ar: tenta de novo na próxima vez que a lista abrir
            cache_mod.registrar(titulo, artista, album=info.get("album"), duracao=info.get("duracao"), consultado=True)
            self.info_pronta.emit(titulo, artista)
