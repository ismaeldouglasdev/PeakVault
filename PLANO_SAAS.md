# PeakVault — De Toy Project a SaaS Vendável

**Status:** awaiting-approval
**Created:** 2026-09-11
**Scope:** Transformar PeakVault de single-tenant toy project em SaaS multiusuário vendável

---

## Context (do repositório atual)

**O que existe hoje:**
- Python + CustomTkinter (desktop, `interface.py`) + Streamlit (web, `app.py`)
- Storage: JSON flat-file em `user_data/`
- Auth: senha única (`PEAKVAULT_PASSWORD`), **single-tenant**
- Stack: streamlit, pandas, matplotlib (só 3 deps)
- `logica.py` (14KB): CRUD, undo/redo (50 snapshots), search, stats, export CSV
- Deploy Render: Dockerfile + Procfile + disco persistente `/app/user_data` (1GB)
- `SAAS_ROADMAP.md` já propõe fases 0-3, pricing (Free/Pro/Lifetime), risco de nicho genérico

**Gap para SaaS (o que falta):**
1. **Multiusuário** — hoje senha única, zero isolamento
2. **Auth real** — magic-link/email+senha, não senha única
3. **Billing** — Stripe Checkout + webhook + portal cliente
4. **Quotas** — Free (1 lista/200 linhas) vs Pro (ilimitado/10k)
5. **Persistência escalável** — JSON flat-file não escala; precisa SQLite/Postgres
6. **Segurança** — rate limit no login (brute force), upload sanitização, antivírus/limite tamanho
7. **Verticalização** — nicho genérico morre (Notion grátis); precisa wedge

---

## Fase 0 — Fundação SaaS (backend + infra)

### D1: Autenticação multiusuário real
- [ ] 1. Migrar storage de `user_data/` (JSON flat-file) para SQLite (ou Postgres no Render)
  - Arquivos: novo `app/storage.py` + `app/db.py`; `logica.py` adaptado
  - Schema: `users` (id, email, password_hash, plan, created_at), `lists` (id, user_id, name, data_json, row_limit, created_at, updated_at)
  - QA: `pytest` migra dados antigos, CRUD em SQLite funciona
- [ ] 2. Implementar auth email+senha com hash PBKDF2 (reutilizar `hash_password`/`verify_password` do inventory-service)
  - Arquivos: `app/auth.py`
  - Endpoints: `register`, `login`, `logout`, `me`, `change_password`
  - JWT ou session cookie para sessão
  - QA: login correto → sessão; senha errada → 401; rate limit no login

### D2: Quotas e planos
- [ ] 3. Implementar model de planos com quotas
  - `users.plan` ∈ {free, pro, lifetime}
  - Quotas: Free = 1 lista / 200 linhas; Pro = ilimitado / 10k linhas
  - Enforcer no storage (bloqueia write quando excede quota)
  - QA: quota Free bloqueia 2ª lista, Pro libera

### D3: Billing real (Stripe)
- [ ] 4. Integrar Stripe Checkout + webhook + portal cliente
  - Deps: `stripe` (adicionar ao requirements)
  - Endpoints: `POST /api/billing/checkout`, `POST /api/billing/webhook`, `GET /api/billing/portal`
  - Webhook atualiza `users.plan` para pro
  - QA: sandbox Stripe — checkout → webhook → plano vira pro; webhook com assinatura válida; teste de quota pós-upgrade

### D4: Segurança
- [ ] 5. Rate limit no login + limite de tamanho de upload + sanitização
  - Reutilizar `IPRateLimiter` do inventory-service (sliding window per-IP)
  - Upload: max 10MB, validação de tipo, sanitização de nome de arquivo
  - QA: 10 tentativas erradas seguidas → bloqueado 60s; upload >10MB → 413; nome com path traversal → sanitizado

### D5: Deploy Render multiusuário
- [ ] 6. Atualizar Dockerfile/Procfile/render.yaml para rodar com SQLite/Postgres + Redis (sessions)
  - Dockerfile já existe (python 3.11-slim + streamlit)
  - Adicionar `DATABASE_URL` (Postgres no Render), `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
  - QA: `render.yaml` com health check, disco persistente, env vars

---

## Fase 1 — Verticalização (o wedge)

### E1: Escolher o nicho
- [ ] 7. Implementar template **"Controle de Estoque MEI"** (o wedge recomendado no SAAS_ROADMAP)
  - Galeria de templates: estoque, anime tracker, TCG collection, hábitos
  - Cada template = schema default + gráficos prontos
  - QA: template estoque cria lista com colunas (produto, qtd, preço_custo, preço_venda, fornecedor, categoria) + gráfico de estoque baixo

### E2: Import CSV/XLSX
- [ ] 8. Importar CSV/XLSX para abrir mercado p/ não-devs
  - Deps: `openpyxl` (XLSX)
  - Endpoint `POST /api/lists/import` aceita CSV (utf-8-sig) + XLSX
  - QA: importa CSV 3 colunas, XLSX com fórmulas

---

## Fase 2 — Experiência SaaS

### F1: Landing page + demo
- [ ] 9. Criar landing page (o que é, screenshots, preços, CTA)
  - Streamlit home page ou página HTML estática
  - Seção pricing (Free R$0 / Pro R$15-25/mês / Lifetime R$290)
  - Botão "Começar grátis" → register
- [ ] 10. Demo read-only pública (conta demo com sample carregado)
  - `PEAKVAULT_DEMO=1` → acesso sem login, sample carregado, somente leitura
  - QA: visitante vê sample, busca/agrupa/grafa, não edita

### F2: Galeria de templates
- [ ] 11. Landing + navegação por templates
  - Lista de templates na home (estoque, anime, TCG, hábitos)
  - "Usar template" → cria lista com schema + dados de exemplo
  - QA: template estoque → lista funcional com 3 itens de exemplo

### F3: Página pública compartilhável
- [ ] 12. `GET /lista/{id}` público por token (SEO + viral loop)
  - Compartilha lista somente leitura via link
  - Meta tags OG (abre Open Graph pro WhatsApp/Facebook)
  - QA: link público renderiza lista, sem auth; não expõe edição

### F4: PWA mobile
- [ ] 13. Tornar app installável no celular (PWA)
  - manifest.json + service worker
  - Streamlit PWA (streamlit-pwa ou manifest estático)
  - QA: Lighthouse PWA pass, instala no Android/iOS

---

## Fase 3 — Crescimento (MRR)

### G1: Analytics + métricas
- [ ] 14. Métricas de uso: DAU, listas criadas, upgrades
  - Coluna `analytics` em SQLite/Postgres + dashboard admin
  - QA: evento de login/lista/upgrade registrado e visível no dashboard

### G2: Planos anuais
- [ ] 15. Stripe plano anual (R$140/ano) + early-adopter lifetime
  - Stripe Prices para monthly + yearly
  - Código de lifetime (cria user com plan=lifetime)
  - QA: checkout monthly → pro; checkout yearly → pro; lifetime → pro vitalício

### G3: Email (boas-vindas, renovações)
- [ ] 16. Email transacional: boas-vindas, falha de pagamento, renovação
  - Deps: `resend` ou SMTP (usar Resend com SendGrid/Postmark como alternativa)
  - QA: email de boas-vindas enviado após register; email de falha de pagamento

---

## Final verification wave

- [ ] F1. Backend: `pytest` passa (auth, quotas, billing, import, storage)
- [ ] F2. Auth: register → login → me → logout; senha errada → 401; rate limit no login
- [ ] F3. Quotas: Free 1 lista/200 linhas; Pro ilimitado/10k; Lifetime pro vitalício
- [ ] F4. Billing: sandbox Stripe — checkout → webhook → plano pro
- [ ] F5. Segurança: upload >10MB → 413; path traversal → sanitizado; rate limit login
- [ ] F6. Verticalização: template estoque funcional; import CSV/XLSX OK
- [ ] F7. Landing: home + demo read-only + preços + CTA register
- [ ] F8. PWA: instalável no Android, manifest OK
- [ ] F9. Deploy Render: health check OK, Postgres conectado, Redis sessions OK
- [ ] F10. Plexo atualizado: task marcada done

---

## Must-NOT-Have

- NÃO manter single-tenant (auth senha única é replaced por multiusuário)
- NÃO usar JSON flat-file como DB primário (migrar pra SQLite/Postgres)
- NÃO adicionar dependências pesadas (mantém stack leve — streamlit, pandas, matplotlib, sqlalchemy, stripe, openpyxl)
- NÃO esquecer o desktop app (`interface.py` CustomTkinter fica como ferramenta local; SaaS é web)
- NÃO deployar sem approval explícito do usuário
- NÃO pular validação de mercado (fase de deploy público + demo antes de escala)

---

## Dependências entre fases

```
Fase 0 (fundação SaaS) → Fase 1 (verticalização) → Fase 2 (experiência SaaS) → Fase 3 (crescimento)
```

D1/D2/D3/D4 (Fase 0) podem rodar em paralelo. D5 depende de D1-D4.
E1 depende de D2 (quotas). F1/F2 dependem de D1 (auth).
G1/G2/G3 dependem de todas as anteriores.