# -*- coding: utf-8 -*-
"""Fila de reprodução do SIREN (docs/PLANO_SIREN.md - "SIREN é dono de: fila
atual") - autoridade SEMPRE do SIREN, nunca do ECHO (ele só entra sugerindo
QUEM adicionar, através de `integrations/echo_client.py`).

Em memória, NÃO persistida entre reinícios de propósito - fila é estado de
SESSÃO (o que você tá tocando agora), diferente de playlist/favorito/
histórico, que são dado de longo prazo."""
import random
import time


class Fila:
    def __init__(self):
        # cada item: {"titulo", "artista", "origem", "adicionada_em"} (+ "voto" se votado)
        self._itens = []

    @staticmethod
    def _item(titulo, artista, origem):
        return {"titulo": titulo, "artista": artista, "origem": origem, "adicionada_em": time.time()}

    def adicionar(self, titulo, artista, origem="fila"):
        self._itens.append(self._item(titulo, artista, origem))

    def adicionar_a_seguir(self, titulo, artista, origem="fila"):
        """Insere no topo (próxima a tocar) - "tocar a seguir" é uma ação
        diferente de "adicionar ao final da fila"."""
        self._itens.insert(0, self._item(titulo, artista, origem))

    def remover(self, indice):
        if 0 <= indice < len(self._itens):
            return self._itens.pop(indice)
        return None

    def mover(self, indice, delta):
        """`delta`: -1 sobe, +1 desce - usado pelas setinhas de reordenar da
        tela de Fila. Sem efeito se o movimento sair dos limites."""
        novo_indice = indice + delta
        if 0 <= indice < len(self._itens) and 0 <= novo_indice < len(self._itens):
            self._itens[indice], self._itens[novo_indice] = self._itens[novo_indice], self._itens[indice]

    def mover_para(self, origem, destino):
        """Arrastar-e-soltar da tela Fila (2026-09-26): `destino` é a
        posição de inserção contada na fila ANTES de tirar o item (0 = topo,
        `len` = fim), igual à linha indicadora que a tela mostra."""
        if not (0 <= origem < len(self._itens)) or not (0 <= destino <= len(self._itens)):
            return
        item = self._itens.pop(origem)
        if destino > origem:
            destino -= 1
        self._itens.insert(destino, item)

    def definir_voto(self, indice, voto):
        """`voto`: "positivo", "negativo" ou None. Faixa com voto negativo
        continua visível na fila, mas é pulada quando chega a vez dela
        (pedido do usuário, 2026-09-26: "dislike mantém a música na fila,
        mas é pulado automaticamente quando chega nela")."""
        if 0 <= indice < len(self._itens):
            self._itens[indice]["voto"] = voto

    def proxima(self, aleatorio=False):
        """Remove e devolve o primeiro item que não levou voto negativo -
        os que levaram saem da fila ao serem alcançados, sem tocar. `None`
        se não sobrar nada (quem chama decide o fallback, ex.: pedir mais
        uma sugestão ao ECHO).

        `aleatorio` (botão Aleatório, 2026-09-26): sorteia entre os itens
        sem voto negativo em vez de pegar o primeiro - no Caos, entre as
        faixas já enfileiradas."""
        if aleatorio:
            candidatos = [i for i, item in enumerate(self._itens) if item.get("voto") != "negativo"]
            if not candidatos:
                self._itens = []  # só sobraram não curtidas: todas seriam puladas
                return None
            return self._itens.pop(random.choice(candidatos))
        while self._itens:
            item = self._itens.pop(0)
            if item.get("voto") != "negativo":
                return item
        return None

    def limpar(self):
        self._itens = []

    def listar(self):
        return list(self._itens)

    def __len__(self):
        return len(self._itens)
