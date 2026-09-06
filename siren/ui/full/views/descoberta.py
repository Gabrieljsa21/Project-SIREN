# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from siren.integrations import echo_client


class ViewDescoberta(QWidget):
    """Camada de inteligência do ECHO - some sozinha (sem travar o resto do
    SIREN) quando ele está fora do ar, cada lista só fica vazia com um
    aviso (PLANO_SIREN.md, seção 2)."""

    def __init__(self, ao_tocar):
        super().__init__()
        self._ao_tocar = ao_tocar

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(10)

        titulo = QLabel("Descoberta")
        titulo.setObjectName("tituloView")
        legenda = QLabel("Caos, Em Alta e Redescobertas do ECHO - sem ele no ar, fica vazio, sem travar o resto do SIREN.")
        legenda.setObjectName("legendaView")
        legenda.setWordWrap(True)

        botao_caos = QPushButton("🎲 Caos")
        botao_caos.setObjectName("botaoAccent")
        botao_caos.setFixedWidth(140)
        botao_caos.clicked.connect(self._pedir_caos)

        rotulo_em_alta = QLabel("Em Alta")
        rotulo_em_alta.setStyleSheet("font-weight: 700; margin-top: 8px;")
        self._lista_em_alta = QListWidget()
        self._lista_em_alta.itemActivated.connect(self._tocar_item)

        rotulo_redescobertas = QLabel("Redescobertas")
        rotulo_redescobertas.setStyleSheet("font-weight: 700; margin-top: 8px;")
        self._lista_redescobertas = QListWidget()
        self._lista_redescobertas.itemActivated.connect(self._tocar_item)

        layout.addWidget(titulo)
        layout.addWidget(legenda)
        layout.addWidget(botao_caos)
        layout.addWidget(rotulo_em_alta)
        layout.addWidget(self._lista_em_alta, stretch=1)
        layout.addWidget(rotulo_redescobertas)
        layout.addWidget(self._lista_redescobertas, stretch=1)

    def _pedir_caos(self):
        faixa = echo_client.sugerir_semente()
        if faixa:
            self._ao_tocar(faixa["titulo"], faixa["artista"], origem="caos")

    def _tocar_item(self, item):
        faixa = item.data(Qt.UserRole)
        if faixa:
            self._ao_tocar(faixa["titulo"], faixa["artista"], origem="descoberta")

    def atualizar(self):
        self._preencher(self._lista_em_alta, echo_client.obter_em_alta())
        self._preencher(self._lista_redescobertas, echo_client.obter_redescobertas())

    def _preencher(self, lista, faixas):
        lista.clear()
        if not faixas:
            item = QListWidgetItem("ECHO indisponível ou sem sugestão agora")
            item.setFlags(Qt.NoItemFlags)
            lista.addItem(item)
            return
        for faixa in faixas:
            item = QListWidgetItem(f"{faixa['titulo']} - {faixa['artista']}")
            item.setData(Qt.UserRole, faixa)
            lista.addItem(item)
