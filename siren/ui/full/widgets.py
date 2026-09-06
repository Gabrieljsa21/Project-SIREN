# -*- coding: utf-8 -*-
"""Widgets pequenos reaproveitados entre views do Modo Completo - evita
repetir a mesma wiring de "baixar"/"enfileirar a faixa selecionada" em
Playlists, Favoritos e Histórico (DRY)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from siren.core import downloads as downloads_mod
from siren.ui.full.download_worker import DownloadWorker


class PainelAcoesFaixa(QWidget):
    """Barra de ações sobre o item atualmente selecionado de uma
    `QListWidget` (`item.data(Qt.UserRole)` precisa ser um dict com
    "titulo"/"artista"): tocar a seguir, adicionar ao final da fila, baixar
    pra ouvir offline. `fila`: instância compartilhada de `core.fila.Fila`
    (a mesma que a `ViewFila` lê) - `None` esconde os 2 botões de fila
    (não faz sentido, por exemplo, numa lista que ainda não tem conceito de
    origem, mas hoje todo chamador passa uma)."""

    def __init__(self, lista, fila=None, origem_padrao="fila", parent=None):
        super().__init__(parent)
        self._lista = lista
        self._fila = fila
        self._origem_padrao = origem_padrao
        self._worker = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 0)

        if fila is not None:
            botao_tocar_a_seguir = QPushButton("▶ Tocar a seguir")
            botao_tocar_a_seguir.setObjectName("botaoSecundario")
            botao_tocar_a_seguir.clicked.connect(self._tocar_a_seguir)
            layout.addWidget(botao_tocar_a_seguir)

            botao_adicionar_fila = QPushButton("+ Adicionar à fila")
            botao_adicionar_fila.setObjectName("botaoSecundario")
            botao_adicionar_fila.clicked.connect(self._adicionar_a_fila)
            layout.addWidget(botao_adicionar_fila)

        self._botao_baixar = QPushButton("⬇ Baixar selecionada")
        self._botao_baixar.setObjectName("botaoSecundario")
        self._botao_baixar.clicked.connect(self._baixar)
        layout.addWidget(self._botao_baixar)

        self._label_status = QLabel("")
        self._label_status.setObjectName("legendaView")
        layout.addWidget(self._label_status)
        layout.addStretch()

    def definir_origem_padrao(self, origem):
        """Playlists reaproveitam o MESMO painel pra qualquer playlist
        aberta - a origem (`"playlist:<nome>"`) muda por playlist, então
        precisa ser atualizável depois da construção, não só no `__init__`."""
        self._origem_padrao = origem

    def _faixa_selecionada(self):
        item = self._lista.currentItem()
        if item is None:
            self._label_status.setText("Selecione uma faixa primeiro.")
            return None
        faixa = item.data(Qt.UserRole)
        if not faixa:
            self._label_status.setText("Selecione uma faixa primeiro.")
            return None
        return faixa

    def _tocar_a_seguir(self):
        faixa = self._faixa_selecionada()
        if faixa is None:
            return
        self._fila.adicionar_a_seguir(faixa["titulo"], faixa["artista"], origem=self._origem_padrao)
        self._label_status.setText(f"\"{faixa['titulo']}\" vai tocar a seguir.")

    def _adicionar_a_fila(self):
        faixa = self._faixa_selecionada()
        if faixa is None:
            return
        self._fila.adicionar(faixa["titulo"], faixa["artista"], origem=self._origem_padrao)
        self._label_status.setText(f"\"{faixa['titulo']}\" adicionada ao final da fila.")

    def _baixar(self):
        faixa = self._faixa_selecionada()
        if faixa is None:
            return
        titulo, artista = faixa["titulo"], faixa["artista"]
        if downloads_mod.esta_baixada(titulo, artista):
            self._label_status.setText("Essa faixa já está baixada.")
            return

        self._botao_baixar.setEnabled(False)
        self._label_status.setText(f"Baixando \"{titulo}\"...")
        self._worker = DownloadWorker(titulo, artista, parent=self)
        self._worker.concluido.connect(self._ao_concluir_download)
        self._worker.start()

    def _ao_concluir_download(self, sucesso):
        self._botao_baixar.setEnabled(True)
        self._label_status.setText("Baixada - disponível offline." if sucesso else "Não consegui baixar essa faixa.")
