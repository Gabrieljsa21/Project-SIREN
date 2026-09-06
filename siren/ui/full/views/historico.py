# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from siren.core import historico_local as historico_mod


class ViewHistorico(QWidget):
    def __init__(self, ao_tocar):
        super().__init__()
        self._ao_tocar = ao_tocar

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(10)

        titulo = QLabel("Histórico")
        titulo.setObjectName("tituloView")
        legenda = QLabel("Guardado localmente pelo SIREN, independe do ECHO estar disponível.")
        legenda.setObjectName("legendaView")

        self._lista = QListWidget()
        self._lista.itemActivated.connect(self._tocar_item)

        layout.addWidget(titulo)
        layout.addWidget(legenda)
        layout.addWidget(self._lista, stretch=1)

    def _tocar_item(self, item):
        faixa = item.data(Qt.UserRole)
        self._ao_tocar(faixa["titulo"], faixa["artista"], origem="historico")

    def atualizar(self):
        self._lista.clear()
        recentes = historico_mod.obter_recentes(limite=50)
        if not recentes:
            item = QListWidgetItem("Nada tocado ainda.")
            item.setFlags(Qt.NoItemFlags)
            self._lista.addItem(item)
            return
        for entrada in recentes:
            texto = f"{entrada['titulo']} - {entrada['artista']} ({entrada['tocado_em']}, {entrada['origem']})"
            item = QListWidgetItem(texto)
            item.setData(Qt.UserRole, entrada)
            self._lista.addItem(item)
