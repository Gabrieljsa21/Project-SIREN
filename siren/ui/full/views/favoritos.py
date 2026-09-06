# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from siren.core import favoritos as favoritos_mod
from siren.core import importar_votos_echo
from siren.ui.full.import_worker import ImportEchoAprovadasWorker
from siren.ui.full.widgets import PainelAcoesFaixa


class ViewFavoritos(QWidget):
    def __init__(self, ao_tocar, fila=None):
        super().__init__()
        self._ao_tocar = ao_tocar
        self._worker_importacao_echo = None

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

        linha_importar = QHBoxLayout()
        botao_importar = QPushButton("Importar 👍 do ECHO (Discord)")
        botao_importar.setObjectName("botaoSecundario")
        botao_importar.clicked.connect(self._importar_do_echo)
        linha_importar.addWidget(botao_importar)
        self._label_status_importacao = QLabel("")
        self._label_status_importacao.setObjectName("legendaView")
        linha_importar.addWidget(self._label_status_importacao)
        linha_importar.addStretch()

        self._lista = QListWidget()
        self._lista.itemActivated.connect(self._tocar_item)

        layout.addWidget(titulo)
        layout.addWidget(legenda)
        layout.addLayout(linha_importar)
        layout.addWidget(self._lista, stretch=1)
        layout.addWidget(PainelAcoesFaixa(self._lista, fila=fila, origem_padrao="favoritos"))

    def _importar_do_echo(self):
        """Faixas com 👍 no ECHO - MESMO discord_user_id que o Modo Música
        do ERIS usa quando é o dono na call (2026-09-06, pedido do usuário:
        "não consegue já importar as músicas que gostei... enquanto ouvia
        pelo Discord?"). Vira ★ favorito + entra na playlist "Descobertas
        do SIREN" (core/importar_votos_echo.py) - idempotente, pode clicar
        de novo sem duplicar nada."""
        self._label_status_importacao.setText("Buscando aprovadas no ECHO...")
        self._worker_importacao_echo = ImportEchoAprovadasWorker(parent=self)
        self._worker_importacao_echo.concluido.connect(self._ao_concluir_importacao_echo)
        self._worker_importacao_echo.start()

    def _ao_concluir_importacao_echo(self, aprovadas):
        if not aprovadas:
            self._label_status_importacao.setText("ECHO indisponível ou sem nenhuma faixa aprovada ainda.")
            return
        novas = importar_votos_echo.importar_aprovadas(aprovadas)
        self._label_status_importacao.setText(f"{len(aprovadas)} aprovada(s) no ECHO, {novas} nova(s) favoritada(s).")
        self.atualizar()

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
