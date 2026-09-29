# -*- coding: utf-8 -*-
"""Efeitos de água do Modo Completo (2026-09-25) - derivados da identidade
do SIREN: "o canto da sereia se transformando em ondas sobre o mar" (README,
seção "Identidade visual").

`CamadaOndas`: camada transparente por cima da janela inteira que desenha
ondulações - a gota ao clicar e o pulso de sonar do ECHO. Só repinta o anel
de cada onda (região em forma de coroa circular), nunca a janela toda.

Removidos a pedido do usuário (2026-09-26): linha do tempo em onda, anéis do
"canto" ao começar uma faixa e rastro de ondulações atrás do mouse."""
import time
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QRegion
from PySide6.QtWidgets import QWidget

from siren.ui.full import styles


def _suavizar(progresso):
    """easeOutCubic - a onda nasce rápida e desacelera, como na água."""
    return 1 - (1 - progresso) ** 3


@dataclass
class _Onda:
    centro: QPointF
    raio_maximo: float
    duracao: float
    tipo: str
    inicio: float
    raio_anterior: float = 0.0

    def progresso(self, agora):
        return min(1.0, max(0.0, (agora - self.inicio) / self.duracao))

    def raio(self, agora):
        return self.raio_maximo * _suavizar(self.progresso(agora))


# tipo -> (meia espessura do anel em px, cor, alpha inicial)
_ESTILOS = {
    "gota": (1.6, QColor(170, 230, 255), 170),
    "sonar": (1.4, QColor(styles.COR_BIOLUM), 170),
}


class CamadaOndas(QWidget):
    """Desenha por cima de tudo, mas nunca recebe clique
    (`WA_TransparentForMouseEvents`)."""

    LIMITE_ONDAS = 40

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self._ondas = []

    def adicionar(self, centro, raio_maximo, duracao, tipo, atraso=0.0):
        if len(self._ondas) >= self.LIMITE_ONDAS:
            self._ondas.pop(0)
        self._ondas.append(_Onda(QPointF(centro), raio_maximo, duracao, tipo, time.monotonic() + atraso))

    @property
    def ativa(self):
        return bool(self._ondas)

    @staticmethod
    def _coroa(centro, raio_interno, raio_externo):
        externo = QRectF(centro.x() - raio_externo, centro.y() - raio_externo, raio_externo * 2, raio_externo * 2)
        regiao = QRegion(externo.toAlignedRect(), QRegion.Ellipse)
        if raio_interno > 4:
            interno = QRectF(centro.x() - raio_interno, centro.y() - raio_interno, raio_interno * 2, raio_interno * 2)
            regiao = regiao.subtracted(QRegion(interno.toAlignedRect(), QRegion.Ellipse))
        return regiao

    def avancar(self):
        """Chamado pelo relógio de efeitos da janela. Marca pra repintar só a
        coroa entre o raio do quadro anterior e o atual (mais a espessura)."""
        if not self._ondas:
            return
        agora = time.monotonic()
        regiao = QRegion()
        vivas = []
        for onda in self._ondas:
            if agora < onda.inicio:
                vivas.append(onda)
                continue
            meia_espessura = _ESTILOS[onda.tipo][0] + 3
            raio = onda.raio(agora)
            regiao = regiao.united(self._coroa(
                onda.centro, min(raio, onda.raio_anterior) - meia_espessura, max(raio, onda.raio_anterior) + meia_espessura,
            ))
            onda.raio_anterior = raio
            if onda.progresso(agora) < 1.0:
                vivas.append(onda)
        self._ondas = vivas
        if not regiao.isEmpty():
            self.update(regiao)

    def paintEvent(self, evento):
        if not self._ondas:
            return
        agora = time.monotonic()
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setBrush(Qt.NoBrush)
        for onda in self._ondas:
            if agora < onda.inicio:
                continue
            meia_espessura, cor, alpha_inicial = _ESTILOS[onda.tipo]
            progresso = onda.progresso(agora)
            raio = onda.raio(agora)
            alpha = int(alpha_inicial * (1 - progresso) ** 1.4)
            if alpha <= 0 or raio <= 0:
                continue
            traco = QColor(cor)
            traco.setAlpha(alpha)
            pintor.setPen(QPen(traco, meia_espessura * 0.75))
            pintor.drawEllipse(onda.centro, raio, raio)
