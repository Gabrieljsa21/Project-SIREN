# -*- coding: utf-8 -*-
"""Ícones vetoriais (SVG em traço, estilo "line icon") do Modo Completo.

Substituem os emojis/caracteres Unicode usados antes (⌂, 🔍, ⏮...), que
dependiam da fonte do sistema e saíam com tamanho/cor inconsistentes. Cada
ícone é um trecho SVG 24x24 renderizado sob demanda na cor pedida - sem
arquivo de asset nenhum, então trocar a paleta em `styles.py` não exige
redesenhar nada."""
from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Conteúdo interno de cada SVG (viewBox 0 0 24 24). `fill` explícito só onde
# o ícone é sólido (play/pause/anterior/próximo/coração cheio).
_CAMINHOS = {
    "inicio": '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/>',
    "descoberta": '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/>',
    "historico": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "historico_seta": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/>',
    "mais": '<path d="M12 5v14M5 12h14"/>',
    "baixar": '<path d="M12 4v11"/><path d="m7 10 5 5 5-5"/><path d="M5 20h14"/>',
    "lua": '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
    "busca": '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
    "coracao": '<path d="M12 20s-7-4.4-9-9.1C1.7 7.6 4 4.5 7.3 4.5c2 0 3.4 1.1 4.7 2.8 1.3-1.7 2.7-2.8 4.7-2.8 3.3 0 5.6 3.1 4.3 6.4C19 15.6 12 20 12 20z"/>',
    "coracao_cheio": '<path fill="currentColor" d="M12 20s-7-4.4-9-9.1C1.7 7.6 4 4.5 7.3 4.5c2 0 3.4 1.1 4.7 2.8 1.3-1.7 2.7-2.8 4.7-2.8 3.3 0 5.6 3.1 4.3 6.4C19 15.6 12 20 12 20z"/>',
    "coracao_partido": '<path d="M12 20s-7-4.4-9-9.1C1.7 7.6 4 4.5 7.3 4.5c2 0 3.4 1.1 4.7 2.8 1.3-1.7 2.7-2.8 4.7-2.8 3.3 0 5.6 3.1 4.3 6.4C19 15.6 12 20 12 20z"/><path d="m12 7.3-1.5 3.7 3 1.5-1.5 4"/>',
    "proibido":'<circle cx="12" cy="12" r="9"/><path d="m5.6 5.6 12.8 12.8"/>',
    "nota": '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
    "play": '<path fill="currentColor" stroke="none" d="M8 5.5v13a1 1 0 0 0 1.5.9l10.2-6.5a1 1 0 0 0 0-1.8L9.5 4.6A1 1 0 0 0 8 5.5z"/>',
    "pause": '<rect fill="currentColor" stroke="none" x="6" y="5" width="4" height="14" rx="1.2"/><rect fill="currentColor" stroke="none" x="14" y="5" width="4" height="14" rx="1.2"/>',
    "anterior": '<path fill="currentColor" stroke="none" d="M18 6.2v11.6a1 1 0 0 1-1.6.8L8.6 12.8a1 1 0 0 1 0-1.6l7.8-5.8a1 1 0 0 1 1.6.8z"/><rect fill="currentColor" stroke="none" x="5" y="5" width="2.6" height="14" rx="1"/>',
    "proximo": '<path fill="currentColor" stroke="none" d="M6 6.2v11.6a1 1 0 0 0 1.6.8l7.8-5.8a1 1 0 0 0 0-1.6L7.6 5.4A1 1 0 0 0 6 6.2z"/><rect fill="currentColor" stroke="none" x="16.4" y="5" width="2.6" height="14" rx="1"/>',
    "dislike": '<path d="M17 14V3"/><path d="M9 18.1 10 14H4.2a2 2 0 0 1-1.9-2.5l2.3-8A2 2 0 0 1 6.5 2H20a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1h-2.8a2 2 0 0 0-1.8 1.1L12 22a3 3 0 0 1-3-3.9z"/>',
    "letras": '<path d="M12 3a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3z"/><path d="M19 11a7 7 0 0 1-14 0"/><path d="M12 18v3"/>',
    "fila": '<path d="M4 6h16M4 12h10M4 18h10"/><path d="m17 15 4 3-4 3z" fill="currentColor"/>',
    "volume": '<path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/><path d="M19 6a8.5 8.5 0 0 1 0 12"/>',
    "brilho": '<path fill="currentColor" stroke="none" d="M12 2.5c.5 4.6 2.9 7 7.5 7.5-4.6.5-7 2.9-7.5 7.5-.5-4.6-2.9-7-7.5-7.5 4.6-.5 7-2.9 7.5-7.5z"/><path fill="currentColor" stroke="none" d="M19 15c.2 2 1.2 3 3 3.2-1.8.2-2.8 1.2-3 3.2-.2-2-1.2-3-3-3.2 1.8-.2 2.8-1.2 3-3.2z"/>',
    "aleatorio": '<path d="M16 3h5v5"/><path d="M4 20 21 3"/><path d="M21 16v5h-5"/><path d="m15 15 6 6"/><path d="m4 4 5 5"/>',
    "repetir": '<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>',
    "repetir_um": '<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/><path d="M11 10h1v4"/>',
    "pessoa": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "alca": '<circle fill="currentColor" stroke="none" cx="8" cy="10" r="1.3"/><circle fill="currentColor" stroke="none" cx="12" cy="10" r="1.3"/><circle fill="currentColor" stroke="none" cx="16" cy="10" r="1.3"/><circle fill="currentColor" stroke="none" cx="8" cy="14" r="1.3"/><circle fill="currentColor" stroke="none" cx="12" cy="14" r="1.3"/><circle fill="currentColor" stroke="none" cx="16" cy="14" r="1.3"/>',
    "expandir": '<path d="M15 3h6v6"/><path d="M9 21H3v-6"/><path d="M21 3l-7 7"/><path d="M3 21l7-7"/>',
    "mais_circulo": '<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',
    "check_circulo": '<circle fill="currentColor" stroke="none" cx="12" cy="12" r="10"/><path stroke="#0b1430" stroke-width="2.4" d="m7.5 12.5 3 3 6-6.5"/>',
    "volume_mudo": '<path d="M4 9h4l5-4v14l-5-4H4z"/><path d="m17 9 5 6M22 9l-5 6"/>',
    "seta_cima": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "seta_baixo": '<path d="M12 5v14M6 13l6 6 6-6"/>',
    "seta_direita": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "minimizar": '<path d="M5 12h14"/>',
    "maximizar": '<rect x="5" y="5" width="14" height="14" rx="1.5"/>',
    "fechar": '<path d="M6 6l12 12M18 6 6 18"/>',
    "equalizador": '<path d="M4 10v4M8 7v10M12 4v16M16 8v8M20 11v2"/>',
}


def _svg(nome, cor, espessura):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{cor}" color="{cor}" stroke-width="{espessura}" '
        'stroke-linecap="round" stroke-linejoin="round">'
        f'{_CAMINHOS[nome]}</svg>'
    ).replace("currentColor", cor)


@lru_cache(maxsize=256)
def pixmap(nome, cor="#eef2ff", tamanho=20, espessura=1.9, escala=2.0):
    """Renderiza em `tamanho * escala` pixels e marca o devicePixelRatio -
    fica nítido tanto em 100% quanto em 200% de escala do Windows."""
    lado = int(tamanho * escala)
    imagem = QPixmap(lado, lado)
    imagem.fill(Qt.transparent)
    renderizador = QSvgRenderer(QByteArray(_svg(nome, cor, espessura).encode("utf-8")))
    pintor = QPainter(imagem)
    pintor.setRenderHint(QPainter.Antialiasing)
    renderizador.render(pintor, QRectF(0, 0, lado, lado))
    pintor.end()
    imagem.setDevicePixelRatio(escala)
    return imagem


def icone(nome, cor="#eef2ff", tamanho=20, cor_ativa=None, espessura=1.9):
    """`cor_ativa`: cor do estado marcado (`setCheckable`) - ex.: aba ativa
    da sidebar ou botão de curtir aceso."""
    resultado = QIcon()
    resultado.addPixmap(pixmap(nome, cor, tamanho, espessura), QIcon.Normal, QIcon.Off)
    if cor_ativa:
        resultado.addPixmap(pixmap(nome, cor_ativa, tamanho, espessura), QIcon.Normal, QIcon.On)
    return resultado
