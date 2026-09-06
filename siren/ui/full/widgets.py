# -*- coding: utf-8 -*-
"""Widgets pequenos reaproveitados entre views do Modo Completo - evita
repetir a mesma wiring de "baixar a faixa selecionada" em Playlists,
Favoritos e Histórico (DRY)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from siren.core import downloads as downloads_mod
from siren.ui.full.download_worker import DownloadWorker


class PainelBaixarSelecionada(QWidget):
    """Barra com um botão "⬇ Baixar selecionada" + status - opera sobre o
    item atualmente selecionado de uma `QListWidget` (`item.data(Qt.UserRole)`
    precisa ser um dict com "titulo"/"artista"). Baixa numa `DownloadWorker`
    própria, nunca trava a janela."""

    def __init__(self, lista, parent=None):
        super().__init__(parent)
        self._lista = lista
        self._worker = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 0)

        self._botao = QPushButton("⬇ Baixar selecionada")
        self._botao.setObjectName("botaoSecundario")
        self._botao.clicked.connect(self._baixar)

        self._label_status = QLabel("")
        self._label_status.setObjectName("legendaView")

        layout.addWidget(self._botao)
        layout.addWidget(self._label_status)
        layout.addStretch()

    def _baixar(self):
        item = self._lista.currentItem()
        if item is None:
            self._label_status.setText("Selecione uma faixa primeiro.")
            return
        faixa = item.data(Qt.UserRole)
        if not faixa:
            return
        titulo, artista = faixa["titulo"], faixa["artista"]
        if downloads_mod.esta_baixada(titulo, artista):
            self._label_status.setText("Essa faixa já está baixada.")
            return

        self._botao.setEnabled(False)
        self._label_status.setText(f"Baixando \"{titulo}\"...")
        self._worker = DownloadWorker(titulo, artista, parent=self)
        self._worker.concluido.connect(self._ao_concluir)
        self._worker.start()

    def _ao_concluir(self, sucesso):
        self._botao.setEnabled(True)
        self._label_status.setText("Baixada - disponível offline." if sucesso else "Não consegui baixar essa faixa.")
