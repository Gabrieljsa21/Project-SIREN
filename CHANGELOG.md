# Changelog

Este arquivo registra as mudanças importantes do projeto. O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Adicionado

- **Contrato de eventos de reprodução SIREN para LOKI (2026-09-07)** - os modos Leve e Completo publicam `track_started`, `playback_paused`, `playback_resumed`, `progress` e `track_ended` pelo schema versionado `siren.playback.v1`, via UDP local. Sessão, faixa e sequência permitem ao LOKI descartar eventos atrasados; sem receptor, o player segue normalmente. O LOKI mantém apenas estado de reprodução, sem impor uma cena visual. O item concluído foi removido de `docs/TODO.md`.
- **Barra de progresso com seek** (2026-09-07): o rodapé do player agora mostra posição e duração em tempo real. Clicar ou arrastar a barra move a reprodução para aquele ponto exato; a duração descoberta pelo MPV cobre também faixas locais que não trazem essa informação no resolvedor.
- **Busca própria no Modo Completo** (2026-09-07): a antiga tela vazia agora pesquisa até cinco resultados diretamente no YouTube com `yt-dlp`, sem depender do ECHO. A consulta roda fora da thread da interface, Enter também inicia a busca e ativar um resultado o envia ao fluxo único de reprodução com origem `busca`.

### Corrigido

- **Tradução de letras não congela mais a janela** (2026-09-07): MyMemory ou GAIA agora são consultados em uma `QThread`, o botão informa que a tradução está em andamento e bloqueia pedidos duplicados. Se a faixa mudar antes da resposta, o resultado antigo é descartado em vez de sobrescrever a letra atual.
- **Importações duplicadas do YouTube bloqueadas** (2026-09-07): o botão "Importar do YouTube" permanecia ativo durante o `ImportYoutubeWorker`, permitindo iniciar duas importações sobrepostas. Agora ele é desabilitado enquanto o worker roda, há uma segunda trava pelo estado da thread e o controle volta ao normal no sinal `finished` mesmo quando a importação falha.

## [0.1.0] - 2026-09-06

### Adicionado

- Player com modos Leve e Completo.
- Reprodução por MPV e busca de áudio com yt-dlp.
- Biblioteca, playlists, favoritos, fila e histórico locais.
- Integração opcional com o ECHO para recomendações e modo Caos.
- Letras sincronizadas, tradução sob demanda e download offline.
