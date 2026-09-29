# -*- coding: utf-8 -*-
"""Última faixa tocada, pra retomar ao reabrir o SIREN (2026-09-26, pedido
do usuário: "quando reinicia, deveria continuar com a música ativa de
quando fechou, só que pausada").

Guarda só a faixa atual e a posição - a fila continua sendo estado de
sessão, de propósito (ver `core/fila.py`). Gravado ao fechar e também de
tempos em tempos enquanto toca, pra sobreviver a um encerramento forçado
do processo (sem `closeEvent`).

Troca entre Modo Completo e Modo Leve sem parar a música (2026-09-26,
pedido do usuário: "deveria abrir o modo leve, continuar tocando apenas
lá, e só então fechar o modo completo"): a janela que sai grava a sessão
com `continuar=True` e o próprio `pid` várias vezes por segundo enquanto
continua tocando; a que entra carrega o áudio, começa na posição mais
recente (compensando o tempo desde a última gravação) e grava
`ARQUIVO_TROCA` com aquele `pid` - a antiga vê o arquivo e fecha.

Gravação atômica (arquivo temporário + `os.replace`): durante a troca, dois
processos leem e escrevem estes arquivos ao mesmo tempo."""
import json
import os
import time

ARQUIVO_SESSAO = "data/sessao.json"
ARQUIVO_JANELA = "data/janela.json"
ARQUIVO_JANELA_MINI = "data/janela_mini.json"
ARQUIVO_TROCA = "data/troca_de_modo.json"


def _gravar(caminho, dados):
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    temporario = f"{caminho}.{os.getpid()}.tmp"
    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    os.replace(temporario, caminho)


def _ler(caminho):
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, dict) else None
    except Exception:
        return None


def salvar_janela(x, y, largura, altura, maximizada, arquivo=None):
    """Tamanho/posição da janela - a geometria "normal" (não maximizada), pra
    restaurar certo mesmo quando ela fechou maximizada. `arquivo`: o
    miniplayer guarda a dele separada (`ARQUIVO_JANELA_MINI`)."""
    _gravar(arquivo or ARQUIVO_JANELA, {"x": x, "y": y, "largura": largura, "altura": altura, "maximizada": bool(maximizada)})


def carregar_janela(arquivo=None):
    dados = _ler(arquivo or ARQUIVO_JANELA)
    if dados and all(isinstance(dados.get(c), int) for c in ("x", "y", "largura", "altura")):
        return dados
    return None


def geometria_visivel(geometria, telas):
    """A geometria salva só vale se a barra do topo da janela cair dentro de
    algum monitor conectado - senão (monitor desligado, resolução mudou) a
    janela abriria fora da tela, e o SIREN pareceria não ter aberto (achado
    2026-09-26: miniplayer salvo em x=3887). `telas`: retângulos
    `(x, y, largura, altura)` das áreas úteis dos monitores."""
    if not geometria:
        return False
    x, y = geometria["x"] + 40, geometria["y"] + 10
    return any(tx <= x < tx + tl and ty <= y < ty + ta for tx, ty, tl, ta in telas)


def salvar(titulo, artista, origem, posicao, duracao=None, thumbnail=None, continuar=False):
    _gravar(ARQUIVO_SESSAO, {
        "titulo": titulo,
        "artista": artista,
        "origem": origem,
        "posicao": round(float(posicao or 0), 2),
        "duracao": int(duracao) if duracao else None,
        "thumbnail": thumbnail,
        "continuar": bool(continuar),
        "pid": os.getpid(),
        "salvo_em": time.time(),
    })


def carregar():
    """`dict` da última faixa, ou `None` se não houver (ou o arquivo estiver
    corrompido - nunca impede o SIREN de abrir)."""
    dados = _ler(ARQUIVO_SESSAO)
    if not dados or not dados.get("titulo") or not dados.get("artista"):
        return None
    return dados


def posicao_atualizada(dados):
    """Posição compensando o tempo desde a gravação - numa troca de modo a
    janela antiga continua tocando, então a posição gravada já ficou pra
    trás quando a nova vai começar."""
    posicao = float(dados.get("posicao") or 0)
    if dados.get("continuar") and dados.get("salvo_em"):
        posicao += max(0.0, time.time() - float(dados["salvo_em"]))
    return posicao


def sinalizar_troca_concluida(pid_origem):
    """A janela nova já está tocando: a antiga (`pid_origem`) pode fechar."""
    _gravar(ARQUIVO_TROCA, {"pid_origem": int(pid_origem), "em": time.time()})


def troca_concluida_para(pid):
    """A janela antiga pergunta se já pode fechar (e consome o aviso)."""
    dados = _ler(ARQUIVO_TROCA)
    if dados and dados.get("pid_origem") == pid:
        try:
            os.remove(ARQUIVO_TROCA)
        except OSError:
            pass
        return True
    return False
