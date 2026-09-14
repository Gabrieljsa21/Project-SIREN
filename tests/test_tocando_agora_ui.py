import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from siren.ui.full.views import tocando_agora as view_mod


class _SinalFalso:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in self.callbacks:
            callback(*args)


class _WorkerFalso:
    def __init__(self, linhas, parent=None):
        self.linhas = linhas
        self.parent = parent
        self.concluido = _SinalFalso()
        self.finished = _SinalFalso()
        self.rodando = False

    def start(self):
        self.rodando = True

    def isRunning(self):
        return self.rodando

    def deleteLater(self):
        pass


class _PlayerFalso:
    posicao_segundos = 0


def test_traducao_roda_em_worker_e_descarta_resultado_de_faixa_antiga(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(view_mod, "_TraduzirWorker", _WorkerFalso)
    monkeypatch.setattr(view_mod.traducao_mod, "traducao_disponivel", lambda: True)

    view = view_mod.ViewTocandoAgora(lambda: None, _PlayerFalso())
    view._linhas_letra = [{"tempo_segundos": 0, "texto": "Old"}]
    view._lista_letras.addItem("Old")
    view._traduzir()
    worker_antigo = view._worker_traducao

    assert worker_antigo.isRunning()
    assert not view._botao_traduzir.isEnabled()
    assert view._botao_traduzir.text() == "Traduzindo..."

    monkeypatch.setattr(view, "_carregar_letra", lambda *_args: setattr(view, "_worker_traducao", None))
    view.definir_faixa_atual("Nova", "Artista")
    worker_antigo.concluido.emit([{"tempo_segundos": 0, "texto": "Old", "traducao": "Antiga"}])
    assert view._lista_letras.item(0).text() == "Old"

    view.deleteLater()
    app.processEvents()
