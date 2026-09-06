# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from siren.core import playlists as playlists_mod
from siren.ui.full.widgets import PainelAcoesFaixa


class ViewPlaylists(QWidget):
    def __init__(self, ao_tocar, fila=None):
        super().__init__()
        self._ao_tocar = ao_tocar
        self._playlist_atual = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(10)

        titulo = QLabel("Playlists")
        titulo.setObjectName("tituloView")
        legenda = QLabel("Criadas por você, ou pelo SIREN a partir do que você aprova. Salvas localmente.")
        legenda.setObjectName("legendaView")

        linha_topo = QHBoxLayout()
        botao_nova = QPushButton("+ Nova playlist")
        botao_nova.setObjectName("botaoSecundario")
        botao_nova.clicked.connect(self._criar_playlist)
        linha_topo.addWidget(botao_nova)
        linha_topo.addStretch()

        self._pilha = QStackedWidget()

        self._lista_playlists = QListWidget()
        self._lista_playlists.itemActivated.connect(self._abrir_playlist)

        painel_detalhe = QWidget()
        layout_detalhe = QVBoxLayout(painel_detalhe)
        layout_detalhe.setContentsMargins(0, 0, 0, 0)
        botao_voltar = QPushButton("← todas as playlists")
        botao_voltar.setObjectName("botaoSecundario")
        botao_voltar.clicked.connect(lambda: self._pilha.setCurrentIndex(0))
        self._rotulo_playlist_atual = QLabel("")
        self._rotulo_playlist_atual.setStyleSheet("font-weight: 700; font-size: 16px; margin-top: 8px;")
        self._lista_faixas = QListWidget()
        self._lista_faixas.itemActivated.connect(self._tocar_faixa_selecionada)
        layout_detalhe.addWidget(botao_voltar)
        layout_detalhe.addWidget(self._rotulo_playlist_atual)
        layout_detalhe.addWidget(self._lista_faixas, stretch=1)
        self._painel_acoes = PainelAcoesFaixa(self._lista_faixas, fila=fila, origem_padrao="playlist")
        layout_detalhe.addWidget(self._painel_acoes)

        self._pilha.addWidget(self._lista_playlists)
        self._pilha.addWidget(painel_detalhe)

        layout.addWidget(titulo)
        layout.addWidget(legenda)
        layout.addLayout(linha_topo)
        layout.addWidget(self._pilha, stretch=1)

    def _criar_playlist(self):
        nome, ok = QInputDialog.getText(self, "Nova playlist", "Nome:")
        if ok and nome.strip():
            playlists_mod.criar(nome.strip())
            self.atualizar()

    def _abrir_playlist(self, item):
        nome = item.data(Qt.UserRole)
        self._playlist_atual = nome
        self._painel_acoes.definir_origem_padrao(f"playlist:{nome}")
        self._rotulo_playlist_atual.setText(nome)
        self._lista_faixas.clear()
        for faixa in playlists_mod.obter_faixas(nome):
            entrada = QListWidgetItem(f"{faixa['titulo']} - {faixa['artista']}")
            entrada.setData(Qt.UserRole, faixa)
            self._lista_faixas.addItem(entrada)
        self._pilha.setCurrentIndex(1)

    def _tocar_faixa_selecionada(self, item):
        faixa = item.data(Qt.UserRole)
        self._ao_tocar(faixa["titulo"], faixa["artista"], origem=f"playlist:{self._playlist_atual}")

    def atualizar(self):
        self._pilha.setCurrentIndex(0)
        self._lista_playlists.clear()
        playlists = playlists_mod.listar()
        if not playlists:
            item = QListWidgetItem("Nenhuma playlist ainda - crie uma acima.")
            item.setFlags(Qt.NoItemFlags)
            self._lista_playlists.addItem(item)
            return
        for pl in playlists:
            item = QListWidgetItem(f"{pl['nome']} ({pl['quantidade']} faixas)")
            item.setData(Qt.UserRole, pl["nome"])
            self._lista_playlists.addItem(item)
