# -*- coding: utf-8 -*-
"""★ Favoritos do SIREN (PLANO_SIREN.md, seção 4) - guardar uma música pra
achar de novo facilmente. Sinal de CONVENIÊNCIA do player, nunca chega no
ECHO e nunca ajusta peso nenhum de perfil musical - isso é o ❤️/👎
(`integrations/echo_client.py`), coisa BEM diferente de propósito."""
import os
import json

ARQUIVO_FAVORITOS = "data/favoritos.json"


def _track_id(titulo, artista):
    return f"{artista.strip().lower()}::{titulo.strip().lower()}"


def carregar():
    if not os.path.exists(ARQUIVO_FAVORITOS):
        return []
    try:
        with open(ARQUIVO_FAVORITOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _salvar(favoritos):
    os.makedirs(os.path.dirname(ARQUIVO_FAVORITOS), exist_ok=True)
    with open(ARQUIVO_FAVORITOS, "w", encoding="utf-8") as f:
        json.dump(favoritos, f, ensure_ascii=False, indent=2)


def esta_favoritada(titulo, artista):
    alvo = _track_id(titulo, artista)
    return any(f["id"] == alvo for f in carregar())


def favoritar(titulo, artista):
    favoritos = carregar()
    alvo = _track_id(titulo, artista)
    if not any(f["id"] == alvo for f in favoritos):
        favoritos.append({"id": alvo, "titulo": titulo, "artista": artista})
        _salvar(favoritos)
    return favoritos


def desfavoritar(titulo, artista):
    favoritos = carregar()
    alvo = _track_id(titulo, artista)
    restantes = [f for f in favoritos if f["id"] != alvo]
    if len(restantes) != len(favoritos):
        _salvar(restantes)
    return restantes


def alternar(titulo, artista):
    """Devolve o novo estado (`True` = favoritada agora, `False` =
    desfavoritada agora) - usado pelo clique do botão ★, que não sabe de
    antemão qual era o estado anterior."""
    if esta_favoritada(titulo, artista):
        desfavoritar(titulo, artista)
        return False
    favoritar(titulo, artista)
    return True
