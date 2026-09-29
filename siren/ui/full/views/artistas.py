# -*- coding: utf-8 -*-
"""Tela Artistas (2026-09-26, pedido do usuário: "vai listar os artistas das
músicas que já ouvi, com a pontuação dele e músicas curtidas e não
curtidas, dando pra ordenar, e vindo como padrão do com maior pontuação").

Junta duas fontes:
- ECHO (`/perfil/artistas`): nota de -1 a +1 e estado de cada artista (regra
  das 5 chances), com as curtidas e não curtidas que o ECHO conhece (votos
  do SIREN e do ERIS);
- local: quantas vezes cada artista tocou no SIREN (`core/historico_local.py`)
  e, sem ECHO, as curtidas/não curtidas das playlists Músicas Curtidas e Não
  Curtidas.

Clicar num cabeçalho ordena por aquela coluna; o padrão é nota, maior
primeiro. Duplo clique abre a tela do artista."""
import unicodedata

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from siren.core import historico_local as historico_mod
from siren.core import playlists as playlists_mod
from siren.integrations import echo_client
from siren.ui.full import icones, styles

ESTADOS = {"normal": "", "em_prova": "Em prova", "rejeitado": "Rejeitado"}
COLUNAS = ["Artista", "Nota", "Curtidas", "Não curtidas", "Reproduções", "Estado"]
COLUNA_NOTA = 1


def _normalizar(texto):
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).strip().lower()


class _CarregarWorker(QThread):
    concluido = Signal(object)

    def run(self):
        self.concluido.emit(echo_client.obter_artistas())


class _ItemNumero(QTableWidgetItem):
    """Ordena pelo número guardado em `UserRole`, não pelo texto ("+0,97"
    ficaria antes de "-0,20" em ordem alfabética). Sem valor = sempre por
    último."""

    def __init__(self, texto, valor):
        super().__init__(texto)
        self.setData(Qt.UserRole, valor)
        self.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def __lt__(self, outro):
        a, b = self.data(Qt.UserRole), outro.data(Qt.UserRole)
        return (a if a is not None else float("-inf")) < (b if b is not None else float("-inf"))


def juntar_artistas(registros_echo, historico, curtidas, nao_curtidas):
    """Uma entrada por artista (chave sem acento/maiúsculas). Função pura -
    testável sem Qt nem ECHO."""
    artistas = {}

    def entrada(nome):
        chave = _normalizar(nome)
        return artistas.setdefault(chave, {
            "nome": nome, "nota": None, "curtidas": 0, "descurtidas": 0, "reproducoes": 0, "estado": "normal",
            "curtidas_local": 0, "descurtidas_local": 0, "tem_echo": False,
        })

    for item in historico:
        entrada(item["artista"])["reproducoes"] += 1
    for faixa in curtidas:
        entrada(faixa["artista"])["curtidas_local"] += 1
    for faixa in nao_curtidas:
        entrada(faixa["artista"])["descurtidas_local"] += 1
    for registro in registros_echo or []:
        dados = entrada(registro["nome"])
        dados.update(nome=registro["nome"], nota=registro.get("nota"), curtidas=registro.get("curtidas", 0),
                     descurtidas=registro.get("descurtidas", 0), estado=registro.get("estado", "normal"), tem_echo=True)
    for dados in artistas.values():
        if not dados["tem_echo"]:
            dados["curtidas"] = dados["curtidas_local"]
            dados["descurtidas"] = dados["descurtidas_local"]
    return list(artistas.values())


class ViewArtistas(QWidget):
    def __init__(self, ao_abrir_artista):
        super().__init__()
        self._ao_abrir_artista = ao_abrir_artista
        self._worker = None
        self._artistas = []

        titulo = QLabel("Artistas")
        titulo.setObjectName("tituloView")
        self._legenda = QLabel("")
        self._legenda.setObjectName("legendaView")

        self._busca = QLineEdit()
        self._busca.setObjectName("buscaGlobal")
        self._busca.setPlaceholderText("Buscar artista")
        self._busca.setClearButtonEnabled(True)
        self._busca.setFixedWidth(260)
        self._busca.setFixedHeight(38)
        self._busca.addAction(icones.icone("busca", styles.COR_TEXTO, 16), QLineEdit.LeadingPosition)
        self._busca.textChanged.connect(self._filtrar)

        cabecalho = QHBoxLayout()
        textos = QVBoxLayout()
        textos.setSpacing(4)
        textos.addWidget(titulo)
        textos.addWidget(self._legenda)
        cabecalho.addLayout(textos, stretch=1)
        cabecalho.addWidget(self._busca, alignment=Qt.AlignBottom)

        self._tabela = QTableWidget(0, len(COLUNAS))
        self._tabela.setObjectName("tabelaFaixas")
        self._tabela.setHorizontalHeaderLabels(COLUNAS)
        self._tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabela.setShowGrid(False)
        self._tabela.setFocusPolicy(Qt.NoFocus)
        self._tabela.verticalHeader().setVisible(False)
        self._tabela.verticalHeader().setDefaultSectionSize(44)
        cabecalho_tabela = self._tabela.horizontalHeader()
        cabecalho_tabela.setHighlightSections(False)
        cabecalho_tabela.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        cabecalho_tabela.setSectionResizeMode(0, QHeaderView.Stretch)
        for indice, largura in ((1, 90), (2, 100), (3, 120), (4, 120), (5, 110)):
            cabecalho_tabela.setSectionResizeMode(indice, QHeaderView.Fixed)
            self._tabela.setColumnWidth(indice, largura)
        cabecalho_tabela.setSortIndicatorShown(True)
        self._tabela.setSortingEnabled(True)
        self._tabela.cellDoubleClicked.connect(self._abrir_linha)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 20)
        layout.setSpacing(14)
        layout.addLayout(cabecalho)
        layout.addWidget(self._tabela, stretch=1)

    def atualizar(self):
        """Recarrega ao abrir a tela - as notas mudam a cada voto."""
        self._legenda.setText("Consultando o ECHO…")
        self._mostrar(juntar_artistas(None, historico_mod.carregar(), *self._votos_locais()))
        if self._worker is not None:
            return
        worker = _CarregarWorker(self)
        worker.concluido.connect(self._ao_carregar)
        worker.finished.connect(lambda w=worker: self._fim_worker(w))
        self._worker = worker
        worker.start()

    @staticmethod
    def _votos_locais():
        return (playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_CURTIDAS),
                playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_NAO_CURTIDAS))

    def _fim_worker(self, worker):
        if worker is self._worker:
            self._worker = None
        worker.deleteLater()

    def _ao_carregar(self, registros):
        artistas = juntar_artistas(registros, historico_mod.carregar(), *self._votos_locais())
        self._mostrar(artistas)
        total = len(artistas)
        if registros is None:
            self._legenda.setText(f"{total} artistas. ECHO offline: sem nota agora, contagens das suas playlists.")
        else:
            self._legenda.setText(f"{total} artistas que você ouviu ou votou. Clique num cabeçalho para ordenar; duplo clique abre o artista.")

    def _mostrar(self, artistas):
        self._artistas = artistas
        cabecalho = self._tabela.horizontalHeader()
        coluna, ordem = cabecalho.sortIndicatorSection(), cabecalho.sortIndicatorOrder()
        if not self._tabela.rowCount():
            coluna, ordem = COLUNA_NOTA, Qt.DescendingOrder  # padrão: maior nota primeiro
        self._tabela.setSortingEnabled(False)
        self._tabela.setRowCount(len(artistas))
        cor_fraca = QColor(styles.COR_TEXTO_FRACO)
        for linha, dados in enumerate(artistas):
            nome = QTableWidgetItem(dados["nome"])
            nome.setData(Qt.UserRole, dados["nome"])
            self._tabela.setItem(linha, 0, nome)
            nota = dados["nota"]
            item_nota = _ItemNumero(f"{nota:+.2f}".replace(".", ",") if nota is not None else "-", nota)
            if nota is not None:
                item_nota.setForeground(QColor(styles.COR_OURO if nota >= 0.5 else styles.COR_TEXTO if nota >= 0 else styles.COR_DISLIKE))
            self._tabela.setItem(linha, 1, item_nota)
            for coluna_indice, chave in ((2, "curtidas"), (3, "descurtidas"), (4, "reproducoes")):
                item = _ItemNumero(str(dados[chave]), dados[chave])
                item.setForeground(cor_fraca)
                self._tabela.setItem(linha, coluna_indice, item)
            estado = QTableWidgetItem(ESTADOS.get(dados["estado"], ""))
            estado.setForeground(QColor(styles.COR_OURO) if dados["estado"] == "em_prova" else QColor(styles.COR_DISLIKE))
            self._tabela.setItem(linha, 5, estado)
        self._tabela.setSortingEnabled(True)
        self._tabela.sortItems(coluna, ordem)
        self._filtrar(self._busca.text())

    def _filtrar(self, texto):
        alvo = _normalizar(texto)
        for linha in range(self._tabela.rowCount()):
            item = self._tabela.item(linha, 0)
            self._tabela.setRowHidden(linha, bool(alvo) and alvo not in _normalizar(item.text() if item else ""))

    def _abrir_linha(self, linha, _coluna):
        item = self._tabela.item(linha, 0)
        if item:
            self._ao_abrir_artista(item.data(Qt.UserRole))
