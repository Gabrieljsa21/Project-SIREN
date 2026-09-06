# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from siren.core import favoritos as favoritos_mod
from siren.ui.full.widgets import PainelAcoesFaixa


class ViewFavoritos(QWidget):
    def __init__(self, ao_tocar, fila=None):
        super().__init__()
        self._ao_tocar = ao_tocar

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(10)

        titulo = QLabel("Favoritos")
        titulo.setObjectName("tituloView")
        legenda = QLabel(
            "★ Favoritar guarda a música pra você achar de novo - é do SIREN, "
            "nunca chega no ECHO. ❤️ Aprovar (na barra de baixo) ensina o ECHO "
            "sobre o seu gosto - são coisas diferentes de propósito."
        )
        legenda.setObjectName("legendaView")
        legenda.setWordWrap(True)

        self._lista = QListWidget()
        self._lista.itemActivated.connect(self._tocar_item)

        layout.addWidget(titulo)
        layout.addWidget(legenda)
        layout.addWidget(self._lista, stretch=1)
        layout.addWidget(PainelAcoesFaixa(self._lista, fila=fila, origem_padrao="favoritos"))

    def _tocar_item(self, item):
        faixa = item.data(Qt.UserRole)
        self._ao_tocar(faixa["titulo"], faixa["artista"], origem="favoritos")

    def atualizar(self):
        self._lista.clear()
        favoritos = favoritos_mod.carregar()
        if not favoritos:
            item = QListWidgetItem("Nenhum favorito ainda - clique em ⭐ na barra de baixo.")
            item.setFlags(Qt.NoItemFlags)
            self._lista.addItem(item)
            return
        for faixa in favoritos:
            item = QListWidgetItem(f"★ {faixa['titulo']} - {faixa['artista']}")
            item.setData(Qt.UserRole, faixa)
            self._lista.addItem(item)
