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
