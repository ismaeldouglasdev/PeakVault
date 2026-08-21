# PeakVault — Roadmap SaaS/MRR (proposta para decisão)

> Status atual: serviço web single-tenant funcional (senha única, storage em
> arquivos JSON, deploy Render). Nível: **portfólio sólido**. Este documento
> propõe o caminho até MRR — com uma avaliação honesta de mercado primeiro.

## 1. Avaliação honesta do nicho

"Gerenciador genérico de listas JSON" compete com Notion/Airtable/planilhas —
mercado ruim para cobrar. O valor real está em **verticalizar**: escolher um
tipo de lista onde o público paga por simplicidade + gráficos prontos.

**Wedge recomendado: controle de coleções/estoque para pequenos vendedores BR**
(vantagem injusta: você já opera loja real com OSPOS + inventory-service +
catálogo de ~10k produtos — conhece a dor de verdade).

Alternativas de vertical: tracker de animes/livros/hábitos (mercado grande mas
acostumado a grátis), listas de colecionadores (TCG, vinis, Funko), controle
de ferramentas/equipamentos para MEI.

## 2. Fases

### Fase 0 — Hoje (feito ✅)
Web funcional, auth fail-closed, autosave persistente, UI Dark Coffee.
Deploy no Render seguindo `DEPLOY.md`.

### Fase 1 — Portfólio + validação (1-2 fins de semana)
Objetivo: **validar demanda antes de construir infra de SaaS**.
- [ ] Deploy público no Render (disco persistente + senha forte)
- [ ] Demo read-only pública (conta demo na landing) para recrutadores
- [ ] Landing simples: o que é, screenshots, link pro GitHub
- [ ] Botão "Quero usar" → Stripe Payment Link (R$15-25/mês) + formulário
      de interesse. Zero código de billing ainda — o link resolve.
- [ ] Métrica de decisão: 10 pagantes ou 100 leads em 60 dias → segue;
      senão → fica como portfólio e pivota o wedge.

### Fase 2 — Multiusuário mínimo (se validar; ~2-3 semanas)
- [ ] Contas reais: magic-link por email (Supabase Auth ou Resend + JWT)
- [ ] Isolamento por usuário: `user_data/<user_id>/` (mantém filesystem) ou
      migração pra SQLite/Postgres se precisar de queries
- [ ] Quotas: Free = 1 lista / 200 linhas; Pro = ilimitado / 10k linhas
- [ ] Billing real: Stripe Checkout + webhook + portal do cliente
- [ ] Rate limit no login (hoje não há — brute force é possível)

### Fase 3 — Crescimento (MRR)
- [ ] Galeria de templates (anime tracker, estoque MEI, coleção TCG, hábitos)
- [ ] Import CSV/XLSX (abre mercado pra não-devs)
- [ ] Página pública compartilhável por lista (SEO + viral loop)
- [ ] PWA mobile
- [ ] Plano anual com desconto + early-adopter lifetime

## 3. Pricing hipótese

| Plano | Preço | Limites |
|---|---|---|
| Free | R$0 | 1 lista, 200 linhas |
| Pro | R$15/mês ou R$140/ano | listas ilimitadas, 10k linhas, export CSV/XLSX, gráficos HD |
| Lifetime early | R$290 único | primeiros 50 usuários |

Meta conservadora fase 3: 50 Pro ≈ R$750/mês. Não é renda principal — é
produto de portfólio que **pode** pagar o próprio servidor e ensinar SaaS
end-to-end (auth, billing, quotas, métricas).

## 4. Riscos

- Nicho genérico sem verticalizar = morte por indiferença (Notion grátis)
- Filesystem como DB não escala horizontalmente (Render pode reiniciar
  instâncias) → fase 2 já isola por usuário; Postgres só se houver tração
- Suporte a uploads maliciosos: sanitização de nome feita, mas falta antivírus/
  limite de tamanho de arquivo (adicionar na fase 2)

## 5. Decisão pedida

1. **A)** Só portfólio: fazer deploy público + demo read-only e parar aqui
2. **B)** Validar (recomendado): fase 1 completa com Stripe Payment Link
3. **C)** Acelerar: pular direto pra fase 2 (multiusuário + billing real)
