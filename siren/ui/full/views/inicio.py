# -*- coding: utf-8 -*-
"""Home do SIREN: descoberta e biblioteca em uma única superfície."""
from datetime import datetime

from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QLabel, QListView, QListWidget, QListWidgetItem, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from siren.core import playlists as playlists_mod
from siren.integrations import echo_client


class _CarregarInicioWorker(QThread):
    concluido = Signal(list, list)

    def run(self):
        self.concluido.emit(echo_client.obter_em_alta(), echo_client.obter_redescobertas())


class ViewInicio(QWidget):
    """Equivalente à Home do Spotify, alimentada pela inteligência do ECHO."""

    def __init__(self, ao_tocar, ao_abrir_playlist, ao_iniciar_caos):
        super().__init__()
        self._ao_tocar = ao_tocar
        self._ao_abrir_playlist = ao_abrir_playlist
        self._ao_iniciar_caos = ao_iniciar_caos
        self._worker = None
        self._carregado = False

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        corpo = QWidget()
        corpo.setObjectName("homeBody")
        layout = QVBoxLayout(corpo)
        layout.setContentsMargins(30, 26, 30, 34)
        layout.setSpacing(14)

        saudacao = QLabel(self._saudacao())
        saudacao.setObjectName("tituloHome")
        layout.addWidget(saudacao)

        self._atalhos = self._criar_prateleira(68)
        self._atalhos.itemActivated.connect(self._abrir_atalho)
        layout.addWidget(self._atalhos)

        cabecalho_feito = QLabel("Feito para você")
        cabecalho_feito.setObjectName("tituloSecao")
        layout.addWidget(cabecalho_feito)

        self._em_alta = self._criar_prateleira(116)
        self._em_alta.itemActivated.connect(self._tocar_item)
        layout.addWidget(self._em_alta)

        cabecalho_voltar = QLabel("Vale ouvir de novo")
        cabecalho_voltar.setObjectName("tituloSecao")
        layout.addWidget(cabecalho_voltar)

        self._redescobertas = self._criar_prateleira(116)
        self._redescobertas.itemActivated.connect(self._tocar_item)
        layout.addWidget(self._redescobertas)

        botao_caos = QPushButton("Surpreenda-me com o Caos")
        botao_caos.setObjectName("botaoAccent")
        botao_caos.setFixedWidth(210)
        botao_caos.clicked.connect(self._ao_iniciar_caos)
        layout.addWidget(botao_caos)
        layout.addStretch()

        scroll.setWidget(corpo)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(scroll)

    @staticmethod
    def _saudacao():
        hora = datetime.now().hour
        if hora < 12:
            return "Bom dia"
        if hora < 18:
            return "Boa tarde"
        return "Boa noite"

    @staticmethod
    def _criar_prateleira(altura):
        lista = QListWidget()
        lista.setObjectName("prateleira")
        lista.setFlow(QListView.LeftToRight)
        lista.setWrapping(True)
        lista.setResizeMode(QListView.Adjust)
        lista.setMovement(QListView.Static)
        lista.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lista.setFixedHeight(altura)
        lista.setGridSize(QSize(224, max(56, altura - 8)))
        return lista

    def _preencher_atalhos(self):
        self._atalhos.clear()
        especiais = [
            (playlists_mod.NOME_PLAYLIST_CURTIDAS, "♥  Músicas Curtidas"),
            (playlists_mod.NOME_PLAYLIST_NAO_CURTIDAS, "⊘  Não Curtidas"),
        ]
        nomes = {nome for nome, _rotulo in especiais}
        entradas = especiais + [
            (pl["nome"], f"♫  {pl['nome']}")
            for pl in playlists_mod.listar()
            if pl["nome"] not in nomes
        ][:4]
        for nome, rotulo in entradas:
            item = QListWidgetItem(rotulo)
            item.setData(Qt.UserRole, {"tipo": "playlist", "nome": nome})
            self._atalhos.addItem(item)

    def _abrir_atalho(self, item):
        dado = item.data(Qt.UserRole)
        if dado:
            self._ao_abrir_playlist(dado["nome"])

    def _tocar_item(self, item):
        faixa = item.data(Qt.UserRole)
        if faixa:
            self._ao_tocar(faixa["titulo"], faixa["artista"], origem="descoberta")

    @staticmethod
    def _mostrar(lista, faixas, vazio):
        lista.clear()
        if not faixas:
            item = QListWidgetItem(vazio)
            item.setFlags(Qt.NoItemFlags)
            lista.addItem(item)
            return
        for faixa in faixas[:8]:
            item = QListWidgetItem(f"{faixa['titulo']}\n{faixa['artista']}")
            item.setData(Qt.UserRole, faixa)
            lista.addItem(item)

    def atualizar(self):
        self._preencher_atalhos()
        if self._worker is not None and self._worker.isRunning():
            return
        if self._carregado:
            return
        if not self._carregado:
            self._mostrar(self._em_alta, [], "Buscando novidades no ECHO…")
            self._mostrar(self._redescobertas, [], "Revisitando seu histórico…")
        worker = _CarregarInicioWorker(self)
        worker.concluido.connect(lambda em_alta, antigas, w=worker: self._concluir(w, em_alta, antigas))
        worker.finished.connect(lambda w=worker: self._finalizar(w))
        self._worker = worker
        worker.start()

    def atualizar_biblioteca(self):
        """Atualiza apenas os atalhos locais, sem refazer chamadas ao ECHO."""
        self._preencher_atalhos()

    def _concluir(self, worker, em_alta, redescobertas):
        if worker is not self._worker:
            return
        self._carregado = True
        self._mostrar(self._em_alta, em_alta, "ECHO offline — suas playlists continuam disponíveis.")
        self._mostrar(self._redescobertas, redescobertas, "Ainda não há músicas para redescobrir.")

    def _finalizar(self, worker):
        if worker is self._worker:
            self._worker = None
        worker.deleteLater()
