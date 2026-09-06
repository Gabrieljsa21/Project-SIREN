# -*- coding: utf-8 -*-
"""Thread compartilhada pra baixar faixa sem travar a janela -
`core/downloads.baixar` é bloqueante (chamada de rede real), reaproveitada
igual nas 3 views que oferecem baixar (Playlists, Favoritos, Histórico)."""
from PySide6.QtCore import QThread, Signal

from siren.core import downloads as downloads_mod


class DownloadWorker(QThread):
    concluido = Signal(bool)  # True = baixou com sucesso, False = falhou

    def __init__(self, titulo, artista, parent=None):
        super().__init__(parent)
        self._titulo = titulo
        self._artista = artista

    def run(self):
        caminho = downloads_mod.baixar(self._titulo, self._artista)
        self.concluido.emit(caminho is not None)
