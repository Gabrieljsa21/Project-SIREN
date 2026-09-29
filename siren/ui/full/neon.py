# -*- coding: utf-8 -*-
"""Brilho bioluminescente que acende só quando o mouse passa por cima.

Um `QGraphicsDropShadowEffect` sem deslocamento vira um halo em volta do
widget. Fica desligado em repouso (custo zero de pintura), acende no hover
e, enquanto o mouse continua em cima, pulsa devagar como plâncton luminoso
- ciano-turquesa em vez do azul neon da 1ª versão (2026-09-25), pra
conversar com o tema de mar do SIREN."""
import math
import time

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect

from siren.ui.full import styles

DURACAO_ACENDER_MS = 180
PERIODO_PULSO_S = 2.2
# Pulso a ~12 fps em vez dos 60 do QPropertyAnimation: cada passo repinta o
# widget, e numa janela translúcida cada repintura custa ~8 ms fixos
# (medido em 2026-09-25) - 60 fps contínuos com o mouse parado num cartão
# ocupariam meio núcleo.
INTERVALO_PULSO_MS = 85


class _FiltroNeon(QObject):
    def __init__(self, widget, cor, raio):
        super().__init__(widget)
        self._widget = widget
        self._raio = raio
        self._efeito = QGraphicsDropShadowEffect(widget)
        self._efeito.setOffset(0, 0)
        self._efeito.setColor(cor)
        self._efeito.setBlurRadius(0)
        self._efeito.setEnabled(False)
        widget.setGraphicsEffect(self._efeito)

        self._acender = QPropertyAnimation(self._efeito, b"blurRadius", self)
        self._acender.setDuration(DURACAO_ACENDER_MS)
        self._acender.setEasingCurve(QEasingCurve.OutCubic)
        self._acender.finished.connect(self._ao_terminar_transicao)

        self._pulso = QTimer(self)
        self._pulso.setInterval(INTERVALO_PULSO_MS)
        self._pulso.timeout.connect(self._pulsar)
        self._inicio_pulso = 0.0
        widget.installEventFilter(self)

    def eventFilter(self, objeto, evento):
        if evento.type() == QEvent.Enter and self._widget.isEnabled():
            self._animar_para(self._raio)
        elif evento.type() in (QEvent.Leave, QEvent.Hide):
            self._animar_para(0)
        return False

    def _animar_para(self, raio):
        self._pulso.stop()
        self._acender.stop()
        if raio:
            self._efeito.setEnabled(True)
        self._acender.setStartValue(self._efeito.blurRadius())
        self._acender.setEndValue(raio)
        self._acender.start()

    def _ao_terminar_transicao(self):
        if self._efeito.blurRadius() == 0:
            # Desliga de vez em repouso: efeito ativo com raio 0 ainda
            # obrigaria o Qt a pintar o widget num buffer à parte.
            self._efeito.setEnabled(False)
        elif self._widget.underMouse():
            self._inicio_pulso = time.monotonic()
            self._pulso.start()

    def _pulsar(self):
        fase = (time.monotonic() - self._inicio_pulso) / PERIODO_PULSO_S * math.pi * 2
        self._efeito.setBlurRadius(self._raio * (0.775 + 0.225 * math.cos(fase)))


def aplicar(widget, cor=styles.COR_BIOLUM, raio=30, alpha=190):
    """Liga o brilho de hover em `widget`. Um widget só aceita UM
    `QGraphicsEffect` - não usar em quem já tem outro efeito."""
    cor_qt = QColor(cor)
    cor_qt.setAlpha(alpha)
    return _FiltroNeon(widget, cor_qt, raio)
