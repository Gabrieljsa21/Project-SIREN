# -*- coding: utf-8 -*-
"""Tela do artista (2026-09-26, pedido do usuário: "o nome do artista tem
que ser clicável, pra ir pra tela dele, igual no Spotify").

- Cabeçalho: nome, nota do artista no ECHO (regra das 5 chances, ver
  `Project-ECHO/echo/core/artistas.py`) e o estado dele (normal, em prova,
  rejeitado).
- "Populares": as faixas mais ouvidas do artista no Last.fm, via ECHO
  (`/artista`). Sem ECHO, a seção avisa e o resto da tela continua.
- "Suas curtidas": faixas desse artista na playlist Músicas Curtidas (local,
  funciona sem ECHO).

Cada linha tem curtir, não curtir e adicionar à fila; duplo clique toca."""
from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPushButton, QScrollArea,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from siren.core import playlists as playlists_mod
from siren.integrations import echo_client
from siren.ui.full import arte, icones, styles
from siren.ui.full import faixas as faixas_ui

LADO_CAPA_ARTISTA = 168
LARGURA_ALBUM = 220
LARGURA_DURACAO = 80
LARGURA_ACOES = 110
DESCRICAO_ESTADO = {
    "em_prova": "Em prova: o ECHO está testando as músicas mais populares dele antes de decidir se continua recomendando.",
    "rejeitado": "Rejeitado: o ECHO não recomenda mais este artista. Curtir uma música dele o traz de volta.",
}


class _CarregarArtistaWorker(QThread):
    concluido = Signal(str, object)

    def __init__(self, nome, parent=None):
        super().__init__(parent)
        self._nome = nome

    def run(self):
        self.concluido.emit(self._nome, echo_client.obter_artista(self._nome))


def _id(faixa):
    return f"{faixa['artista'].strip().lower()}::{faixa['titulo'].strip().lower()}"


class _TabelaFaixas(QTableWidget):
    """Tabela sem rolagem própria (a tela inteira rola): #, Título, Álbum,
    Duração e ações."""

    COLUNAS = ["numero", "titulo", "album", "duracao", "acoes"]

    def __init__(self, ao_tocar, ao_votar, ao_enfileirar):
        super().__init__()
        self._ao_tocar = ao_tocar
        self._ao_votar = ao_votar
        self._ao_enfileirar = ao_enfileirar
        self._faixas = []
        self._votos = {}
        self.setObjectName("tabelaFaixas")
        self.setColumnCount(len(self.COLUNAS))
        self.setHorizontalHeaderLabels(["#", "Título", "Álbum", "Duração", ""])
        self.horizontalHeaderItem(3).setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(faixas_ui.ALTURA_LINHA)
        cabecalho = self.horizontalHeader()
        cabecalho.setHighlightSections(False)
        cabecalho.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        for indice in range(len(self.COLUNAS)):
            cabecalho.setSectionResizeMode(indice, QHeaderView.Fixed)
        self.cellDoubleClicked.connect(self._tocar_linha)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._ajustar_larguras()

    def _ajustar_larguras(self):
        fixas = {0: 44, 2: LARGURA_ALBUM, 3: LARGURA_DURACAO, 4: LARGURA_ACOES}
        for indice, largura in fixas.items():
            self.setColumnWidth(indice, largura)
        self.setColumnWidth(1, max(faixas_ui.LARGURA_MINIMA_TITULO, self.viewport().width() - sum(fixas.values())))

    def mostrar(self, faixas, votos):
        self._faixas = list(faixas)
        self._votos = votos
        self.clearContents()
        self.setRowCount(len(self._faixas))
        cor_fraca = QColor(styles.COR_TEXTO_FRACO)
        for linha, faixa in enumerate(self._faixas):
            voto = votos.get(_id(faixa))
            numero = QTableWidgetItem(str(linha + 1))
            numero.setTextAlignment(Qt.AlignCenter)
            numero.setForeground(cor_fraca)
            self.setItem(linha, 0, numero)
            self.setItem(linha, 1, QTableWidgetItem(""))
            self.setCellWidget(linha, 1, faixas_ui.CelulaTitulo(faixa, pulada=voto == "negativo"))
            album = QTableWidgetItem(faixas_ui.texto_album(faixa))
            album.setForeground(cor_fraca)
            self.setItem(linha, 2, album)
            duracao = QTableWidgetItem(faixas_ui.texto_duracao(faixa))
            duracao.setForeground(cor_fraca)
            duracao.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(linha, 3, duracao)
            self.setItem(linha, 4, QTableWidgetItem(""))
            self.setCellWidget(linha, 4, self._celula_acoes(faixa, voto))
        altura = self.horizontalHeader().height() + faixas_ui.ALTURA_LINHA * len(self._faixas) + 18
        self.setFixedHeight(altura)
        self._ajustar_larguras()

    def _celula_acoes(self, faixa, voto):
        celula = QWidget()
        layout = QHBoxLayout(celula)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(2)
        layout.addStretch()
        for botao in faixas_ui.botoes_voto(voto, lambda v, f=faixa: self._votar(f, v)):
            layout.addWidget(botao)
        enfileirar = faixas_ui.botao_acao("mais", "Adicionar à fila")
        enfileirar.clicked.connect(lambda _=False, f=faixa: self._ao_enfileirar(f))
        layout.addWidget(enfileirar)
        return celula

    def _votar(self, faixa, voto):
        if self._votos.get(_id(faixa)) != voto:
            self._votos[_id(faixa)] = voto
            self._ao_votar(faixa, voto == "positivo")
        self.mostrar(self._faixas, self._votos)

    def _tocar_linha(self, linha, _coluna):
        if 0 <= linha < len(self._faixas):
            self._ao_tocar(self._faixas[linha])

    def atualizar_info(self, titulo, artista):
        for linha, faixa in enumerate(self._faixas):
            if faixa["titulo"] == titulo and faixa["artista"] == artista:
                self.item(linha, 2).setText(faixas_ui.texto_album(faixa))
                self.item(linha, 3).setText(faixas_ui.texto_duracao(faixa))


class ViewArtista(QWidget):
    def __init__(self, ao_tocar, ao_tocar_lista, ao_votar, ao_enfileirar):
        """`ao_tocar(titulo, artista, origem)`, `ao_tocar_lista(faixas,
        origem)`, `ao_votar(faixa, positivo)`, `ao_enfileirar(faixa, origem)`
        - todos da janela principal."""
        super().__init__()
        self._ao_tocar = ao_tocar
        self._ao_tocar_lista = ao_tocar_lista
        self._ao_votar = ao_votar
        self._ao_enfileirar = ao_enfileirar
        self._nome = ""
        self._populares = []
        self._worker = None
        self._worker_info = None

        self._capa = QLabel()
        self._capa.setFixedSize(LADO_CAPA_ARTISTA, LADO_CAPA_ARTISTA)
        sobrelinha = QLabel("ARTISTA")
        sobrelinha.setObjectName("rotuloSobrelinha")
        self._rotulo_nome = QLabel("")
        self._rotulo_nome.setObjectName("tituloArtista")
        self._rotulo_nota = QLabel("")
        self._rotulo_nota.setObjectName("subtituloSecao")
        self._rotulo_estado = QLabel("")
        self._rotulo_estado.setObjectName("avisoEstadoArtista")
        self._rotulo_estado.setWordWrap(True)

        self._botao_tocar = QPushButton()
        self._botao_tocar.setObjectName("botaoPlay")
        self._botao_tocar.setFixedSize(52, 52)
        self._botao_tocar.setIcon(icones.icone("play", "#ffffff", 20))
        self._botao_tocar.setIconSize(QSize(20, 20))
        self._botao_tocar.setCursor(Qt.PointingHandCursor)
        self._botao_tocar.setToolTip("Tocar as populares")
        self._botao_tocar.clicked.connect(self._tocar_populares)

        textos = QVBoxLayout()
        textos.setSpacing(4)
        textos.addStretch()
        textos.addWidget(sobrelinha)
        textos.addWidget(self._rotulo_nome)
        textos.addWidget(self._rotulo_nota)
        textos.addWidget(self._rotulo_estado)
        textos.addStretch()

        cabecalho = QHBoxLayout()
        cabecalho.setSpacing(24)
        cabecalho.addWidget(self._capa)
        cabecalho.addLayout(textos, stretch=1)
        cabecalho.addWidget(self._botao_tocar, alignment=Qt.AlignBottom)

        titulo_populares = QLabel("Populares")
        titulo_populares.setObjectName("tituloSecao")
        self._aviso_populares = QLabel("")
        self._aviso_populares.setObjectName("subtituloSecao")
        self._tabela_populares = _TabelaFaixas(self._tocar_popular, self._ao_votar, self._enfileirar)

        titulo_curtidas = QLabel("Suas curtidas")
        titulo_curtidas.setObjectName("tituloSecao")
        self._aviso_curtidas = QLabel("")
        self._aviso_curtidas.setObjectName("subtituloSecao")
        self._tabela_curtidas = _TabelaFaixas(self._tocar_curtida, self._ao_votar, self._enfileirar)

        corpo = QWidget()
        layout = QVBoxLayout(corpo)
        layout.setContentsMargins(32, 24, 32, 28)
        layout.setSpacing(10)
        layout.addLayout(cabecalho)
        layout.addSpacing(14)
        for widget in (titulo_populares, self._aviso_populares, self._tabela_populares,
                       titulo_curtidas, self._aviso_curtidas, self._tabela_curtidas):
            layout.addWidget(widget)
        layout.addStretch()

        rolagem = QScrollArea()
        rolagem.setWidgetResizable(True)
        rolagem.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        rolagem.setWidget(corpo)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(rolagem)

    # ---------------- abrir ----------------

    def abrir(self, nome):
        self._nome = nome
        self._populares = []
        self._capa.setPixmap(arte.capa_arredondada("generico", LADO_CAPA_ARTISTA, 16, f"artista::{nome.lower()}"))
        self._rotulo_nome.setText(nome)
        self._rotulo_nota.setText("Consultando o ECHO…")
        self._rotulo_estado.hide()
        self._aviso_populares.setText("Buscando as músicas mais ouvidas…")
        self._aviso_populares.show()
        self._tabela_populares.mostrar([], {})
        self._tabela_populares.hide()
        self._mostrar_curtidas()
        worker = _CarregarArtistaWorker(nome, self)
        worker.concluido.connect(self._ao_carregar)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def atualizar(self):
        """Chamado ao voltar pra tela (`_mudar_view`) - só refaz o que é
        local, sem reconsultar o ECHO."""
        if self._nome:
            self._mostrar_curtidas()

    def _votos_locais(self):
        votos = {}
        for faixa in playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_CURTIDAS):
            votos[_id(faixa)] = "positivo"
        for faixa in playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_NAO_CURTIDAS):
            votos[_id(faixa)] = "negativo"
        return votos

    def _mostrar_curtidas(self):
        nome = self._nome.strip().lower()
        curtidas = [
            f for f in playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_CURTIDAS)
            if f["artista"].strip().lower() == nome
        ]
        self._tabela_curtidas.mostrar(curtidas, self._votos_locais())
        self._tabela_curtidas.setVisible(bool(curtidas))
        self._aviso_curtidas.setText(
            f"{len(curtidas)} música{'s' if len(curtidas) != 1 else ''} dele em Músicas Curtidas." if curtidas
            else "Você ainda não curtiu nenhuma música deste artista."
        )
        self._buscar_infos(curtidas)

    def _ao_carregar(self, nome, dados):
        if nome != self._nome:
            return  # abriu outro artista enquanto este carregava
        if not dados:
            self._rotulo_nota.setText("ECHO offline: sem nota nem populares agora.")
            self._aviso_populares.setText("As populares vêm do ECHO, que não respondeu.")
            return
        self._rotulo_nome.setText(dados.get("nome") or nome)
        nota = dados.get("nota") or 0.0
        curtidas = dados.get("curtidas", 0)
        descurtidas = dados.get("descurtidas", 0)
        self._rotulo_nota.setText(
            f"Sua nota no ECHO: {nota:+.2f}".replace(".", ",")
            + f"  ·  {curtidas} curtida{'s' if curtidas != 1 else ''}"
            + f"  ·  {descurtidas} não curtida{'s' if descurtidas != 1 else ''}"
        )
        estado = DESCRICAO_ESTADO.get(dados.get("estado"))
        self._rotulo_estado.setText(estado or "")
        self._rotulo_estado.setVisible(bool(estado))
        self._populares = dados.get("populares") or []
        if not self._populares:
            self._aviso_populares.setText("O Last.fm não trouxe músicas populares deste artista.")
            return
        self._aviso_populares.hide()
        self._tabela_populares.mostrar(self._populares, self._votos_locais())
        self._tabela_populares.show()
        self._buscar_infos(self._populares)

    # ---------------- álbum/duração ----------------

    def _buscar_infos(self, faixas):
        if self._worker_info is not None or not faixas:
            return
        worker = faixas_ui.InfoFaixasWorker(faixas, self)
        if not worker.tem_trabalho:
            worker.deleteLater()
            return
        worker.info_pronta.connect(self._aplicar_info)
        worker.finished.connect(lambda w=worker: self._fim_worker_info(w))
        self._worker_info = worker
        worker.start()

    def _fim_worker_info(self, worker):
        if worker is self._worker_info:
            self._worker_info = None
        worker.deleteLater()
        if worker.falhou:
            return  # ECHO fora do ar: não fica tentando em laço
        # Seção que chegou enquanto o worker anterior rodava ainda pode estar sem info.
        self._buscar_infos(self._populares + [
            f for f in playlists_mod.obter_faixas(playlists_mod.NOME_PLAYLIST_CURTIDAS)
            if f["artista"].strip().lower() == self._nome.strip().lower()
        ])

    def _aplicar_info(self, titulo, artista):
        self._tabela_populares.atualizar_info(titulo, artista)
        self._tabela_curtidas.atualizar_info(titulo, artista)

    # ---------------- ações ----------------

    def _origem(self):
        return f"artista:{self._nome}"

    def _tocar_popular(self, faixa):
        indice = self._populares.index(faixa) if faixa in self._populares else 0
        self._ao_tocar_lista(self._populares[indice:], self._origem())

    def _tocar_curtida(self, faixa):
        self._ao_tocar(faixa["titulo"], faixa["artista"], origem=self._origem())

    def _tocar_populares(self):
        if self._populares:
            self._ao_tocar_lista(self._populares, self._origem())

    def _enfileirar(self, faixa):
        self._ao_enfileirar(faixa, self._origem())
