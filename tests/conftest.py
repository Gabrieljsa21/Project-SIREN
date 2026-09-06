# -*- coding: utf-8 -*-
"""Redireciona os arquivos de persistência do SIREN pra um diretório
temporário em TODO teste - mesmo padrão do Project-ECHO (tests/conftest.py) -
sem isso, os testes leriam/escreveriam em cima de `data/` de verdade."""
import pytest

from siren.core import favoritos as favoritos_mod
from siren.core import historico_local as historico_mod
from siren.core import playlists as playlists_mod
from siren.core import config as config_mod
from siren.core import downloads as downloads_mod


@pytest.fixture(autouse=True)
def isolar_persistencia(tmp_path, monkeypatch):
    monkeypatch.setattr(favoritos_mod, "ARQUIVO_FAVORITOS", str(tmp_path / "favoritos.json"))
    monkeypatch.setattr(historico_mod, "ARQUIVO_HISTORICO", str(tmp_path / "historico_local.json"))
    monkeypatch.setattr(playlists_mod, "ARQUIVO_PLAYLISTS", str(tmp_path / "playlists.json"))
    monkeypatch.setattr(config_mod, "ARQUIVO_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.setattr(downloads_mod, "ARQUIVO_MANIFESTO", str(tmp_path / "downloads.json"))
    yield
