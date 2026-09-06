# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class ViewTocandoAgora(QWidget):
    """Mostra a faixa atual - os controles de transporte (play/pause/
    pular/voto) ficam na barra inferior, compartilhada com as outras telas;
    aqui só o destaque + atalho pro Caos."""

    def __init__(self, ao_iniciar_caos):
        super().__init__()
        self._ao_iniciar_caos = ao_iniciar_caos

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(14)

        titulo = QLabel("Tocando agora")
        titulo.setObjectName("tituloView")

        self._label_faixa = QLabel("Nenhuma faixa - clique em Caos")
        self._label_faixa.setStyleSheet("font-size: 22px; font-weight: 700;")
        self._label_artista = QLabel("")
        self._label_artista.setObjectName("legendaView")

        botao_caos = QPushButton("🎲 Caos")
        botao_caos.setObjectName("botaoAccent")
        botao_caos.setFixedWidth(140)
        botao_caos.clicked.connect(self._ao_iniciar_caos)

        layout.addWidget(titulo)
        layout.addWidget(self._label_faixa)
        layout.addWidget(self._label_artista)
        layout.addWidget(botao_caos)
        layout.addStretch()

    def atualizar(self):
        pass

    def definir_faixa_atual(self, titulo, artista):
        self._label_faixa.setText(titulo)
        self._label_artista.setText(artista)
