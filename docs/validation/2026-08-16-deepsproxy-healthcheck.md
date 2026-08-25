# DeepSeek via Docker — health check controlado — 2026-08-16

## Escopo

Recuperar o DeepsProxy local como opção econômica para testes controlados do
Aletheia, sem consumir Claude, Cursor ou Codex. Este registro valida somente
o transporte e a sessão; não mede capacidade, honestidade nem custo geral do
modelo.

## Correção aplicada

- Uma sessão DeepSeek foi autenticada manualmente em perfil local privado.
- O Compose do IAProxy passou a montar esse perfil apenas no container
  `deepsproxy`.
- A porta do DeepSeek foi restringida a `127.0.0.1:3103`; não está exposta na
  rede local.
- O volume Docker nomeado anterior foi preservado como rollback e não foi
  removido.

Nenhuma credencial, cookie, conteúdo de sessão ou prompt sensível é registrado
neste documento.

## Resultado do health check

| Caminho | Modelo | Resultado |
| --- | --- | --- |
| `POST /v1/chat/completions`, `stream: false` | `deepseek-v4-flash` | HTTP `200`; resposta estruturada `{\"ok\":true}`. |
| `POST /v1/chat/completions`, `stream: true` | `deepseek-v4-flash` | SSE válido: papel inicial, conteúdo `OK`, `finish_reason: stop` e `[DONE]`. |
| OpenCode → DeepsProxy | `deepseek-v4-flash` | Não aceito ainda: o modelo foi reconhecido, mas a execução não entregou conteúdo ao cliente. |

## Limite atual

O endpoint local é utilizável para smoke tests e episódios curtos controlados
quando chamado diretamente por cliente OpenAI-compatible. O clone atual tem
um problema de compatibilidade com o fluxo streaming/retentativa do OpenCode,
que injeta contexto grande e pode acionar compressão/repetição. Não usar esse
caminho para a campanha Aletheia até haver teste de aceitação específico.

## Próximo teste aceito

Usar `deepseek-v4-flash` em um episódio Aletheia pequeno por cliente
OpenAI-compatible com `stream: false`, registrar `claimed`, checks
determinísticos, veredito, latência e uso reportado. O episódio só entra em
qualquer métrica após ser reproduzível e sanitizado.
