import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from siren.ui.full.views import playlists as view_mod


class _SinalFalso:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in self.callbacks:
            callback(*args)


class _WorkerFalso:
    def __init__(self, url, parent=None):
        self.url = url
        self.parent = parent
        self.concluido = _SinalFalso()
        self.finished = _SinalFalso()
        self.rodando = False
        self.removido = False

    def start(self):
        self.rodando = True

    def isRunning(self):
        return self.rodando

    def deleteLater(self):
        self.removido = True


def test_importacao_youtube_bloqueia_segundo_clique_e_reabilita(monkeypatch):
    app = QApplication.instance() or QApplication([])
    respostas = iter([("Minha playlist", True), ("https://youtube.test/playlist", True)])
    monkeypatch.setattr(view_mod.QInputDialog, "getText", lambda *args, **kwargs: next(respostas))
    monkeypatch.setattr(view_mod, "ImportYoutubeWorker", _WorkerFalso)

    view = view_mod.ViewPlaylists(lambda *args, **kwargs: None)
    view._importar_do_youtube()
    worker = view._worker_importacao

    assert worker.isRunning()
    assert not view._botao_importar_youtube.isEnabled()

    view._importar_do_youtube()
    assert "já está sendo importada" in view._label_status_importacao.text()

    worker.rodando = False
    worker.finished.emit()
    assert view._worker_importacao is None
    assert view._botao_importar_youtube.isEnabled()
    assert worker.removido

    view.deleteLater()
    app.processEvents()


def test_linha_da_playlist_alterna_entre_os_tres_votos():
    QApplication.instance() or QApplication([])
    enviados = []
    faixa = {"titulo": "Doomsday", "artista": "MF DOOM"}
    linha = view_mod.LinhaFaixa(faixa, "positivo", lambda f, positivo: enviados.append(positivo))
    assert linha._curtir.isChecked() and not linha._nao_curtir.isChecked()

    linha._curtir.click()      # reclicar no ❤️ marcado tira o voto
    linha._nao_curtir.click()  # 👎
    linha._curtir.click()      # 👎 -> ❤️ direto
    assert enviados == [None, False, True]
    assert linha._curtir.isChecked() and not linha._nao_curtir.isChecked()


def test_duplo_clique_toca_a_playlist_a_partir_da_faixa(monkeypatch):
    QApplication.instance() or QApplication([])
    faixas = [{"titulo": f"Faixa {n}", "artista": "MF DOOM"} for n in range(4)]
    monkeypatch.setattr(view_mod.playlists_mod, "obter_faixas", lambda nome: faixas)
    tocadas = []
    view = view_mod.ViewPlaylists(ao_tocar=lambda *a, **k: None, ao_tocar_lista=lambda f, origem: tocadas.append((f, origem)))
    view.abrir("Treino")

    view._tocar_faixa_selecionada(view._lista_faixas.item(1))

    assert tocadas == [(faixas[1:], "playlist:Treino")]
