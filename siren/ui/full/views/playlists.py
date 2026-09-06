# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from siren.core import importador_texto
from siren.core import playlists as playlists_mod
from siren.ui.full.import_worker import ImportYoutubeWorker
from siren.ui.full.widgets import PainelAcoesFaixa


class ViewPlaylists(QWidget):
    def __init__(self, ao_tocar, fila=None):
        super().__init__()
        self._ao_tocar = ao_tocar
        self._playlist_atual = None
        self._worker_importacao = None

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
        botao_importar_youtube = QPushButton("Importar do YouTube")
        botao_importar_youtube.setObjectName("botaoSecundario")
        botao_importar_youtube.clicked.connect(self._importar_do_youtube)
        botao_importar_texto = QPushButton("Colar playlist (texto)")
        botao_importar_texto.setObjectName("botaoSecundario")
        botao_importar_texto.clicked.connect(self._importar_de_texto)
        linha_topo.addWidget(botao_nova)
        linha_topo.addWidget(botao_importar_youtube)
        linha_topo.addWidget(botao_importar_texto)
        linha_topo.addStretch()
        self._label_status_importacao = QLabel("")
        self._label_status_importacao.setObjectName("legendaView")

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
        layout.addWidget(self._label_status_importacao)
        layout.addWidget(self._pilha, stretch=1)

    def _criar_playlist(self):
        nome, ok = QInputDialog.getText(self, "Nova playlist", "Nome:")
        if ok and nome.strip():
            playlists_mod.criar(nome.strip())
            self.atualizar()

    def _importar_do_youtube(self):
        nome, ok = QInputDialog.getText(self, "Importar do YouTube", "Nome da nova playlist:")
        if not (ok and nome.strip()):
            return
        url, ok = QInputDialog.getText(self, "Importar do YouTube", "URL da playlist do YouTube:")
        if not (ok and url.strip()):
            return

        nome = nome.strip()
        self._label_status_importacao.setText(f"Importando \"{url.strip()}\"...")
        self._worker_importacao = ImportYoutubeWorker(url.strip(), parent=self)
        self._worker_importacao.concluido.connect(lambda faixas: self._ao_concluir_importacao(nome, faixas))
        self._worker_importacao.start()

    def _importar_de_texto(self):
        nome, ok = QInputDialog.getText(self, "Colar playlist", "Nome da nova playlist:")
        if not (ok and nome.strip()):
            return
        texto, ok = QInputDialog.getMultiLineText(
            self, "Colar playlist",
            "Uma faixa por linha, no formato \"Artista - Título\" (ex.: copiado do Spotify):",
        )
        if not (ok and texto.strip()):
            return

        faixas = importador_texto.parsear_texto(texto)
        self._ao_concluir_importacao(nome.strip(), faixas)

    def _ao_concluir_importacao(self, nome, faixas):
        if not faixas:
            self._label_status_importacao.setText("Não consegui importar nenhuma faixa - confira a URL/o texto.")
            return
        playlists_mod.criar(nome)
        for faixa in faixas:
            playlists_mod.adicionar_faixa(nome, faixa["titulo"], faixa["artista"])
        self._label_status_importacao.setText(f"\"{nome}\" criada com {len(faixas)} faixa(s).")
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
