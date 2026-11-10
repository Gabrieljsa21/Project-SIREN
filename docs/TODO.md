# TODO - Project SIREN

## Prioridade média

- **Biblioteca real** (view "library" hoje é só placeholder) - artistas/
  álbuns a partir de `historico_local.obter_artistas_mais_tocados` +
  favoritos + playlists, não um scanner de arquivo (SIREN não tem arquivo
  de música além do que já foi baixado). Complexidade: média. Status: não
  iniciado.
## Prioridade baixa

- **Resolver avançado + múltiplas fontes + cache/fallback** (v2 do roadmap)
  - só faz sentido depois que o resto estiver estável. Status: não
  iniciado.
- **Dividir `siren/ui/full/main_window.py`** (2026-11-09) - 1.242 linhas
  numa classe só (barra do player, sidebar, navegação, redimensionamento).
  Extrair a barra do player e a sidebar para módulos próprios. Mexe em
  layout sem teste visual automático, então precisa de conferência na tela
  a cada passo. Complexidade: média. Status: não iniciado.
- **Testes e lint automáticos no GitHub (CI)** (2026-11-09) - hoje rodam só
  à mão (`pytest`, `ruff`). O runner precisa de Windows (dependências
  `winrt-*`). Complexidade: baixa. Status: não iniciado.
- **Resolver em processo separado** (2026-11-09) - o yt-dlp agora roda em
  thread, mas ainda disputa o interpretador com a interface: medido ao
  vivo, pausas de até 0,9 s (antes a janela parava os 8 s inteiros). Um
  processo auxiliar zeraria isso. Só vale se a pausa incomodar.
  Complexidade: média. Status: não iniciado.
- **Duplo clique pra maximizar pode ter ficado instável com
  `startSystemMove()`** (2026-09-06) - trocar o arrasto manual pelo
  arrasto nativo pode interferir na detecção de duplo clique do Qt, já
  que o SO agora entra num loop de mover a cada 1º clique da barra de
  título. Não confirmado se ainda funciona. Status: aguardando
  confirmação do usuário.
- **Confirmar clique em espaço vazio das views não passa mais através**
  (2026-09-06) - causa raiz real das 2 tentativas anteriores falharem:
  `rgba()` no QSS usa alpha como FRAÇÃO 0.0-1.0, não inteiro 0-255 -
  `rgba(0, 0, 0, 1)` = opacidade TOTAL, não "1 de 255" (mesmo erro que o
  Project-ARGUS já tinha documentado). Corrigido pra `rgba(0, 0, 0,
  0.004)` (≈1/255 de verdade) + `Qt.WA_StyledBackground` na janela de
  topo inteira (`chrome.py::configurar_janela_vidro_fosco`) - cobre
  qualquer espaço vazio sem escurecer o vidro fosco. Status: aguardando
  confirmação do usuário.
