<p align="center">
  <img src="assets/icone_siren.png" alt="Project SIREN" width="180">
</p>

# Project SIREN

Player de música para desktop com dois modos de interface, biblioteca, playlists, favoritos, fila e histórico.

## Recursos principais

- reprodução com MPV;
- busca própria e resolução de áudio com yt-dlp;
- barra de progresso clicável para avançar ou voltar na faixa;
- modo Leve para gastar poucos recursos;
- modo Completo com biblioteca e controles extras;
- favoritos, playlists, fila e histórico locais;
- letras sincronizadas e download para uso offline.

## Integração com o LOKI

Os dois modos publicam o estado real da reprodução em eventos UDP locais com schema `siren.playback.v1`: início, pausa, retomada, progresso e término. Cada evento traz sessão, faixa e sequência para o consumidor rejeitar mensagens atrasadas. A porta padrão é `8771` e pode ser alterada por `LOKI_PLAYBACK_EVENT_PORT`. Se o LOKI estiver fechado, a reprodução continua sem erro ou espera.

O contrato só informa o estado musical. A decisão visual futura, inclusive respeito a movimento reduzido, pertence ao LOKI e não duplica player, fila ou histórico dentro do Mascot.

## Origem do nome

SIREN vem das Sereias da mitologia grega, criaturas conhecidas pelo canto irresistível que atraía quem o ouvia. Essa voz marcante combina com o papel do projeto como player e infraestrutura de reprodução musical.

Nas representações gregas antigas, as sereias apareciam muitas vezes com características de mulher e ave. A escolha do nome se concentra em sua voz e em seu canto. A relação pode ser resumida como **Sereias → canto irresistível → música → reprodução**.

### Identidade visual

A logo mostra uma sereia sobre uma pedra diante da lua cheia. O reflexo e as ondulações da água lembram ondas do mar e ondas sonoras. A cauda toca a região de onde elas se propagam, como se o canto atravessasse o próprio mar.

Os quatro cristais azuis e dourados nos pontos cardeais mantêm a linguagem visual do ecossistema. A composição circular preserva três formas reconhecíveis em tamanho pequeno: a lua, a sereia e as ondas.

Em uma frase: **a logo do SIREN representa o canto da sereia se transformando em ondas sobre o mar.**

## Requisitos

- Python 3.11 ou mais recente;
- `ffmpeg` disponível no `PATH`;
- `libmpv-2.dll` acessível ao pacote `python-mpv`.

O pacote `shinchiro.mpv` do Winget traz o executável, mas pode não incluir a DLL usada pelo Python. Baixe uma versão `mpv-dev-x86_64` na página de [releases do mpv para Windows](https://github.com/shinchiro/mpv-winbuild-cmake/releases), extraia `libmpv-2.dll` e coloque o arquivo em `.venv/Lib/site-packages/`.

## Instalação e uso

```powershell
uv sync
uv run siren
uv run siren --lite
uv run siren --full
```

O modo padrão fica em `data/config.json`. Use `iniciar_siren_oculto.vbs` para abrir sem terminal visível.

## Integrações com outros projetos

- **ECHO:** usa o histórico, os votos e o comportamento musical para aprender o que funciona e trazer escolhas relacionadas, incluindo músicas novas. Com ele, o SIREN ganha Caos, recomendações, Em Alta e Redescobertas.

> **SIREN canta o que você quer ouvir.**\
> **ECHO ouve o que você gosta e traz de volta algo que combina com você.**

O SIREN entrega o som. O ECHO ajuda a decidir o que merece voltar. O player, a biblioteca e os recursos locais do SIREN continuam funcionando sem essa integração.

## Documentação

- [Plano do projeto](docs/PLANO_SIREN.md)
- [Pendências](docs/TODO.md)
- [Histórico de versões](CHANGELOG.md)
- [Padrão de documentação](docs/PADRAO_DOCUMENTACAO.md)

## Situação atual

Os dois modos de interface usam o mesmo motor de reprodução. O que ainda está em construção fica listado em `docs/TODO.md`.
