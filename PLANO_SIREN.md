# Plano — Project SIREN

## 1. Propósito

SIREN é o player de música pessoal do ecossistema - um "Spotify pessoal": abrir
o programa, tocar música, sem depender de entrar no canal de voz certo do
Discord pra interagir com botões. Nasceu da avaliação de
`Project-ECHO/PLANO_ECHO_PLAYER_LEVE.md` (arquivado - a Fase 7-9 daquele plano,
que propunha um "ECHO Desktop" acoplado e migrar o ERIS, foi substituída por
esta separação de domínio mais limpa).

## 2. Fronteira SIREN × ECHO × ERIS

```text
SIREN                              ECHO                          ERIS
Personal Music Player      Music Intelligence            Discord Social Player
│                                  │                              │
├── reprodução                    ├── perfil musical              ├── reprodução no Discord
├── busca                         ├── 👍 / 👎                     ├── resolver próprio (yt-dlp)
├── fila                          ├── pools                       ├── FFmpegPCMAudio
├── biblioteca                    ├── ranking                     └── estado de playback do Discord
├── favoritos ★                   ├── recomendações
├── playlists                     ├── descoberta / Caos
├── histórico local               ├── Em Alta
└── integração com SO             └── Redescobertas
        │                                  ▲
        └──────── HTTP opcional ───────────┘
```

- **SIREN deve funcionar independentemente do ECHO.** Abrir o programa,
  pesquisar uma música, tocar, favoritar, criar playlist - tudo isso continua
  funcionando com o ECHO desligado.
- **ECHO é uma integração opcional de inteligência.** Quando disponível,
  adiciona Caos/descoberta/recomendação/Em Alta/Redescobertas por cima do
  player. Quando indisponível, o SIREN não trava - só perde essa camada.
- **ERIS permanece completamente à parte.** Nenhuma infraestrutura de
  reprodução é compartilhada entre SIREN e ERIS (ver guardrail 2).

## 3. Ownership de dados e funcionalidades

| Pertence ao SIREN | Pertence ao ECHO |
|---|---|
| fila atual | perfil musical |
| playlists pessoais | pool pré-calculado |
| favoritos do player (★) | ranking / recomendações |
| volume, posição, dispositivo de saída | descoberta / Caos / Em Alta / Redescobertas |
| histórico de reprodução local | votos usados pelo algoritmo (👍/👎) |
| biblioteca | sinais comportamentais (feedback passivo) |
| configurações do player e fontes | |

## 4. `★ Favorito` × `👍/👎` do ECHO

Dois conceitos DIFERENTES de "gostar", intencionalmente:

- **★ Favorito (SIREN)** - "quero guardar/encontrar esta música facilmente".
  Conveniência de player, não vira sinal de treino automaticamente.
- **👍/👎 (ECHO)** - "use isso pra entender meu gosto e influenciar futuras
  escolhas". Sinal de treino do algoritmo (`POST /radar/feedback_ao_vivo`,
  já existe no ECHO).

A UI precisa deixar isso visualmente claro (ícones diferentes) desde que
os dois existirem na mesma tela - nunca um botão só que faz as duas coisas.

## 5. Guardrails (regra fixa, não decisão de implementação)

> **Project SIREN não deve reimplementar perfil musical, ranking ou
> recomendação. Essas responsabilidades pertencem ao Project ECHO. Project
> ECHO não deve reimplementar fila, playlists, biblioteca ou favoritos de
> player. Essas responsabilidades pertencem ao Project SIREN.**

> **Project SIREN não deve substituir, modificar ou compartilhar
> infraestrutura de reprodução com o Project ERIS. Pequena duplicação do
> Playback Resolver é aceitável para preservar a independência dos projetos.**

Essas regras existem especificamente para impedir que a implementação (minha
ou de qualquer agente) "aproveite e já melhore a arquitetura" no meio do
caminho - migrando o ERIS, criando uma lib Python compartilhada entre
repositórios, ou fazendo o ECHO crescer feature de player. Nenhum desses
repositórios hoje compartilha código Python entre si (só HTTP) - criar
acoplamento novo aqui custaria mais do que os ~30-50 linhas de duplicação que
evita.

## 6. Stack inicial

Python + PySide6 (mesmo padrão visual de GAIA/Argus/IRIS - `qt_widgets.py`) +
MPV (via `python-mpv`, requer `libmpv` instalado no sistema) + `yt-dlp`.
Nada de Tauri/Svelte/Rust - resolveria o mesmo problema introduzindo uma
toolchain nova sem necessidade.

## 7. Playback Resolver mínimo

Local ao SIREN (`siren/playback/resolver.py`), sem múltiplos provedores, cache
sofisticado ou fallback complexo nesta fase:

```text
artista + título → yt-dlp (busca) → seleciona 1º resultado → extrai stream
```

Contrato conceitual compartilhado com o ERIS (mesma ideia, implementação
própria em cada repositório - ver guardrail 2):

```python
resolve_stream(title, artist) -> ResolvedStream
# ResolvedStream: url, title, artist, duration, thumbnail, source, expires_at
```

## 8. Endpoints do ECHO usados pela v1

Nenhuma mudança no ECHO é necessária - todas essas rotas já existem
(`Project-ECHO/echo/api_bridge.py`), usadas hoje pelo `/caos` do ERIS:

- `POST /radar/semente` - sugestão de partida sem faixa de referência.
- `POST /radar/proxima` - continuação a partir da faixa atual.
- `POST /radar/feedback_ao_vivo` - 👍/👎.
- `GET /perfil/voto` - se a faixa atual já foi avaliada antes.

`discord_user_id` usa o mesmo `DONO_DISCORD_ID` fixo que `assistant/integrations/echo_client.py`
já usa (SIREN é consumo pessoal, não social).

## 9. Critérios objetivos da v1

1. SIREN consegue obter uma faixa do ECHO (`/radar/semente`).
2. SIREN consegue reproduzi-la localmente, sem Discord (resolver + MPV).
3. As ações do usuário (👍/👎/pular) voltam corretamente pro ECHO.

Nada além disso faz parte da v1: sem fila completa, biblioteca, playlists,
letras, busca própria, múltiplos providers ou telas extras.

## 10. Roadmap incremental

```text
v1     Caos + playback + votos (só ECHO como fonte de faixa)
v1.1   fila / anterior / próximo / volume / seek
v1.2   mini-player + atalhos multimídia do Windows
v1.3   busca própria (yt-dlp direto, sem precisar do ECHO)
v1.4   histórico local + favoritos (★)
v1.5   playlists
v1.6   artista / álbum / letras
v2     resolver avançado + múltiplas fontes + cache/fallback
```

## 11. Referências (arquitetura, não código)

Estudar o desenho, nunca copiar implementação de projeto GPL/AGPL - **conferir
a licença de cada um antes de usar qualquer detalhe de implementação
concreta**, mesma regra que já valia pro `PLANO_ECHO_PLAYER_LEVE.md`.

| Projeto | O que estudar |
|---|---|
| LX Music Desktop | arquitetura de player, controle externo, sources, fila |
| Nuclear | providers, separação metadata/stream, integração com IA |
| YesPlayMusic | UX de um "Spotify pessoal" |
| MusicFree / Desktop | abstração e resolução de fontes |
| Feishin | player desktop, fila, letras, navegação |
| Pear Desktop | organização de app desktop grande |
| Navidrome | fronteira servidor musical ↔ clientes |
| Supersonic | cliente leve e simples |

## 12. Primeiro PR

Não tenta o player inteiro. Prova só o caminho crítico:

```text
SIREN abre → conecta ao ECHO → pede uma faixa do Caos
→ yt-dlp resolve → MPV toca localmente → 👎/⏮/▶/⏭/❤️ → ECHO recebe
```
