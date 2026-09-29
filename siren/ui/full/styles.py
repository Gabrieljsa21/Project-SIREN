# -*- coding: utf-8 -*-
"""QSS do Modo Completo - visual "noturno azul" (2026-09-25): fundo azul
marinho com brilho difuso no topo (pintado em
`main_window.py::FullWindow.paintEvent`), sidebar/conteúdo/player como
painéis flutuantes arredondados e accent azul. Substitui a paleta
índigo/dourado original. Painéis usam fundo translúcido (rgba com alpha < 1)
pra deixar o gradiente da janela aparecer por trás."""

COR_FUNDO = "#060b18"
COR_TEXTO = "#eef2ff"
COR_TEXTO_FRACO = "#9aa6c4"
COR_TEXTO_AZUL = "#8fb4ff"
COR_ACCENT = "#3b82f6"
COR_ACCENT_CLARO = "#60a5fa"
COR_ACCENT_ESCURO = "#2563eb"
COR_ACCENT_TINTA = "#ffffff"
COR_BORDA = "rgba(130, 160, 255, 0.13)"
COR_BORDA_FORTE = "rgba(130, 160, 255, 0.24)"
COR_PAINEL = "rgba(10, 18, 38, 0.50)"
COR_PAINEL_2 = "rgba(28, 42, 78, 0.70)"
COR_LIKE = "#f43f7a"
COR_DISLIKE = "#8b9bd4"
COR_BIOLUM = "#3fe0d0"  # ciano-turquesa do brilho de hover (plâncton luminoso)
COR_OURO = "#e8c26a"  # cristais dourados da logo - marca o item ativo da sidebar (curtir usa COR_LIKE)
COR_LUAR = "#dfe8ff"
COR_ONLINE = "#34d399"
COR_OFFLINE = "#f5b041"

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
    font-family: "Segoe UI Variable Text", "Segoe UI";
    font-size: 13px;
    background: rgba(0, 0, 0, 0.004);
}}
QToolTip {{ background: #111c38; color: {COR_TEXTO}; border: 1px solid {COR_BORDA_FORTE}; padding: 4px 8px; }}

#barraTitulo {{ background: rgba(0, 0, 0, 0.004); }}
#barraTituloTexto {{ font-weight: 600; color: {COR_TEXTO_FRACO}; font-size: 12px; }}
#barraTituloBotao, #barraTituloBotaoFechar {{
    background: rgba(0, 0, 0, 0.004); border: none; border-radius: 6px;
}}
#barraTituloBotao:hover {{ background: rgba(255, 255, 255, 0.08); }}
#barraTituloBotaoFechar:hover {{ background: {COR_LIKE}; }}

#sidebar, #painelConteudo, #playerBar {{
    background: {COR_PAINEL}; border: 1px solid {COR_BORDA}; border-radius: 16px;
}}
#topBar, #homeBody {{ background: rgba(0, 0, 0, 0.004); }}

#logoSiren {{ color: {COR_TEXTO}; font-size: 28px; font-weight: 800; font-style: italic; }}
#echoPill {{
    background: rgba(255, 255, 255, 0.04); border: 1px solid {COR_BORDA}; border-radius: 15px;
    padding: 6px 12px; color: {COR_TEXTO_FRACO}; font-size: 11px;
}}
#navBotao {{
    text-align: left; padding: 9px 14px; border-radius: 11px; border: 1px solid rgba(0, 0, 0, 0.004);
    background: rgba(0, 0, 0, 0.004); color: {COR_TEXTO}; font-size: 14px;
}}
#navBotao:hover {{ background: rgba(59, 130, 246, 0.10); border: 1px solid rgba(96, 165, 250, 0.40); }}
#navBotao:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(59, 130, 246, 0.38), stop:1 rgba(59, 130, 246, 0.10));
    border: 1px solid rgba(96, 165, 250, 0.45);
}}
#tituloBiblioteca {{ color: {COR_TEXTO}; font-size: 17px; font-weight: 700; }}
#botaoBiblioteca, #botaoCircular {{
    background: rgba(255, 255, 255, 0.05); border: 1px solid {COR_BORDA}; border-radius: 17px;
}}
#botaoBiblioteca:hover, #botaoCircular:hover {{ background: rgba(255, 255, 255, 0.12); }}
#botaoContorno {{
    background: rgba(255, 255, 255, 0.03); border: 1px solid {COR_BORDA_FORTE}; border-radius: 11px;
    padding: 11px 14px; color: {COR_TEXTO}; font-size: 14px;
}}
#botaoContorno:hover {{ background: rgba(255, 255, 255, 0.08); }}

#buscaGlobal {{
    background: rgba(255, 255, 255, 0.05); border: 1px solid {COR_BORDA_FORTE};
    border-radius: 21px; padding: 0px 16px 0px 8px; color: {COR_TEXTO}; font-size: 14px;
    selection-background-color: {COR_ACCENT_ESCURO};
}}
#buscaGlobal:focus {{ border-color: rgba(96, 165, 250, 0.75); }}

QScrollArea {{ border: none; background: rgba(0, 0, 0, 0.004); }}
QScrollBar:vertical {{ background: rgba(0, 0, 0, 0.004); width: 8px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: rgba(255, 255, 255, 0.14); border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(255, 255, 255, 0.26); }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QFrame#painel {{ background: {COR_PAINEL}; border: 1px solid {COR_BORDA}; border-radius: 12px; }}

QListWidget {{ outline: none; background: rgba(0, 0, 0, 0.004); border: none; }}
QListWidget::item {{ padding: 8px; border-radius: 8px; }}
QListWidget::item:hover {{ background: rgba(255, 255, 255, 0.06); }}
QListWidget::item:selected {{ background: rgba(59, 130, 246, 0.22); color: {COR_TEXTO}; }}

QPushButton#botaoAccent {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {COR_ACCENT_CLARO}, stop:1 {COR_ACCENT_ESCURO});
    color: {COR_ACCENT_TINTA}; border: none; border-radius: 10px; padding: 8px 16px; font-weight: 700;
}}
QPushButton#botaoAccent:hover {{ background: {COR_ACCENT_CLARO}; }}
QPushButton#botaoAccent:disabled {{ background: rgba(59, 130, 246, 0.35); color: rgba(255, 255, 255, 0.6); }}

QPushButton#botaoCaos {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:0.55 #3b82f6, stop:1 #8b5cf6);
    color: white; border: none; border-radius: 25px; padding: 0px 24px; font-size: 14px; font-weight: 700;
}}
QPushButton#botaoCaos:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7dd3fc, stop:0.55 #60a5fa, stop:1 #a78bfa);
}}

QPushButton#botaoSecundario {{
    background: rgba(255, 255, 255, 0.04); border: 1px solid {COR_BORDA_FORTE}; border-radius: 10px;
    padding: 7px 14px; color: {COR_TEXTO_FRACO}; font-weight: 600;
}}
QPushButton#botaoSecundario:hover {{ color: {COR_TEXTO}; background: rgba(255, 255, 255, 0.08); }}
QPushButton#botaoSecundario:checked {{ color: {COR_ACCENT_CLARO}; border-color: {COR_ACCENT}; }}

QPushButton#botaoIcone {{ background: rgba(0, 0, 0, 0.004); border: none; border-radius: 18px; }}
QPushButton#botaoIcone:hover {{ background: rgba(255, 255, 255, 0.08); }}

QPushButton#botaoModo {{ background: rgba(0, 0, 0, 0.004); border: none; border-radius: 16px; }}
QPushButton#botaoModo:hover {{ background: rgba(255, 255, 255, 0.08); }}

QPushButton#botaoPlay {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {COR_ACCENT_CLARO}, stop:1 {COR_ACCENT_ESCURO});
    border: 2px solid rgba(147, 197, 253, 0.55); border-radius: 26px;
}}
QPushButton#botaoPlay:hover {{ background: {COR_ACCENT_CLARO}; }}
QPushButton#botaoPlay:disabled {{ background: rgba(59, 130, 246, 0.30); border-color: rgba(147, 197, 253, 0.2); }}

QPushButton#botaoPlayPlayer {{
    background: rgba(59, 130, 246, 0.16); border: 2px solid {COR_ACCENT_CLARO}; border-radius: 20px;
}}
QPushButton#botaoPlayPlayer:hover {{ background: rgba(59, 130, 246, 0.34); }}
QPushButton#botaoPlayPlayer:disabled {{ background: rgba(255, 255, 255, 0.03); border-color: rgba(147, 197, 253, 0.25); }}

#divisorSidebar {{ background: {COR_BORDA}; }}
#rotuloGrupo {{ color: {COR_TEXTO_AZUL}; font-size: 11px; font-weight: 600; }}
#bibliotecaVazia {{ color: {COR_TEXTO_FRACO}; font-size: 12px; padding: 6px 4px; }}
#botaoPequeno {{
    background: rgba(255, 255, 255, 0.04); border: 1px solid {COR_BORDA}; border-radius: 15px;
}}
#botaoPequeno:hover {{ background: rgba(255, 255, 255, 0.12); }}

QPushButton#botaoPlayCartao {{
    background: rgba(8, 14, 30, 0.62); border: 1px solid rgba(255, 255, 255, 0.14); border-radius: 22px;
}}
QPushButton#botaoPlayCartao:hover {{ background: {COR_ACCENT}; border-color: {COR_ACCENT_CLARO}; }}

QPushButton#botaoLike, QPushButton#botaoDislike {{
    background: rgba(255, 255, 255, 0.05); border: 1px solid {COR_BORDA}; border-radius: 19px;
}}
QPushButton#botaoLike:hover, QPushButton#botaoDislike:hover {{ background: rgba(255, 255, 255, 0.10); }}
QPushButton#botaoLike:checked {{ background: rgba(244, 63, 122, 0.16); border-color: rgba(244, 63, 122, 0.55); }}
QPushButton#botaoDislike:checked {{ background: rgba(139, 155, 212, 0.18); border-color: {COR_DISLIKE}; }}

#capaPlayer {{ background: {COR_PAINEL_2}; border-radius: 8px; }}
#tituloFaixaPlayer {{ font-size: 14px; font-weight: 700; }}
#botaoPlayerTexto {{
    background: rgba(255, 255, 255, 0.03); border: 1px solid {COR_BORDA_FORTE}; border-radius: 11px;
    color: {COR_TEXTO}; padding: 9px 16px; font-size: 13px;
}}
#botaoPlayerTexto:hover {{ background: rgba(255, 255, 255, 0.09); }}
#separadorVertical {{ background: {COR_BORDA_FORTE}; }}
#tempoPlayer {{ color: {COR_TEXTO_FRACO}; font-size: 11px; }}

QSlider::groove:horizontal {{ height: 4px; background: rgba(255, 255, 255, 0.16); border-radius: 2px; }}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COR_ACCENT_ESCURO}, stop:1 {COR_ACCENT_CLARO});
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: white; width: 10px; height: 10px; margin: -5px 0px; border-radius: 7px;
    border: 2px solid {COR_ACCENT_CLARO};
}}
QSlider::handle:horizontal:disabled {{ background: rgba(255, 255, 255, 0.3); border-color: rgba(255, 255, 255, 0.1); }}
QSlider::sub-page:horizontal:disabled {{ background: rgba(255, 255, 255, 0.16); }}

#tituloHome {{ font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 36px; font-weight: 700; }}
#subtituloHome {{ color: {COR_TEXTO_AZUL}; font-size: 16px; }}
#tituloSecao {{ font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 26px; font-weight: 700; }}
#subtituloSecao {{ color: {COR_TEXTO_FRACO}; font-size: 14px; }}
#cartaoDestaque, #cartaoVazio {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(22, 34, 66, 0.80), stop:1 rgba(12, 20, 42, 0.62));
    border: 1px solid {COR_BORDA}; border-radius: 14px;
}}
#rotuloSobrelinha {{ color: {COR_TEXTO_FRACO}; font-size: 11px; letter-spacing: 1px; }}
#tituloDestaque {{ font-size: 21px; font-weight: 700; }}
#textoDestaque {{ color: {COR_TEXTO_FRACO}; font-size: 14px; }}
#tituloVazio {{ font-size: 15px; }}
#textoVazio {{ color: {COR_TEXTO_FRACO}; font-size: 12px; }}
#caixaIconeVazio {{ background: rgba(255, 255, 255, 0.06); border-radius: 12px; }}

#tabelaFaixas {{ background: rgba(0, 0, 0, 0.004); border: none; outline: none; }}
#tabelaFaixas::item {{ border: none; padding: 0px 6px; }}
#tabelaFaixas::item:hover {{ background: rgba(255, 255, 255, 0.05); }}
#tabelaFaixas::item:selected {{ background: rgba(59, 130, 246, 0.18); color: {COR_TEXTO}; }}
#tabelaFaixas QHeaderView::section {{
    background: rgba(0, 0, 0, 0.004); color: {COR_TEXTO_FRACO}; border: none;
    border-bottom: 1px solid {COR_BORDA_FORTE}; padding: 8px 6px; font-size: 12px;
}}
#tabelaFaixas QTableCornerButton::section {{ background: rgba(0, 0, 0, 0.004); border: none; }}
QPushButton#botaoAcaoLinha {{ background: rgba(0, 0, 0, 0.004); border: none; border-radius: 15px; }}
QPushButton#botaoAcaoLinha:hover {{ background: rgba(255, 255, 255, 0.10); }}
QPushButton#botaoAcaoLinha:disabled {{ background: rgba(0, 0, 0, 0.004); }}
QPushButton#botaoAcaoLinha:checked {{ background: rgba(139, 155, 212, 0.22); }}
QMenu {{ background: #111c38; border: 1px solid {COR_BORDA_FORTE}; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 8px 28px 8px 12px; border-radius: 6px; color: {COR_TEXTO}; }}
QMenu::item:selected {{ background: rgba(59, 130, 246, 0.25); }}
QMenu::item:disabled {{ color: {COR_TEXTO_FRACO}; font-size: 11px; }}
QMenu::indicator {{ width: 14px; height: 14px; right: 8px; left: auto; }}

#tituloArtista {{ font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 40px; font-weight: 800; }}
#avisoEstadoArtista {{
    color: {COR_OURO}; background: rgba(232, 194, 106, 0.10); border: 1px solid rgba(232, 194, 106, 0.35);
    border-radius: 8px; padding: 6px 10px; font-size: 12px;
}}
QScrollBar:horizontal {{ background: rgba(0, 0, 0, 0.004); height: 8px; margin: 2px 4px; }}
QScrollBar::handle:horizontal {{ background: rgba(255, 255, 255, 0.14); border-radius: 3px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: rgba(255, 255, 255, 0.26); }}

#tituloView {{ font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 24px; font-weight: 700; }}
#legendaView {{ color: {COR_TEXTO_FRACO}; font-size: 12px; }}
"""
