# -*- coding: utf-8 -*-
"""Chrome de janela do Modo Completo do SIREN - sem barra de título nativa,
cantos arredondados + Acrylic (ver win32_dwm.py), com uma barra de título
própria (arrastar pra mover, minimizar, fechar, maximizar no duplo clique).
Mesmo padrão visual do Argus, adaptado: SIREN é uma janela de app comum
(`Qt.Window`), não um widget flutuante sempre no topo (`Qt.Tool` +
`WindowStaysOnTopHint`) como o Argus.

O Modo Leve NUNCA usa nada deste módulo - continua com a janela padrão do
Qt (barra de título nativa, sem Acrylic), exatamente pra pesar o mínimo
possível."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from siren.ui import win32_dwm

LIMIAR_ARRASTAR_PIXELS = 3


def configurar_janela_vidro_fosco(widget, cor_hex, alpha=130, acrylic_ativado=True):
    """Sem borda + translúcida + cantos nativos + Acrylic. Devolve um dict
    dizendo o que realmente aplicou (`cantos_ok`/`acrylic_ok`) - quem chama
    decide se ainda precisa reforçar um fundo sólido (ex.: Windows mais
    antigo, sem suporte nenhum a isso)."""
    widget.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
    widget.setAttribute(Qt.WA_TranslucentBackground)
    widget.winId()
    cantos_ok = win32_dwm.aplicar_cantos_redondos(widget)
    win32_dwm.remover_cor_borda(widget)
    acrylic_ok = acrylic_ativado and win32_dwm.aplicar_acrylic(widget, cor_hex, alpha)
    return {"cantos_ok": cantos_ok, "acrylic_ok": acrylic_ok}


class BarraTitulo(QWidget):
    """`janela`: a janela de topo que esta barra controla (arrastar,
    minimizar, fechar, maximizar) - passada explicitamente em vez de usar
    `self.window()`, pra não depender de em que hierarquia de widgets essa
    barra acaba sendo colocada."""

    def __init__(self, janela, titulo, parent=None):
        super().__init__(parent)
        self._janela = janela
        self._pos_pressionada = None
        self.setFixedHeight(38)
        self.setObjectName("barraTitulo")

        rotulo = QLabel(titulo)
        rotulo.setObjectName("barraTituloTexto")

        botao_min = QPushButton("—")
        botao_min.setObjectName("barraTituloBotao")
        botao_min.setFixedSize(30, 26)
        botao_min.setCursor(Qt.PointingHandCursor)
        botao_min.clicked.connect(janela.showMinimized)

        botao_fechar = QPushButton("✕")
        botao_fechar.setObjectName("barraTituloBotaoFechar")
        botao_fechar.setFixedSize(30, 26)
        botao_fechar.setCursor(Qt.PointingHandCursor)
        botao_fechar.clicked.connect(janela.close)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.addWidget(rotulo)
        layout.addStretch()
        layout.addWidget(botao_min)
        layout.addWidget(botao_fechar)

    def mousePressEvent(self, evento):
        self._pos_pressionada = evento.globalPosition().toPoint()

    def mouseMoveEvent(self, evento):
        if self._pos_pressionada is None:
            return
        atual = evento.globalPosition().toPoint()
        delta = atual - self._pos_pressionada
        if delta.manhattanLength() > LIMIAR_ARRASTAR_PIXELS:
            self._janela.move(self._janela.pos() + delta)
            self._pos_pressionada = atual

    def mouseReleaseEvent(self, evento):
        self._pos_pressionada = None

    def mouseDoubleClickEvent(self, evento):
        if self._janela.isMaximized():
            self._janela.showNormal()
        else:
            self._janela.showMaximized()
