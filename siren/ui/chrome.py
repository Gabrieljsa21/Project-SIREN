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
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from siren.ui import win32_dwm
from siren.ui.full import icones


def configurar_janela_vidro_fosco(widget, cor_hex, alpha=130, acrylic_ativado=True, translucida=True):
    """Sem borda + cantos nativos + (se `translucida`) fundo translúcido com
    Acrylic. Devolve um dict dizendo o que realmente aplicou
    (`cantos_ok`/`acrylic_ok`) - quem chama decide se ainda precisa reforçar
    um fundo sólido (ex.: Windows mais antigo, sem suporte nenhum a isso).

    `translucida=False` (2026-09-25): janela opaca comum, só sem borda e com
    cantos arredondados. Medido no Modo Completo: numa janela translúcida o
    Windows reenvia a janela INTEIRA ao compositor a cada atualização (~8 ms
    fixos, por menor que seja a área), e os efeitos animados custavam ~83%
    de um núcleo contra ~16% com a janela opaca."""
    widget.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
    if not translucida:
        widget.setAttribute(Qt.WA_StyledBackground, True)
        widget.winId()
        cantos_ok = win32_dwm.aplicar_cantos_redondos(widget)
        win32_dwm.remover_cor_borda(widget)
        return {"cantos_ok": cantos_ok, "acrylic_ok": False}
    widget.setAttribute(Qt.WA_TranslucentBackground)
    # 🔥 Sem isso, a própria janela de topo (QWidget puro) nunca pinta a
    # regra genérica `QWidget { background: ... }` do QSS - qualquer pedaço
    # dela onde nenhum widget-filho pinta nada por cima (espaço vazio de
    # view/painel) fica com alpha 0 de verdade = clique-através (achado do
    # usuário, 2026-09-06: "ao clicar dentro de outro espaço da janela, o
    # clique passa direto"). 1ª tentativa (ligar isso com a regra genérica
    # em `rgba(0, 0, 0, 1)`) virou um retângulo preto sólido cobrindo o
    # Acrylic inteiro ("essas cores ficaram horríveis") - causa real, achada
    # comparando com o Project-ARGUS: `rgba()` no QSS usa alpha como FRAÇÃO
    # 0.0-1.0, não inteiro 0-255, então "1" = opacidade TOTAL, não "1 de
    # 255" (ver `full/styles.py`, valor corrigido pra `0.004`).
    widget.setAttribute(Qt.WA_StyledBackground, True)
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
        # o valor de styles.py nunca chegava a virar pixel de verdade, o
        # alpha real continuava 0 e o clique-através (ver comentário em
        # styles.py) persistia mesmo depois do fix de CSS.
        self.setAttribute(Qt.WA_StyledBackground, True)

        rotulo = QLabel(titulo)
        rotulo.setObjectName("barraTituloTexto")
        fonte = rotulo.font()
        fonte.setLetterSpacing(QFont.AbsoluteSpacing, 5)
        rotulo.setFont(fonte)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(2)
        layout.addWidget(rotulo)
        layout.addStretch()
        for nome_icone, nome_objeto, acao in (
            ("minimizar", "barraTituloBotao", janela.showMinimized),
            ("maximizar", "barraTituloBotao", self._alternar_maximizado),
            ("fechar", "barraTituloBotaoFechar", janela.close),
        ):
            botao = QPushButton()
            botao.setObjectName(nome_objeto)
            botao.setIcon(icones.icone(nome_icone, "#c3cbe0", 16, espessura=1.6))
            botao.setIconSize(QSize(15, 15))
            botao.setFixedSize(40, 30)
            botao.setCursor(Qt.PointingHandCursor)
            botao.clicked.connect(acao)
            layout.addWidget(botao)

    def _alternar_maximizado(self):
        if self._janela.isMaximized():
            self._janela.showNormal()
        else:
            self._janela.showMaximized()

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
        self._alternar_maximizado()
