# -*- coding: utf-8 -*-
"""Testa só a parte pura (manifesto) - `baixar()` faz chamada de rede de
verdade (yt-dlp), mesma convenção de `test_resolver.py` (não testar rede em
teste automatizado)."""
from siren.core import downloads as downloads_mod


def _fingir_arquivo_baixado(tmp_path, titulo, artista):
    arquivo = tmp_path / f"{artista} - {titulo}.webm"
    arquivo.write_bytes(b"conteudo falso")
    manifesto = downloads_mod._carregar_manifesto()
    manifesto[downloads_mod._track_id(titulo, artista)] = {
        "titulo": titulo, "artista": artista, "caminho": str(arquivo),
    }
    downloads_mod._salvar_manifesto(manifesto)
    return arquivo


def test_nao_baixada_por_padrao():
    assert not downloads_mod.esta_baixada("Doomsday", "MF DOOM")
    assert downloads_mod.obter_caminho_local("Doomsday", "MF DOOM") is None


def test_esta_baixada_quando_arquivo_existe(tmp_path):
    arquivo = _fingir_arquivo_baixado(tmp_path, "Doomsday", "MF DOOM")
    assert downloads_mod.esta_baixada("Doomsday", "MF DOOM")
    assert downloads_mod.obter_caminho_local("Doomsday", "MF DOOM") == str(arquivo)


def test_registro_orfao_nao_conta_como_baixada(tmp_path):
    """Registro no manifesto apontando pra um arquivo que não existe mais
    (usuário apagou por fora) - nunca finge que ainda tá baixada."""
    manifesto = {"mf doom::doomsday": {"titulo": "Doomsday", "artista": "MF DOOM", "caminho": str(tmp_path / "sumiu.webm")}}
    downloads_mod._salvar_manifesto(manifesto)
    assert not downloads_mod.esta_baixada("Doomsday", "MF DOOM")


def test_listar_baixadas(tmp_path):
    _fingir_arquivo_baixado(tmp_path, "Doomsday", "MF DOOM")
    assert len(downloads_mod.listar_baixadas()) == 1


def test_remover_apaga_arquivo_e_registro(tmp_path):
    arquivo = _fingir_arquivo_baixado(tmp_path, "Doomsday", "MF DOOM")
    downloads_mod.remover("Doomsday", "MF DOOM")
    assert not arquivo.exists()
    assert not downloads_mod.esta_baixada("Doomsday", "MF DOOM")
