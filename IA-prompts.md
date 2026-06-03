# IA Prompts

Registro de prompts enviados à IA durante o desenvolvimento do projeto, com data, horário, ação executada e artefatos gerados.

## 2026-05-28 11:59:52 -03

### Prompt

> Leia o session e spec para entender o contexto do projeto

### Feito/Gerado

- Foram lidos `session-log.md` e `backend-spec.md`.
- Foi identificado que o foco atual do projeto é fechar a modelagem/API REST do MVP.
- Foram resumidos o estado do schema Prisma, recursos REST existentes, pendências de DTOs, placeholders nos services e próximos passos.

## 2026-05-28 11:59:52 -03

### Prompt

> Termine a criação dos DTOs das entidade existentes
> Utulize validation pipe do nextjs
> Utilize mappedtype, class validator e transform

### Feito/Gerado

- Foram preenchidos DTOs de criação para:
  - `grupos-pesquisa`.
  - `instituicao`.
  - `linha-pesquisa`.
  - `pesquisadores`.
  - `producoes`.
  - DTOs do gateway `langchain`.
- Os DTOs de atualização permaneceram baseados em `PartialType` de `@nestjs/mapped-types`.
- Foi ativado `ValidationPipe` global no NestJS com `whitelist`, `forbidNonWhitelisted` e `transform`.
- Foram adicionadas as dependências `class-validator` e `class-transformer`.
- Foram corrigidos endpoints scaffold que convertiam UUID para número.
- `npm run build` passou.
- `npm test` falhou por incompatibilidade entre Jest e Prisma Client gerado com `import.meta`.

## 2026-05-28 11:59:52 -03

### Prompt

> Adicione um alias @ para diminuir o texto dos imports apontando para src/
> Quero que vocẽ use os enums criados pelo prisma, não crie novos

### Feito/Gerado

- Foi adicionado alias `@/*` apontando para `src/*` no `tsconfig.json`.
- Foi adicionado `moduleNameMapper` equivalente para Jest.
- Foi criado `src/prisma/prisma.enums.ts` para reexportar enums gerados pelo Prisma.
- DTOs passaram a importar enums do Prisma em vez de enums locais duplicados.
- Imports internos de `PrismaService` foram atualizados para usar `@/prisma/prisma.service`.
- `npm run build` passou.

## 2026-05-28 11:59:52 -03

### Prompt

> Lembre de ir sempre atualizando o session.md e o backend-spec.md

### Feito/Gerado

- `session-log.md` foi atualizado com a sessão de 2026-05-28.
- `backend-spec.md` foi atualizado com o estado atual dos DTOs, validação global, alias `@`, uso de enums Prisma e pendência dos testes Jest.
- Foi registrado que `session-log.md` está no `.gitignore`, mas continua sendo mantido localmente.

## 2026-05-28 11:59:52 -03

### Prompt

> Faça também um IA-prompts.md onde  você irá guardar os prompts enviados formatados, o que foi feito/gerado e a data   e horário que aconteceu.

### Feito/Gerado

- Foi criado este arquivo `IA-prompts.md`.
- Foi definido um formato de registro com data/hora, prompt e ações/artefatos gerados.
- Foram registrados os prompts principais da sessão atual.

## 2026-05-28 12:01:17 -03

### Prompt

> Não registre no backend-spec coisas relacionadas a essa conversa ou sessão, apenas alterações que tenham relevância no escopo do projeto

### Feito/Gerado

- Foi removida do `backend-spec.md` a seção sobre registros de apoio/conversa.
- Foi mantida em `session-log.md` a decisão operacional de limitar o `backend-spec.md` a conteúdo técnico/acadêmico do projeto.
- Este prompt foi registrado em `IA-prompts.md`.

## 2026-05-28 12:04:41 -03

### Prompt

> Crie uma pasta docs e converta todo o código prisma para planuml, coloque como modelagem_DER.md  o nome do arquivo
> Adicione a essa pasta o backend-spec.md
> Crie uma imagem do diagrama estrutural do projeto e coloque nessa pasta

### Feito/Gerado

- Foi criada a pasta `docs`.
- Foi copiado `backend-spec.md` para `docs/backend-spec.md`.
- Foi criado `docs/modelagem_DER.md` com o DER em PlantUML derivado do schema Prisma.
- Foi criada a imagem `docs/diagrama_estrutural.svg` com a estrutura do projeto.
- `session-log.md` e `IA-prompts.md` foram atualizados.

## 2026-05-28 18:28:13 -03

### Prompt

> Quero que troque todas as funções que usam id como string para UUID

### Feito/Gerado

- Foi criado o tipo interno `UUID` em `apps/api/src/common/types/uuid.type.ts`.
- Controllers scaffold passaram a validar `:id` com `ParseUUIDPipe`.
- Services scaffold passaram a usar `UUID` nas assinaturas de `findOne`, `update` e `remove`.
- `backend-spec.md`, `docs/backend-spec.md`, `session-log.md` e `IA-prompts.md` foram atualizados.
- `npm run build` passou.

## 2026-05-28 18:34:45 -03

### Prompt

> Adicione isso ao seu contexto e a algum arquivo que achar necessário. Todas as mudanças de código devem ser perguntadas antes de realizadas para feedback , sempre pergunte antes de aplicar mudanças

### Feito/Gerado

- A regra foi incorporada ao contexto de trabalho desta sessão.
- `session-log.md` foi atualizado com a decisão de sempre pedir confirmação antes de aplicar mudanças de código.
- Este prompt foi registrado em `IA-prompts.md`.
