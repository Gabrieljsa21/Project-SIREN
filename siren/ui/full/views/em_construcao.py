# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ViewEmConstrucao(QWidget):
    """Placeholder honesto - melhor entregar o resto funcionando do que
    atrasar tudo esperando ficar completo de uma vez (ver TODO.md)."""

    def __init__(self, nome):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        titulo = QLabel(nome)
        titulo.setObjectName("tituloView")
        legenda = QLabel("Ainda em construção - ver TODO.md do Project-SIREN.")
        legenda.setObjectName("legendaView")
        layout.addWidget(titulo)
        layout.addWidget(legenda)
        layout.addStretch()

    def atualizar(self):
        pass
