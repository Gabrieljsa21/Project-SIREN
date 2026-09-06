# -*- coding: utf-8 -*-
"""Vidro fosco nativo do Windows (Acrylic) pro Modo Completo do SIREN -
pedido do usuário (2026-09-06): "também gosto da arte meio vidro fosco,
igual Argus". Mesmo `ctypes` puro já validado em `Project-ARGUS/argus/core/
win32_dwm.py` (funciona igual em cima do PySide6, sem dependência nova) -
só cantos arredondados + Acrylic, sem a função de Mica: o Argus já testou
Mica visualmente e o usuário rejeitou ("achei feio... prefiro cores
escuras"), preferência que se aplica igual aqui.

O Modo Leve NUNCA chama nada deste módulo de propósito - Acrylic tem custo
real de composição (por menor que seja), e o Modo Leve existe justamente
pra pesar o mínimo possível rodando ao lado de jogo/programa pesado."""
import ctypes
import sys

DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_BORDER_COLOR = 34
DWMWA_COLOR_NONE = 0xFFFFFFFE
DWMWCP_ROUND = 2

WCA_ACCENT_POLICY = 19
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4


class _ACCENTPOLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_uint),
    ]


class _WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.POINTER(ctypes.c_int)),
        ("SizeOfData", ctypes.c_size_t),
    ]


def aplicar_cantos_redondos(widget) -> bool:
    """Cantos arredondados nativos (Windows 11, build 22000+) - devolve
    `False` em qualquer outra situação (Windows mais antigo, não-Windows,
    erro), sem levantar exceção nenhuma."""
    if sys.platform != "win32":
        return False
    try:
        if sys.getwindowsversion().build < 22000:
            return False
        hwnd = int(widget.winId())
        preferencia = ctypes.c_int(DWMWCP_ROUND)
        resultado = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(preferencia), ctypes.sizeof(preferencia)
        )
        return resultado == 0
    except Exception:
        return False


def remover_cor_borda(widget) -> bool:
    """Sem isso, o Windows desenharia a cor de accent do sistema ao redor da
    janela - o SIREN já pinta a própria borda sutil, a nativa por cima
    ficaria destoante da identidade índigo/dourada."""
    if sys.platform != "win32":
        return False
    try:
        hwnd = int(widget.winId())
        cor = ctypes.c_int(DWMWA_COLOR_NONE)
        resultado = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_BORDER_COLOR, ctypes.byref(cor), ctypes.sizeof(cor)
        )
        return resultado == 0
    except Exception:
        return False


def _cor_para_gradiente(cor_hex: str, alpha: int) -> int:
    """"#RRGGBB" + alpha (0-255) -> inteiro AABBGGRR que a struct
    ACCENTPOLICY espera."""
    cor_hex = cor_hex.lstrip("#")
    r = int(cor_hex[0:2], 16)
    g = int(cor_hex[2:4], 16)
    b = int(cor_hex[4:6], 16)
    return (alpha << 24) | (b << 16) | (g << 8) | r


def aplicar_acrylic(widget, cor_hex: str = "#101a2c", alpha: int = 130) -> bool:
    """Acrylic (API não documentada `SetWindowCompositionAttribute`,
    Windows 10+) - `cor_hex` tinge o blur com a cor de fundo do SIREN
    (índigo profundo por padrão) em vez de mostrar o material cru do
    sistema. `alpha` mais alto = mais sólido/escuro, mais baixo = mais
    transparente (blur aparece mais)."""
    if sys.platform != "win32":
        return False
    try:
        hwnd = int(widget.winId())
        accent = _ACCENTPOLICY()
        accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
        accent.AccentFlags = 0
        accent.GradientColor = _cor_para_gradiente(cor_hex, alpha)
        accent.AnimationId = 0

        data = _WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.SizeOfData = ctypes.sizeof(accent)
        data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.POINTER(ctypes.c_int))

        resultado = ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
        return resultado != 0  # API de user32/BOOL - 0 é FALHA aqui, oposto do HRESULT do dwmapi acima
    except Exception:
        return False
