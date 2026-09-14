from siren.playback.player import Player


class _MpvFalso:
    time_pos = None
    duration = None


def _player_sem_mpv_real():
    player = Player.__new__(Player)
    player._mpv = _MpvFalso()
    return player


def test_buscar_posicao_define_tempo_absoluto():
    player = _player_sem_mpv_real()
    player.buscar_posicao(42.5)
    assert player.posicao_segundos == 42.5


def test_buscar_posicao_nao_aceita_tempo_negativo():
    player = _player_sem_mpv_real()
    player.buscar_posicao(-10)
    assert player.posicao_segundos == 0.0


def test_duracao_segundos_reflete_mpv():
    player = _player_sem_mpv_real()
    player._mpv.duration = 185.2
    assert player.duracao_segundos == 185.2
