# Smarter Jira TS Monorepo

## Estrutura Proposta

- [`package.json`](ts-monorepo/package.json): manifesto raiz com scripts de build, lint, testes e workspaces.
- [`tsconfig.base.json`](ts-monorepo/tsconfig.base.json): configuração compartilhada do TypeScript.
- [`src/core/`](ts-monorepo/src/core/index.ts): módulos puros reutilizáveis (cliente Jira, configuração, parsing CSV, serviços de criação/reordenamento/relatórios).
- [`src/cli/`](ts-monorepo/src/cli/index.ts): comandos CLI consumindo o núcleo e exportados via `bin`.
- [`src/extension/`](ts-monorepo/src/extension/manifest.json): código da extensão WebExtension (service worker, popup, options) construído sobre o núcleo.

## Ferramentas Sugeridas

- Build bundler: `tsup` para CLI e núcleos, `Vite` para a extensão.
- Testes: `vitest` para unidade, `playwright` para smoke de extensão.
- Lint/format: `eslint` + `prettier`.
- Gerenciamento de tipos: referências entre `tsconfig` para CLI e extensão apontando para o `core`.

## Próximos Passos

1. Criar `package.json` raiz com workspaces (`core`, `cli`, `extension`).
2. Adicionar `tsconfig` base e específicos.
3. Implementar utilitários de cliente Jira, normalização de CSV e carregamento de config no núcleo.
4. Portar funcionalidades da CLI Python para comandos TypeScript.
5. Criar manifest v3 e integrar UI da extensão com o núcleo.
