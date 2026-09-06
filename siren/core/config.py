# -*- coding: utf-8 -*-
"""Configuração persistente do SIREN (`data/config.json`) - fonte única pra
tudo que deveria ser fácil de mudar sem editar código (pedido do usuário,
2026-09-06: "sempre deixando fácil alterar ou configurar o que importa").
Mesmo padrão de arquivo JSON simples já usado em todo o ecossistema
(`echo/core/perfil.py`, HESTIA etc.) - sem banco de dados, sem dependência
nova.

`modo_ui` é a decisão mais importante daqui - "lite" (janela simples de
sempre, pra rodar de lado com jogo/programa pesado sem competir por CPU/GPU)
ou "full" (biblioteca/playlists/fila/letras, vidro fosco tipo Argus). Ver
PLANO_SIREN.md, seção "Modo Leve x Modo Completo"."""
import os
import json

ARQUIVO_CONFIG = "data/config.json"

PADRAO = {
    "modo_ui": "lite",
    "pasta_downloads": "data/downloads",
    "acrylic_ativado": True,
    "volume_inicial": 70,
    "youtube_cookies_file": "",
    "lyrics_ativado": True,
    # "nenhum" (botão "Traduzir" some), "gratis" (MyMemory, sem chave) ou
    # "llm" (Groq, precisa de GROQ_API_KEY no ambiente) - pedido do usuário
    # (2026-09-06): "deixa isso meio que habilitável, só trazer a tradução
    # quando solicitado" - NUNCA traduz sozinho, só quando o usuário clica.
    "traducao_provedor": "nenhum",
    "traducao_idioma_alvo": "pt-BR",
}


def carregar():
    """Sempre devolve TODAS as chaves de `PADRAO`, mesmo se o arquivo salvo
    for de uma versão mais antiga (chave nova ainda não existia) - nunca
    KeyError em `config[chave]` só porque o config.json é velho."""
    if not os.path.exists(ARQUIVO_CONFIG):
        return dict(PADRAO)
    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        return dict(PADRAO)
    config = dict(PADRAO)
    config.update(dados)
    return config


def salvar(config):
    os.makedirs(os.path.dirname(ARQUIVO_CONFIG), exist_ok=True)
    with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def obter(chave):
    return carregar().get(chave, PADRAO.get(chave))


def definir(chave, valor):
    config = carregar()
    config[chave] = valor
    salvar(config)
    return config
