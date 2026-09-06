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
        self.setFixedHeight(38)
        self.setObjectName("barraTitulo")
        # 🔥 QWidget puro NÃO pinta "background" do QSS sozinho (diferente
        # de QFrame/QPushButton/etc, que já são "style aware") - sem isso,
        # o `rgba(0, 0, 0, 1)` de styles.py nunca chegava a virar pixel de
        # verdade, o alpha real continuava 0 e o clique-através (ver
        # comentário em styles.py) persistia mesmo depois do fix de CSS
        # (achado do usuário: "continua com erro").
        self.setAttribute(Qt.WA_StyledBackground, True)

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
        """Arrastar via `startSystemMove()` (Qt 5.15+/6, nativo do SO) - em
        vez de calcular delta de posição à mão (`janela.move(...)` a cada
        `mouseMoveEvent`). Achado real (2026-09-06, usuário: "não estou
        conseguindo mover as janelas, quando clico pra arrastá-las, elas se
        minimizam") - mover a janela chamando `.move()` repetidamente
        durante o arrasto, numa janela sem borda/translúcida, deixava o
        DWM do Windows confuso sobre o estado dela. Delegar o arrasto
        inteiro pro sistema operacional evita essa classe de bug inteira -
        mesma técnica usada por apps reais com título próprio (VS Code,
        Windows Terminal)."""
        if evento.button() == Qt.LeftButton:
            handle = self._janela.windowHandle()
            if handle is not None:
                handle.startSystemMove()
            evento.accept()

    def mouseDoubleClickEvent(self, evento):
        if self._janela.isMaximized():
            self._janela.showNormal()
        else:
            self._janela.showMaximized()
