# -*- coding: utf-8 -*-
"""QSS do Modo Completo - paleta índigo/dourado igual à simulação publicada
como artifact ("SIREN"), adaptada pra vidro fosco: painéis usam fundo
translúcido (rgba com alpha baixo) pra deixar o Acrylic aparecer por trás,
em vez de cor sólida como uma janela comum."""

COR_FUNDO = "#101a2c"
COR_TEXTO = "#eef1fb"
COR_TEXTO_FRACO = "#aab3d6"
COR_ACCENT = "#e7b95d"
COR_ACCENT_ESCURO = "#c99b45"
COR_ACCENT_TINTA = "#3a2a0c"
COR_BORDA = "rgba(255, 255, 255, 28)"
COR_PAINEL = "rgba(20, 30, 55, 150)"
COR_PAINEL_2 = "rgba(38, 54, 94, 170)"
COR_LIKE = "#ea6b86"
COR_DISLIKE = "#7784ab"

# 🔥 Nenhum widget aqui pode usar `background: transparent` (alpha 0 de
# verdade) - achado real (2026-09-06, usuário: "é como se o clique passasse
# por ele e clicasse no que está atrás"): numa janela translúcida por pixel
# (`WA_TranslucentBackground` + Acrylic, ver chrome.py), o Windows trata
# pixel com alpha ZERO como clique-através de propósito (mesmo bug já
# documentado no Project-ARGUS, `argus/core/widget.py`) - o clique nem
# chegava a virar `mousePressEvent` (confirmado com log de diagnóstico), ia
# direto pra janela por trás do SIREN, que então vinha pra frente e cobria
# ele.
#
# 🔥 PEGADINHA DE UNIDADE (2026-09-06, 2ª rodada - "mesmo problema, como foi
# feito no Argus?") - `rgba()` no QSS/CSS usa alpha como FRAÇÃO 0.0-1.0, não
# um inteiro 0-255. `rgba(0, 0, 0, 1)` (usado numa 1ª tentativa) significa
# opacidade TOTAL, não "1 de 255" - o Project-ARGUS já tinha documentado
# exatamente esse mesmo erro (`argus/core/widget.py::_ChipCategoria`).
# `rgba(0, 0, 0, 0.004)` (≈1/255 de verdade) é o valor certo -
# imperceptível, mas != 0. Além disso, `QWidget` puro não pinta o próprio
# "background" do QSS sozinho sem `Qt.WA_StyledBackground` (ver
# `chrome.py::BarraTitulo.__init__`/`configurar_janela_vidro_fosco`) - sem
# essa flag o valor daqui nunca vira pixel de verdade.
QSS = f"""
QWidget {{
    color: {COR_TEXTO};
    font-family: "Segoe UI";
    font-size: 13px;
    background: rgba(0, 0, 0, 0.004);
}}
#barraTitulo {{ background: rgba(0, 0, 0, 0.004); }}
#barraTituloTexto {{ font-weight: 600; color: {COR_TEXTO_FRACO}; }}
#barraTituloBotao, #barraTituloBotaoFechar {{
    background: transparent; border: none; border-radius: 6px;
    color: {COR_TEXTO_FRACO}; font-size: 13px;
}}
#barraTituloBotao:hover {{ background: rgba(255,255,255,30); }}
#barraTituloBotaoFechar:hover {{ background: {COR_LIKE}; color: white; }}

#sidebar {{ background: {COR_PAINEL}; border-right: 1px solid {COR_BORDA}; }}
#logoSiren {{ color: {COR_TEXTO}; font-size: 21px; font-weight: 700; font-style: italic; }}
#echoPill {{
    background: {COR_PAINEL_2}; border: 1px solid {COR_BORDA}; border-radius: 9px;
    padding: 6px 9px; color: {COR_TEXTO_FRACO}; font-size: 11px;
}}
#navBotao {{
    text-align: left; padding: 9px 12px; border-radius: 9px; border: none;
    background: transparent; color: {COR_TEXTO_FRACO}; font-weight: 600;
}}
#navBotao:hover {{ background: rgba(255,255,255,18); color: {COR_TEXTO}; }}
#navBotao:checked {{ background: {COR_PAINEL_2}; color: {COR_TEXTO}; }}

QScrollArea {{ border: none; background: transparent; }}

QFrame#painel {{ background: {COR_PAINEL}; border: 1px solid {COR_BORDA}; border-radius: 12px; }}

QListWidget {{ outline: none; background: transparent; border: none; }}
QListWidget::item {{ padding: 8px; border-radius: 8px; }}
QListWidget::item:hover {{ background: rgba(255,255,255,18); }}
QListWidget::item:selected {{ background: {COR_PAINEL_2}; color: {COR_TEXTO}; }}

QPushButton#botaoAccent {{
    background: {COR_ACCENT}; color: {COR_ACCENT_TINTA}; border: none;
    border-radius: 9px; padding: 8px 16px; font-weight: 700;
}}
QPushButton#botaoAccent:hover {{ background: {COR_ACCENT_ESCURO}; }}

QPushButton#botaoSecundario {{
    background: {COR_PAINEL_2}; border: 1px solid {COR_BORDA}; border-radius: 9px;
    padding: 7px 14px; color: {COR_TEXTO_FRACO}; font-weight: 600;
}}
QPushButton#botaoSecundario:hover {{ color: {COR_TEXTO}; }}
QPushButton#botaoSecundario:checked {{ color: {COR_ACCENT}; border-color: {COR_ACCENT_ESCURO}; }}

QPushButton#botaoIcone {{
    background: {COR_PAINEL_2}; border: 1px solid {COR_BORDA}; border-radius: 8px;
    color: {COR_TEXTO_FRACO}; font-size: 13px;
}}
QPushButton#botaoIcone:hover {{ color: {COR_TEXTO}; }}
QPushButton#botaoIcone:checked {{ color: {COR_ACCENT}; border-color: {COR_ACCENT_ESCURO}; }}

QPushButton#botaoLike, QPushButton#botaoDislike {{
    background: {COR_PAINEL_2}; border: 1px solid {COR_BORDA}; border-radius: 8px;
    color: {COR_TEXTO_FRACO}; font-size: 13px;
}}
QPushButton#botaoLike:hover, QPushButton#botaoDislike:hover {{ color: {COR_TEXTO}; }}
QPushButton#botaoLike:checked {{ color: {COR_LIKE}; border-color: {COR_LIKE}; }}
QPushButton#botaoDislike:checked {{ color: {COR_DISLIKE}; border-color: {COR_DISLIKE}; }}

#playerBar {{ background: {COR_PAINEL}; border-top: 1px solid {COR_BORDA}; }}
#tituloView {{ font-size: 20px; font-weight: 700; }}
#legendaView {{ color: {COR_TEXTO_FRACO}; font-size: 12px; }}
"""
