# -*- coding: utf-8 -*-
"""Tela Fila em tabela, no estilo da lista de faixas do Spotify (2026-09-26).

Colunas fixas: número, título (capa + nome + artista clicável, que abre a
tela do artista) e ações da linha (curtir, não curtir, remover). Colunas
opcionais ("Álbum", "Duração", "Origem", "Adicionada em") ligam/desligam
pelo menu "Colunas" e a escolha fica salva em `config.json::fila_colunas`.
Álbum e duração vêm do cache `core/cache_faixas.py`, preenchido em segundo
plano pelo ECHO (Last.fm) e pela duração real das faixas que já tocaram.

O título ocupa o espaço que sobra, mas nunca menos que
`faixas.LARGURA_MINIMA_TITULO`: com colunas demais pra largura da janela,
aparece barra de rolagem horizontal em vez de uma coluna invadir a outra.

Arrastar uma linha troca a posição dela, no mesmo padrão já usado no editor
da Gesture Wheel do Project-LOKI: `QDrag` com um retrato semitransparente
da linha e uma linha dourada mostrando onde ela vai entrar (metade de cima
do alvo insere antes, metade de baixo insere depois). Os botões de subir e
descer saíram por isso."""
import time
from datetime import datetime

from PySide6.QtCore import QMimeData, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QHBoxLayout, QHeaderView, QLabel, QMenu, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from siren.core import config as config_mod
from siren.ui.full import faixas as faixas_ui
from siren.ui.full import icones, styles

# chave -> (título no cabeçalho, largura fixa), na ordem em que aparecem
COLUNAS_OPCIONAIS = {
    "album": ("Álbum", 200),
    "origem": ("Origem", 170),
    "adicionada_em": ("Adicionada em", 120),
    "duracao": ("Duração", 80),
}
LARGURA_NUMERO = 44
LARGURA_ACOES = 110


def _descrever_origem(origem):
    origem = origem or "fila"
    if origem.startswith("playlist:"):
        return f"Playlist · {origem.split(':', 1)[1]}"
    if origem.startswith("artista:"):
        return f"Artista · {origem.split(':', 1)[1]}"
    return {
        "caos": "Caos", "descoberta": "Descoberta", "busca": "Busca", "fila": "Adicionada por você",
        "historico": "Histórico",
    }.get(origem, origem.capitalize())


def _descrever_quando(instante):
    if not instante:
        return "-"
    minutos = int((time.time() - instante) // 60)
    if minutos < 1:
        return "agora"
    if minutos < 60:
        return f"há {minutos} min"
    return datetime.fromtimestamp(instante).strftime("%H:%M")


class _TabelaArrastavel(QTableWidget):
    """`QTableWidget` que reordena linhas por arraste, sem o `InternalMove`
    nativo (que não carrega os widgets de célula - capa, botões - junto com
    a linha). Emite `linha_movida(origem, destino)`; quem reordena de fato
    é a `Fila`, e a tela se remonta a partir dela."""

    linha_movida = Signal(int, int)
    redimensionada = Signal()
    MIME = "application/x-siren-linha-fila"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self._linha_pressionada = None
        self._pos_pressionada = None
        self._y_indicador = None

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self.redimensionada.emit()

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            self._linha_pressionada = self.rowAt(int(evento.position().y()))
            self._pos_pressionada = evento.position()
        super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento):
        if (
            self._linha_pressionada is not None and self._linha_pressionada >= 0
            and evento.buttons() & Qt.LeftButton
            and (evento.position() - self._pos_pressionada).manhattanLength() >= QApplication.startDragDistance()
        ):
            linha = self._linha_pressionada
            self._linha_pressionada = None
            self._iniciar_arraste(linha, evento.position())
            return
        super().mouseMoveEvent(evento)

    def mouseReleaseEvent(self, evento):
        self._linha_pressionada = None
        super().mouseReleaseEvent(evento)

    def _retangulo_linha(self, linha):
        return QRect(0, self.rowViewportPosition(linha), self.viewport().width(), self.rowHeight(linha))

    def _iniciar_arraste(self, linha, posicao):
        """Retrato semitransparente da linha acompanha o cursor (mesmo
        pedido que motivou isso no LOKI: ver o card sendo de fato
        arrastado)."""
        retangulo = self._retangulo_linha(linha)
        retrato = self.viewport().grab(retangulo)
        semi_transparente = QPixmap(retrato.size())
        semi_transparente.setDevicePixelRatio(retrato.devicePixelRatio())
        semi_transparente.fill(Qt.transparent)
        pintor = QPainter(semi_transparente)
        pintor.setOpacity(0.75)
        pintor.drawPixmap(0, 0, retrato)
        pintor.end()

        mime = QMimeData()
        mime.setData(self.MIME, str(linha).encode("ascii"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(semi_transparente)
        drag.setHotSpot(QPoint(int(posicao.x()), int(posicao.y()) - retangulo.top()))
        drag.exec(Qt.MoveAction)
        self._definir_indicador(None)

    def _destino(self, y):
        """Posição de inserção (0..rowCount) pra um `y` do viewport."""
        linha = self.rowAt(int(y))
        if linha < 0:
            return self.rowCount() if y > 0 else 0
        retangulo = self._retangulo_linha(linha)
        return linha + 1 if y > retangulo.center().y() else linha

    def _definir_indicador(self, destino):
        if destino is None or self.rowCount() == 0:
            self._y_indicador = None
        elif destino >= self.rowCount():
            self._y_indicador = self._retangulo_linha(self.rowCount() - 1).bottom()
        else:
            self._y_indicador = self.rowViewportPosition(destino)
        self.viewport().update()

    def dragEnterEvent(self, evento):
        if evento.source() is self and evento.mimeData().hasFormat(self.MIME):
            evento.acceptProposedAction()
        else:
            evento.ignore()

    def dragMoveEvent(self, evento):
        if evento.source() is not self:
            evento.ignore()
            return
        self._definir_indicador(self._destino(evento.position().y()))
        evento.acceptProposedAction()

    def dragLeaveEvent(self, evento):
        self._definir_indicador(None)

    def dropEvent(self, evento):
        if evento.source() is not self or not evento.mimeData().hasFormat(self.MIME):
            evento.ignore()
            return
        origem = int(bytes(evento.mimeData().data(self.MIME)).decode("ascii"))
        destino = self._destino(evento.position().y())
        self._definir_indicador(None)
        evento.acceptProposedAction()
        if destino not in (origem, origem + 1):
            self.linha_movida.emit(origem, destino)

    def paintEvent(self, evento):
        super().paintEvent(evento)
        if self._y_indicador is None:
            return
        pintor = QPainter(self.viewport())
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setPen(QPen(QColor(styles.COR_OURO), 2))
        y = max(1, min(self._y_indicador, self.viewport().height() - 1))
        pintor.drawLine(8, y, self.viewport().width() - 8, y)
        pintor.setBrush(QColor(styles.COR_OURO))
        pintor.drawEllipse(QPoint(8, y), 3, 3)


class ViewFila(QWidget):
    """Mostra o conteúdo de uma `core.fila.Fila` compartilhada com a janela
    principal - este widget nunca é dono da fila, só a lê/reordena."""

    def __init__(self, fila, ao_tocar, ao_votar=None, ao_abrir_artista=None):
        """`ao_votar(faixa, positivo)`: a janela principal manda o voto pro
        ECHO e pras playlists locais (mesmo caminho dos botões do player).
        `ao_abrir_artista(nome)`: clique no nome do artista."""
        super().__init__()
        self._fila = fila
        self._ao_tocar = ao_tocar
        self._ao_votar = ao_votar
        self._ao_abrir_artista = ao_abrir_artista
        self._worker_info = None
        self._colunas_visiveis = [c for c in (config_mod.obter("fila_colunas") or []) if c in COLUNAS_OPCIONAIS]

        titulo = QLabel("Fila")
        titulo.setObjectName("tituloView")
        legenda = QLabel("Arraste uma música para mudar a ordem. O ECHO só sugere quem entra; a ordem é sempre sua.")
        legenda.setObjectName("legendaView")

        self._botao_colunas = QPushButton("  Colunas")
        self._botao_colunas.setObjectName("botaoSecundario")
        self._botao_colunas.setIcon(icones.icone("fila", styles.COR_TEXTO_FRACO, 16))
        self._botao_colunas.setCursor(Qt.PointingHandCursor)
        self._botao_colunas.setToolTip("Escolher colunas (também no clique direito do cabeçalho)")
        self._botao_colunas.clicked.connect(
            lambda: self._abrir_menu_colunas(self._botao_colunas.mapToGlobal(QPoint(0, self._botao_colunas.height() + 4)))
        )

        cabecalho = QHBoxLayout()
        textos = QVBoxLayout()
        textos.setSpacing(4)
        textos.addWidget(titulo)
        textos.addWidget(legenda)
        cabecalho.addLayout(textos, stretch=1)
        cabecalho.addWidget(self._botao_colunas, alignment=Qt.AlignBottom)

        self._tabela = _TabelaArrastavel()
        self._tabela.linha_movida.connect(self._mover_para)
        self._tabela.redimensionada.connect(self._ajustar_larguras)
        self._tabela.setObjectName("tabelaFaixas")
        self._tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabela.setShowGrid(False)
        self._tabela.setFocusPolicy(Qt.NoFocus)
        self._tabela.setMouseTracking(True)
        self._tabela.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._tabela.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._tabela.verticalHeader().setVisible(False)
        self._tabela.verticalHeader().setDefaultSectionSize(faixas_ui.ALTURA_LINHA)
        cabecalho_tabela = self._tabela.horizontalHeader()
        cabecalho_tabela.setHighlightSections(False)
        cabecalho_tabela.setStretchLastSection(False)
        cabecalho_tabela.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        cabecalho_tabela.setContextMenuPolicy(Qt.CustomContextMenu)
        cabecalho_tabela.customContextMenuRequested.connect(
            lambda posicao: self._abrir_menu_colunas(cabecalho_tabela.mapToGlobal(posicao))
        )
        self._tabela.cellDoubleClicked.connect(self._tocar_linha)

        self._vazia = QLabel("Fila vazia - toque algo de uma playlist ou peça Caos.")
        self._vazia.setObjectName("legendaView")
        self._vazia.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 20)
        layout.setSpacing(14)
        layout.addLayout(cabecalho)
        layout.addWidget(self._tabela, stretch=1)
        layout.addWidget(self._vazia, stretch=1)

    # ---------------- colunas ----------------

    def _colunas(self):
        """Ordem final das colunas: #, Título, opcionais visíveis, ações."""
        return ["numero", "titulo"] + [c for c in COLUNAS_OPCIONAIS if c in self._colunas_visiveis] + ["acoes"]

    def _abrir_menu_colunas(self, posicao_global):
        menu = QMenu(self)
        cabecalho = menu.addAction("Colunas")
        cabecalho.setEnabled(False)
        for chave, (rotulo, _largura) in COLUNAS_OPCIONAIS.items():
            acao = menu.addAction(rotulo)
            acao.setCheckable(True)
            acao.setChecked(chave in self._colunas_visiveis)
            acao.toggled.connect(lambda marcada, c=chave: self._alternar_coluna(c, marcada))
        menu.exec(posicao_global)

    def _alternar_coluna(self, chave, visivel):
        if visivel and chave not in self._colunas_visiveis:
            self._colunas_visiveis.append(chave)
        elif not visivel and chave in self._colunas_visiveis:
            self._colunas_visiveis.remove(chave)
        config_mod.definir("fila_colunas", list(self._colunas_visiveis))
        self.atualizar()

    def _largura_fixa(self, coluna):
        return {"numero": LARGURA_NUMERO, "acoes": LARGURA_ACOES}.get(coluna) or COLUNAS_OPCIONAIS[coluna][1]

    def _configurar_colunas(self):
        colunas = self._colunas()
        rotulos = {"numero": "#", "titulo": "Título", "acoes": ""}
        rotulos.update({c: r for c, (r, _l) in COLUNAS_OPCIONAIS.items()})
        self._tabela.setColumnCount(len(colunas))
        self._tabela.setHorizontalHeaderLabels([rotulos[c] for c in colunas])
        cabecalho = self._tabela.horizontalHeader()
        for indice in range(len(colunas)):
            cabecalho.setSectionResizeMode(indice, QHeaderView.Fixed)
        if "duracao" in colunas:
            item = self._tabela.horizontalHeaderItem(colunas.index("duracao"))
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._ajustar_larguras()
        return colunas

    def _ajustar_larguras(self):
        """Título fica com o que sobra da largura visível, com piso de
        `LARGURA_MINIMA_TITULO` - abaixo disso a soma passa da largura e a
        tabela ganha rolagem horizontal (bug corrigido em 2026-09-26: com
        `Stretch` o título encolhia a zero e as colunas se sobrepunham)."""
        colunas = self._colunas()
        if self._tabela.columnCount() != len(colunas):
            return
        largura_disponivel = self._tabela.viewport().width()
        if self._tabela.verticalScrollBar().isVisible():
            largura_disponivel = self._tabela.width() - self._tabela.verticalScrollBar().width() - 2
        soma_fixas = 0
        for indice, coluna in enumerate(colunas):
            if coluna == "titulo":
                continue
            largura = self._largura_fixa(coluna)
            self._tabela.setColumnWidth(indice, largura)
            soma_fixas += largura
        self._tabela.setColumnWidth(
            colunas.index("titulo"), max(faixas_ui.LARGURA_MINIMA_TITULO, largura_disponivel - soma_fixas),
        )

    # ---------------- ações das linhas ----------------

    def _celula_acoes(self, indice, faixa):
        celula = QWidget()
        layout = QHBoxLayout(celula)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(2)
        layout.addStretch()
        if self._ao_votar is not None:
            for botao in faixas_ui.botoes_voto(faixa.get("voto"), lambda voto, i=indice: self._votar(i, voto)):
                layout.addWidget(botao)
        remover = faixas_ui.botao_acao("fechar", "Remover da fila")
        remover.clicked.connect(lambda _=False, i=indice: self._remover(i))
        layout.addWidget(remover)
        return celula

    def _votar(self, indice, voto):
        faixas = self._fila.listar()
        if not (0 <= indice < len(faixas)) or faixas[indice].get("voto") == voto:
            self.atualizar()  # reclicar no botão já marcado não desfaz o voto (o ECHO não tem "tirar voto")
            return
        self._fila.definir_voto(indice, voto)
        self._ao_votar(faixas[indice], voto == "positivo")
        self.atualizar()

    def _mover_para(self, origem, destino):
        self._fila.mover_para(origem, destino)
        self.atualizar()

    def _remover(self, indice):
        self._fila.remover(indice)
        self.atualizar()

    def _tocar_linha(self, linha, _coluna):
        faixas = self._fila.listar()
        if 0 <= linha < len(faixas):
            faixa = faixas[linha]
            self._ao_tocar(faixa["titulo"], faixa["artista"], origem=faixa.get("origem", "fila"))

    # ---------------- álbum/duração em segundo plano ----------------

    def _buscar_infos(self, faixas):
        if self._worker_info is not None:
            return
        worker = faixas_ui.InfoFaixasWorker(faixas, self)
        if not worker.tem_trabalho:
            worker.deleteLater()
            return
        worker.info_pronta.connect(self._aplicar_info)
        worker.finished.connect(lambda w=worker: self._fim_worker_info(w))
        self._worker_info = worker
        worker.start()

    def _fim_worker_info(self, worker):
        if worker is self._worker_info:
            self._worker_info = None
        worker.deleteLater()

    def _aplicar_info(self, titulo, artista):
        """Atualiza só as células de álbum/duração das linhas dessa faixa."""
        colunas = self._colunas()
        for linha, faixa in enumerate(self._fila.listar()):
            if faixa["titulo"] != titulo or faixa["artista"] != artista:
                continue
            for coluna, texto in (("album", faixas_ui.texto_album(faixa)), ("duracao", faixas_ui.texto_duracao(faixa))):
                if coluna in colunas and self._tabela.item(linha, colunas.index(coluna)):
                    self._tabela.item(linha, colunas.index(coluna)).setText(texto)

    # ---------------- montagem ----------------

    def atualizar(self):
        faixas = self._fila.listar()
        self._tabela.setVisible(bool(faixas))
        self._vazia.setVisible(not faixas)
        # Zera antes de remontar: `setItem` não tira um widget de célula
        # antigo, e ao mudar as colunas os botões de uma coluna que mudou
        # de lugar ficavam desenhados por cima do texto (bug de 2026-09-26).
        self._tabela.clearContents()
        self._tabela.setRowCount(0)
        colunas = self._configurar_colunas()
        self._tabela.setRowCount(len(faixas))
        cor_fraca = QColor(styles.COR_TEXTO_FRACO)
        for linha, faixa in enumerate(faixas):
            pulada = faixa.get("voto") == "negativo"
            for coluna_indice, coluna in enumerate(colunas):
                if coluna in ("titulo", "acoes"):
                    self._tabela.setItem(linha, coluna_indice, QTableWidgetItem(""))
                    if coluna == "titulo":
                        widget = faixas_ui.CelulaTitulo(faixa, self._ao_abrir_artista, pulada=pulada)
                    else:
                        widget = self._celula_acoes(linha, faixa)
                    self._tabela.setCellWidget(linha, coluna_indice, widget)
                    continue
                texto = {
                    "numero": lambda: str(linha + 1),
                    "album": lambda: faixas_ui.texto_album(faixa),
                    "duracao": lambda: faixas_ui.texto_duracao(faixa),
                    "origem": lambda: _descrever_origem(faixa.get("origem")),
                    "adicionada_em": lambda: _descrever_quando(faixa.get("adicionada_em")),
                }[coluna]()
                item = QTableWidgetItem(texto)
                item.setToolTip(texto if coluna == "album" else "")
                alinhamento = {"numero": Qt.AlignCenter, "duracao": Qt.AlignRight | Qt.AlignVCenter}
                item.setTextAlignment(alinhamento.get(coluna, Qt.AlignLeft | Qt.AlignVCenter))
                item.setForeground(cor_fraca)
                self._tabela.setItem(linha, coluna_indice, item)
        self._ajustar_larguras()
        if "album" in colunas or "duracao" in colunas:
            self._buscar_infos(faixas)
