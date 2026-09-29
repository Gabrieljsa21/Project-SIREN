# -*- coding: utf-8 -*-
"""Arte procedural do Modo Completo - capas de playlist/faixa e a paisagem
noturna do fundo da Home, desenhadas com QPainter.

O SIREN não tem capa de álbum pra playlist (só a faixa tocando traz
thumbnail do YouTube), e embutir imagens prontas pesaria o repositório sem
necessidade. Cada tema tem um motivo fixo (coração, lua, montanhas) e o resto
usa um gradiente derivado do nome, então a mesma playlist sempre ganha a
mesma capa."""
import math
import random
import zlib
from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF,
    QRadialGradient,
)

from siren.core import playlists as playlists_mod

TEMA_POR_PLAYLIST = {
    playlists_mod.NOME_PLAYLIST_CURTIDAS: "curtidas",
    playlists_mod.NOME_PLAYLIST_NAO_CURTIDAS: "nao_curtidas",
}


def tema_da_playlist(nome):
    return TEMA_POR_PLAYLIST.get(nome, "generico")


def _semente(texto):
    return zlib.crc32(texto.encode("utf-8"))


def _gradiente_vertical(pintor, largura, altura, paradas):
    gradiente = QLinearGradient(0, 0, largura * 0.35, altura)
    for posicao, cor in paradas:
        gradiente.setColorAt(posicao, QColor(cor))
    pintor.fillRect(QRectF(0, 0, largura, altura), gradiente)


def _brilho(pintor, x, y, raio, cor, alpha):
    radial = QRadialGradient(QPointF(x, y), raio)
    centro = QColor(cor)
    centro.setAlpha(alpha)
    borda = QColor(cor)
    borda.setAlpha(0)
    radial.setColorAt(0, centro)
    radial.setColorAt(1, borda)
    pintor.setPen(Qt.NoPen)
    pintor.setBrush(radial)
    pintor.drawEllipse(QPointF(x, y), raio, raio)


def _estrelas(pintor, largura, altura, gerador, quantidade, teto=0.7):
    pintor.setPen(Qt.NoPen)
    for _ in range(quantidade):
        cor = QColor(255, 255, 255, gerador.randint(60, 220))
        pintor.setBrush(cor)
        raio = gerador.uniform(0.4, 1.3) * max(1.0, largura / 220)
        pintor.drawEllipse(QPointF(gerador.uniform(0, largura), gerador.uniform(0, altura * teto)), raio, raio)


def _cordilheira(pintor, largura, altura, base, amplitude, cor, gerador, picos=7):
    pontos = [QPointF(0, altura)]
    passo = largura / picos
    for indice in range(picos + 1):
        x = indice * passo + gerador.uniform(-passo * 0.25, passo * 0.25)
        y = base - gerador.uniform(0.3, 1.0) * amplitude
        pontos.append(QPointF(x, y))
        pontos.append(QPointF(x + passo / 2, base - gerador.uniform(0.0, 0.35) * amplitude))
    pontos.append(QPointF(largura, altura))
    pintor.setPen(Qt.NoPen)
    pintor.setBrush(QColor(cor))
    pintor.drawPolygon(QPolygonF(pontos))


def _arvores(pintor, largura, altura, cor, gerador, quantidade=26):
    pintor.setPen(Qt.NoPen)
    pintor.setBrush(QColor(cor))
    for _ in range(quantidade):
        x = gerador.uniform(0, largura)
        alto = gerador.uniform(0.12, 0.28) * altura
        meia = alto * 0.22
        pintor.drawPolygon(QPolygonF([
            QPointF(x, altura - alto - altura * 0.02), QPointF(x - meia, altura), QPointF(x + meia, altura),
        ]))


def _coracao(largura, altura, cx, cy, tamanho):
    caminho = QPainterPath()
    caminho.moveTo(cx, cy + tamanho * 0.9)
    caminho.cubicTo(cx - tamanho * 1.4, cy, cx - tamanho * 0.9, cy - tamanho * 1.0, cx, cy - tamanho * 0.35)
    caminho.cubicTo(cx + tamanho * 0.9, cy - tamanho * 1.0, cx + tamanho * 1.4, cy, cx, cy + tamanho * 0.9)
    return caminho


def _tema_curtidas(pintor, largura, altura, gerador):
    _gradiente_vertical(pintor, largura, altura, [(0, "#2b0a3f"), (0.55, "#5a1650"), (1, "#16061f")])
    cx, cy, tamanho = largura * 0.34, altura * 0.42, min(largura, altura) * 0.32
    _brilho(pintor, cx, cy, tamanho * 2.6, "#ff4fa3", 150)
    gradiente = QLinearGradient(cx - tamanho, cy - tamanho, cx + tamanho, cy + tamanho)
    gradiente.setColorAt(0, QColor("#ff9ad0"))
    gradiente.setColorAt(0.5, QColor("#ff3d8b"))
    gradiente.setColorAt(1, QColor("#b3125e"))
    pintor.setBrush(gradiente)
    pintor.setPen(Qt.NoPen)
    pintor.drawPath(_coracao(largura, altura, cx, cy, tamanho))
    _estrelas(pintor, largura, altura, gerador, 22)
    _arvores(pintor, largura, altura, "#12041b", gerador)


def _tema_nao_curtidas(pintor, largura, altura, gerador):
    _gradiente_vertical(pintor, largura, altura, [(0, "#070d22"), (0.6, "#16244a"), (1, "#0a1128")])
    _estrelas(pintor, largura, altura, gerador, 60, teto=0.9)
    cx, cy, raio = largura * 0.4, altura * 0.36, min(largura, altura) * 0.2
    _brilho(pintor, cx, cy, raio * 3.2, "#b9c8ff", 90)
    lua = QPainterPath()
    lua.addEllipse(QPointF(cx, cy), raio, raio)
    sombra = QPainterPath()
    sombra.addEllipse(QPointF(cx + raio * 0.55, cy - raio * 0.25), raio * 0.92, raio * 0.92)
    pintor.setBrush(QColor("#f3e6c4"))
    pintor.drawPath(lua.subtracted(sombra))
    for indice in range(3):
        _brilho(pintor, largura * (0.2 + indice * 0.32), altura * (0.8 + gerador.uniform(-0.05, 0.05)),
                largura * 0.28, "#27365f", 200)


def _tema_descobertas(pintor, largura, altura, gerador):
    _gradiente_vertical(pintor, largura, altura, [(0, "#4c6fb8"), (0.5, "#223f7c"), (1, "#0b1733")])
    _brilho(pintor, largura * 0.6, altura * 0.15, largura * 0.6, "#a8c4ff", 90)
    _estrelas(pintor, largura, altura, gerador, 14, teto=0.35)
    _cordilheira(pintor, largura, altura, altura * 0.62, altura * 0.42, "#6f8fcf", gerador, picos=5)
    _cordilheira(pintor, largura, altura, altura * 0.78, altura * 0.3, "#2a4378", gerador, picos=6)
    _cordilheira(pintor, largura, altura, altura * 0.95, altura * 0.22, "#101d3d", gerador, picos=8)


def _tema_generico(pintor, largura, altura, gerador):
    matiz = gerador.randint(190, 290)
    claro = QColor.fromHsv(matiz, 150, 200)
    escuro = QColor.fromHsv((matiz + 25) % 360, 200, 50)
    _gradiente_vertical(pintor, largura, altura, [(0, claro.name()), (1, escuro.name())])
    _brilho(pintor, largura * gerador.uniform(0.2, 0.8), altura * 0.3, largura * 0.55, "#ffffff", 50)
    pintor.setBrush(Qt.NoBrush)
    for indice in range(5):
        cor = QColor(255, 255, 255, 40 - indice * 6)
        pintor.setPen(cor)
        caminho = QPainterPath()
        base = altura * (0.55 + indice * 0.08)
        caminho.moveTo(0, base)
        for passo in range(1, 21):
            x = largura * passo / 20
            caminho.lineTo(x, base + math.sin(passo / 3 + indice) * altura * 0.05)
        pintor.drawPath(caminho)


_TEMAS = {
    "curtidas": _tema_curtidas,
    "nao_curtidas": _tema_nao_curtidas,
    "descobertas": _tema_descobertas,
    "generico": _tema_generico,
}


@lru_cache(maxsize=128)
def capa(tema, largura, altura, semente="", escala=2.0):
    """Pixmap `largura`x`altura` (lógicos) do tema pedido, sem cantos
    arredondados - quem desenha recorta com o raio que precisar."""
    largura_real, altura_real = int(largura * escala), int(altura * escala)
    imagem = QPixmap(largura_real, altura_real)
    imagem.fill(QColor("#0b1430"))
    pintor = QPainter(imagem)
    pintor.setRenderHint(QPainter.Antialiasing)
    gerador = random.Random(_semente(f"{tema}:{semente}"))
    _TEMAS.get(tema, _tema_generico)(pintor, largura_real, altura_real, gerador)
    pintor.end()
    imagem.setDevicePixelRatio(escala)
    return imagem


def capa_arredondada(tema, lado, raio, semente=""):
    """Versão quadrada já recortada - usada nas miniaturas da biblioteca."""
    base = capa(tema, lado, lado, semente)
    imagem = QPixmap(base.size())
    imagem.fill(Qt.transparent)
    imagem.setDevicePixelRatio(base.devicePixelRatio())
    pintor = QPainter(imagem)
    pintor.setRenderHint(QPainter.Antialiasing)
    caminho = QPainterPath()
    caminho.addRoundedRect(QRectF(0, 0, lado, lado), raio, raio)
    pintor.setClipPath(caminho)
    pintor.drawPixmap(0, 0, base)
    pintor.end()
    return imagem


def recortar_quadrado_arredondado(origem, lado, raio):
    """Thumbnail real (YouTube, geralmente 16:9) -> quadrado central
    arredondado, no mesmo formato das capas procedurais."""
    escala = 2.0
    menor = min(origem.width(), origem.height())
    quadrado = origem.copy((origem.width() - menor) // 2, (origem.height() - menor) // 2, menor, menor)
    quadrado = quadrado.scaled(int(lado * escala), int(lado * escala), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    imagem = QPixmap(quadrado.size())
    imagem.fill(Qt.transparent)
    pintor = QPainter(imagem)
    pintor.setRenderHint(QPainter.Antialiasing)
    caminho = QPainterPath()
    caminho.addRoundedRect(QRectF(0, 0, imagem.width(), imagem.height()), raio * escala, raio * escala)
    pintor.setClipPath(caminho)
    pintor.drawPixmap(0, 0, quadrado)
    pintor.end()
    imagem.setDevicePixelRatio(escala)
    return imagem


HORIZONTE_PAISAGEM = 0.5  # fração da altura da faixa de paisagem


@lru_cache(maxsize=8)
def _paisagem_estatica(largura, altura, escala=2.0):
    """Colinas com luzes de vila + mar calmo embaixo, desenhados UMA vez por
    tamanho (a Home repinta essa faixa a cada frame do reflexo da lua)."""
    imagem = QPixmap(int(largura * escala), int(altura * escala))
    imagem.fill(Qt.transparent)
    imagem.setDevicePixelRatio(escala)
    pintor = QPainter(imagem)
    pintor.setRenderHint(QPainter.Antialiasing)
    gerador = random.Random(7)
    horizonte = altura * HORIZONTE_PAISAGEM

    pontos = [QPointF(0, horizonte)]
    for indice in range(15):
        x = largura * indice / 14
        pico = math.sin(indice * 0.8) * 0.5 + 0.5
        pontos.append(QPointF(x, horizonte - altura * (0.04 + 0.12 * pico) - gerador.uniform(0, altura * 0.03)))
    pontos.append(QPointF(largura, horizonte))
    pintor.setPen(Qt.NoPen)
    pintor.setBrush(QColor(12, 20, 40, 175))
    pintor.drawPolygon(QPolygonF(pontos))

    mar = QLinearGradient(0, horizonte, 0, altura)
    mar.setColorAt(0, QColor(18, 34, 66, 170))
    mar.setColorAt(1, QColor(6, 12, 28, 210))
    pintor.fillRect(QRectF(0, horizonte, largura, altura - horizonte), mar)
    pintor.setPen(QPen(QColor(120, 160, 230, 22), 1))
    for _ in range(40):
        y = gerador.uniform(horizonte + 4, altura - 4)
        x = gerador.uniform(0, largura)
        comprimento = gerador.uniform(20, 90) * (0.5 + (y - horizonte) / altura)
        pintor.drawLine(QPointF(x, y), QPointF(x + comprimento, y))

    pintor.setPen(Qt.NoPen)
    for _ in range(60):
        x = gerador.uniform(largura * 0.05, largura * 0.62)
        y = gerador.uniform(horizonte - altura * 0.07, horizonte - 2)
        alpha = gerador.randint(90, 200)
        raio = gerador.uniform(0.6, 1.4)
        pintor.setBrush(QColor(255, 196, 110, alpha))
        pintor.drawEllipse(QPointF(x, y), raio, raio)
        # reflexo borrado de cada luz na água
        pintor.setBrush(QColor(255, 196, 110, alpha // 5))
        pintor.drawRect(QRectF(x - raio * 0.6, 2 * horizonte - y, raio * 1.2, raio * 5))
    pintor.end()
    return imagem


def pintar_paisagem(pintor, retangulo):
    """Colinas + mar no rodapé da Home, bem sutil - dá profundidade sem
    competir com os cartões por cima."""
    largura, altura = int(retangulo.width()), int(retangulo.height())
    if largura <= 0 or altura <= 0:
        return
    pintor.drawPixmap(retangulo.topLeft(), _paisagem_estatica(largura, altura))


def retangulo_reflexo_lua(retangulo, x_lua):
    horizonte = retangulo.top() + retangulo.height() * HORIZONTE_PAISAGEM
    return QRectF(x_lua - 90, horizonte, 180, retangulo.bottom() - horizonte).toAlignedRect()


def pintar_reflexo_lua(pintor, retangulo, x_lua, instante, intensidade=1.0):
    """Coluna de traços horizontais trêmulos no mar, embaixo da lua - cada
    traço oscila de largura e posição num ritmo próprio, como luar na água."""
    horizonte = retangulo.top() + retangulo.height() * HORIZONTE_PAISAGEM
    fundo = retangulo.bottom()
    pintor.save()
    pintor.setRenderHint(QPainter.Antialiasing)
    total = 13
    y = horizonte + 3
    for indice in range(total):
        if y > fundo - 2:
            break
        meia_largura = (8 + indice * 4.5) * (0.55 + 0.45 * math.sin(instante * 1.7 + indice * 1.9))
        desvio = math.sin(instante * 1.1 + indice * 0.8) * (2 + indice * 0.5)
        alpha = int(165 * intensidade * (1 - indice / total) ** 1.2)
        pintor.setPen(QPen(QColor(225, 235, 255, alpha), 1.7, Qt.SolidLine, Qt.RoundCap))
        pintor.drawLine(QPointF(x_lua + desvio - meia_largura, y), QPointF(x_lua + desvio + meia_largura, y))
        y += 3.5 + indice * 1.1
    pintor.restore()
