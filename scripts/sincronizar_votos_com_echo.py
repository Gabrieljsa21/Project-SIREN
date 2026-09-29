# -*- coding: utf-8 -*-
"""Envia ao ECHO os votos que só existem no SIREN (uso único, 2026-09-26).

As playlists "Músicas Curtidas" e "Não Curtidas" do SIREN guardam votos que
o ECHO nunca recebeu: os favoritos (★) antigos, migrados só localmente, e o
que foi votado com o ECHO desligado. Sem eles, a nota de cada artista no
ECHO (regra das 5 chances) começa incompleta.

- Curtidas: vão como 👍 normais.
- Não Curtidas: vão como 👎 com `abrir_prova=False` - só reduzem a nota do
  artista, sem colocar dezenas de artistas em prova de uma vez (decisão do
  usuário).
- Faixas que o ECHO já conhece (qualquer voto) ficam de fora.

Uso, da raiz do repositório, com o ECHO rodando:

    .venv\\Scripts\\python.exe scripts\\sincronizar_votos_com_echo.py [--simular]
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from siren.core import playlists as playlists_mod  # noqa: E402
from siren.integrations import echo_client  # noqa: E402

PAUSA_ENTRE_VOTOS = 0.4  # cada voto consulta o gênero no Last.fm - evita esbarrar no limite de requisições


def _pendentes(nome_playlist):
    return [
        faixa for faixa in playlists_mod.obter_faixas(nome_playlist)
        if echo_client.obter_voto(faixa["artista"], faixa["titulo"]) is None
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--simular", action="store_true", help="só mostra o que seria enviado")
    argumentos = parser.parse_args()

    if not echo_client.esta_disponivel():
        print("ECHO fora do ar - inicie o ECHO e rode de novo.")
        return 1

    curtidas = _pendentes(playlists_mod.NOME_PLAYLIST_CURTIDAS)
    nao_curtidas = _pendentes(playlists_mod.NOME_PLAYLIST_NAO_CURTIDAS)
    print(f"Curtidas que o ECHO não conhece: {len(curtidas)}")
    print(f"Não Curtidas que o ECHO não conhece: {len(nao_curtidas)}")
    if argumentos.simular:
        for faixa in curtidas:
            print(f"  + {faixa['artista']} - {faixa['titulo']}")
        for faixa in nao_curtidas:
            print(f"  - {faixa['artista']} - {faixa['titulo']}")
        return 0

    falhas = 0
    for faixa in curtidas:
        if echo_client.enviar_feedback(faixa["artista"], faixa["titulo"], "positivo") is None:
            falhas += 1
        time.sleep(PAUSA_ENTRE_VOTOS)
    for faixa in nao_curtidas:
        if echo_client.enviar_feedback(faixa["artista"], faixa["titulo"], "negativo", abrir_prova=False) is None:
            falhas += 1
        time.sleep(PAUSA_ENTRE_VOTOS)
    print(f"Enviados: {len(curtidas) + len(nao_curtidas) - falhas}. Falhas: {falhas}.")
    return 0 if not falhas else 2


if __name__ == "__main__":
    sys.exit(main())
