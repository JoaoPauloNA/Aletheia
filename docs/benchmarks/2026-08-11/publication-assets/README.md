# Assets de publicação — benchmark 2026-08-11

Estes assets foram gerados deterministicamente por
`scripts/generate_publication_assets.py`, usando exclusivamente os dados
numéricos de `../result-public.json`. Run ID:
`1c7334d6-075c-4b0f-8dcb-aaf9430629f5`.

## Mapa dos assets

| Asset | Finalidade |
|---|---|
| `provider-outcomes.svg` / `.png` | Desfechos por provedor/argumento de modelo (36 episódios por linha). |
| `task-outcomes.svg` / `.png` | Desfechos por tarefa (15 episódios por linha). |
| `provider-results.md` / `.csv` | Consulta auditável exata por provedor/argumento. |
| `task-results.md` / `.csv` | Consulta auditável exata por tarefa. |
| `SHA256SUMS` | Checksums dos gráficos e tabelas gerados. |

## Uso no DEV.to e LinkedIn

Use preferencialmente o PNG em postagens: é a cópia rasterizada em resolução
de publicação. Preserve o SVG como fonte canônica e reprodutível para edição
ou redimensionamento. Faça upload do arquivo, cole a legenda apropriada abaixo
e preencha o campo de texto alternativo com o alt text correspondente. Não
recorte a legenda, a nota de fonte ou a ressalva exploratória para transformar
as barras em ranking.

### provider-outcomes

- Legenda: “Desfechos verificados por provedor/argumento de modelo em 36
  episódios cada; estudo exploratório com três repetições por combinação, não
  um ranking de modelos.”
- Alt text: “Gráfico de barras horizontais 100% empilhadas para cinco
  provedores e argumentos de modelo. Cada barra tem 36 episódios e mostra as
  proporções de SOLVED, FALSE_SUCCESS, FAILED_HONEST e GUARD_VIOLATION, com
  padrões além das cores.”

### task-outcomes

- Legenda: “Desfechos verificados por tarefa, com 15 episódios por tarefa;
  o bucket inválido foi zero e não é mostrado.”
- Alt text: “Gráfico de barras horizontais 100% empilhadas para 12 tarefas.
  Cada barra tem 15 episódios e mostra SOLVED, FALSE_SUCCESS, FAILED_HONEST e
  GUARD_VIOLATION, com padrões além das cores.”

## Tabelas e fonte

As tabelas Markdown são copiáveis para o editor; os CSVs servem para auditoria
ou planilha. As contagens, taxas e durações são derivadas diretamente dos 180
episódios em `result-public.json`. Taxa de falso sucesso condicional =
`FALSE_SUCCESS / (SOLVED + FALSE_SUCCESS)`; taxa de guardas =
`GUARD_VIOLATION / episódios classificáveis`. A duração mediana usa a média do
par central quando o número de episódios é par; p95 usa nearest-rank
(`ceil(0,95 × n)`). O nome de modelo registrado é argumento da Athena CLI, não
identidade de backend verificada independentemente. Palindrome e slugify são
intencionalmente subespecificadas em relação aos seus casos ocultos.

## Integridade

- SHA-256 da fonte numérica `result-public.json`:
  `aa9f2f3611bd35cf28e4d91af83fc591a32369cf599b6fc57350ee71d29ba71e`.
- SHA-256 do JSON bruto registrado no resultado: `401dbb270bc0694cfb36d62b05264718fbacc483532d7ab50b0db87bea84780e`.
- Para verificar os assets gerados, dentro deste diretório execute:
  `shasum -a 256 -c SHA256SUMS`.

## Limitações

- Há somente n=3 por combinação tarefa/provedor; não há alegação de ranking
  amplo, causalidade ou custo-eficiência.
- O baseline da suíte estava sujo, mas foi revisado; não equivale a uma revisão
  limpa e commitada.
- Identidade de modelo, temperatura e não determinismo do provedor não foram
  verificados/controlados independentemente.
- Diretórios temporários isolam episódios, mas não são sandboxes do sistema
  operacional.
