# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from siren.integrations import echo_client


class _CarregarDescobertaWorker(QThread):
    """`echo_client.obter_em_alta`/`obter_redescobertas` são chamadas de rede
    de verdade (até 15s de timeout cada) - achado do usuário (2026-09-06):
    "porque está demorando pra entrar na página Descoberta... entrando,
    saindo e entrando de novo também demora". Rodar na GUI thread (como era
    antes) travava a janela inteira TODA VEZ que a view era mostrada, não só
    na 1ª. Ver também o cache adicionado no Project-ECHO
    (`echo/providers/lastfm.py`) pro outro lado real do problema: sem
    cache, `/em_alta` resolvia o gênero de até 50 artistas com 1 chamada
    HTTP CADA, sempre do zero."""
    concluido = Signal(list, list)  # em_alta, redescobertas

    def run(self):
        self.concluido.emit(echo_client.obter_em_alta(), echo_client.obter_redescobertas())


class ViewDescoberta(QWidget):
    """Camada de inteligência do ECHO - some sozinha (sem travar o resto do
    SIREN) quando ele está fora do ar, cada lista só fica vazia com um
    aviso (docs/PLANO_SIREN.md, seção 2)."""

    def __init__(self, ao_tocar):
        super().__init__()
        self._ao_tocar = ao_tocar
        self._worker = None
        self._tem_dados = False  # 1ª carga mostra "Carregando...", as próximas atualizam em silêncio (ver atualizar())

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
        # 🔥 Achado do usuário (2026-09-06): "por que precisa carregar toda
        # vez que clico em Descoberta?" - antes, TODA entrada na view limpava
        # as 2 listas e mostrava "Carregando..." de novo, mesmo o ECHO já
        # tendo cache (10min, ver `echo/providers/lastfm.py`) e os dados
        # quase certamente não tendo mudado desde a última vez. Só a 1ª
        # carga de verdade mostra "Carregando..." - as próximas mantêm o que
        # já estava na tela (sem piscar/limpar) e só trocam o conteúdo
        # quando a resposta nova chega, atualização silenciosa em segundo
        # plano.
        if not self._tem_dados:
            self._mostrar_carregando(self._lista_em_alta)
            self._mostrar_carregando(self._lista_redescobertas)
        worker = _CarregarDescobertaWorker(self)
        worker.concluido.connect(lambda em_alta, redescobertas, w=worker: self._ao_carregar(w, em_alta, redescobertas))
        self._worker = worker
        worker.start()

    def _ao_carregar(self, worker, em_alta, redescobertas):
        # Descarta resultado de uma chamada antiga se a view já pediu outra
        # `atualizar()` no meio do caminho (ex.: usuário saiu e voltou rápido).
        if worker is not self._worker:
            return
        self._tem_dados = True
        self._preencher(self._lista_em_alta, em_alta)
        self._preencher(self._lista_redescobertas, redescobertas)

    def _mostrar_carregando(self, lista):
        lista.clear()
        item = QListWidgetItem("Carregando...")
        item.setFlags(Qt.NoItemFlags)
        lista.addItem(item)

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
