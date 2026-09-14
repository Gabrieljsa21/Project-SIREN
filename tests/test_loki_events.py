import json

from siren.integrations.loki_events import PublicadorPlayback


class _Socket:
    pacotes = []

    def __init__(self, *_args):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def sendto(self, dados, destino):
        self.pacotes.append((json.loads(dados), destino))


def test_eventos_tem_sessao_faixa_e_sequencia():
    _Socket.pacotes.clear()
    publicador = PublicadorPlayback(porta=9999, socket_factory=_Socket)
    inicio = publicador.faixa_iniciada("Música", "Artista", "busca", 120)
    assert inicio["schema"] == "siren.playback.v1"
    assert inicio["track_id"]
    assert inicio["track"]["origem"] == "busca"
    assert publicador.progresso(1.2, 120)["sequence"] == 2
    assert publicador.progresso(1.8, 120) is None
    assert publicador.pausa_alterada(True)["type"] == "playback_paused"
    fim = publicador.faixa_encerrada("fim")
    assert fim["type"] == "track_ended"
    assert [evento[0]["sequence"] for evento in _Socket.pacotes] == [1, 2, 3, 4]
