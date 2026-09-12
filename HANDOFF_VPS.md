# HANDOFF — PeakVault SaaS → Agente VPS

**Data:** 2026-09-12 · **Origem:** sessão local (F0.1–F0.4 + F0.4-QA real Stripe)
**Próximo agente:** VPS (deploy/continuar F0.5)

---

## 📌 Status Atual e Progresso

### Completo e testado (F0.1–F0.4, 23 testes verdes)
- Pacote `app/` em `/home/ismaeldev/Desktop/code_study/MeusProjetos/PeakVault`:
  `db.py`, `security.py`, `auth.py`, `storage.py`, `plans.py`, `billing.py`.
- `tests/` → `python3 -m pytest tests/ -q` = **23 passed**.
- App rodando em Streamlit (`localhost:8501`).

### F0.4-QA — validação real Stripe: ✅ COMPLETA (ponta a ponta)
- Checkout hosted Stripe funciona com o catálogo real (produto/price), pagamento em modo teste `payment_status=paid` (R$19,90 BRW).
- **Entrega real do webhook confirmada:** evento `evt_1UEhZwJAIJUM8Ur1KLWQ2SOh` (session `cs_test_a1XpUAgJwT3LUAPPponayOAPRjCVLm6ySVBT681GdCcyel2GqHjkrkYTtG`) → `pending_webhooks: 0`; chegou via tunnel estável cloudflared (pane tmux `whook` mostrou POST real às `01:26:31`).
- **DB:** `user_id=1, email=e2e-1789179914@peakvault.test, plan=pro, customer=cus_VFB63lE3eYR3ec`. Assinatura verificada com whsec real (`construct_event`).

## ⚠️ Pendências e Bloqueios

### Conhecidos (não bloqueiam F0.5)
1. **Evento `evt_1UEgjzJAIJUM8Ur10oasXYzn`** (1º checkout, `cs_test_a10SKoUd9...`) ainda `pending: 1` — em retry backoff do Stripe; vai cair no tunnel atual eventualmente. Pode marcar como resolvido quando `pending: 0`.
2. **Tunnels:**
   - `localhost.run` (anônimo) **MUITO instável** — morre em ~15min. NÃO usar para webhook. Foi a causa raiz das falhas de entrega.
   - **`cloudflared`** (estável, atual): iniciar é `~/.local/bin/cloudflared tunnel --no-autoupdate --url http://localhost:8787` (rodar com `setsid -f` para sobreviver; regex `https://[a-z0-9-]+\.trycloudflare\.com` para achar URL). URL atual: `https://sensitivity-formation-extends-knowledgestorm.trycloudflare.com` (pode mudar se reiniciar).
   - Se o tunnel reiniciar, **PATCH o endpoint**: `curl -X POST https://api.stripe.com/v1/webhook_endpoints/we_1UEgRFJAIJUM8Ur1AyU8lGkt -u "$SK:" -d "url=https://NOVA-URL/api/billing/webhook"`.
3. **Webhook server local:** tmux session `whook`, `python3 scripts/webhook_server.py` na `127.0.0.1:8787`. **OBS importante:** `billing.handle_webhook` é `async` → o servidor já foi corrigido para `asyncio.run(...)`. NÃO reverter.

## 🚀 Próximos Passos Imediatos (F0.5 / fase D4 — segurança)

1. **Rate-limit login:** portar `IPRateLimiter` (sliding window per-IP) do `inventory-service/` → `app/security.py`/`auth.py`. Regra: 10 falhas de login → bloqueio por 60s.
2. **Upload max 10MB → 413:** validar tamanho máx em `app/storage.py` (retornar 413 quando exceder).
3. **Sanitização de filename:** impedir path traversal em nomes de arquivo.
4. **Testes** para os 3 itens (rate-limit, upload, sanitização) → suíte verde.
5. Depois: deploy (VPS), plano `peakvault-saas.md`.

## 💡 Onboarding Stripe (pedido do usuário — pendente)
- `npx skills add https://docs.stripe.com`
- MCP: `https://mcp.stripe.com`
- Tool `stripe_implementation_planner`
- Revisar `billing.py` vs plano D3 + Payments/Invoicing/Tax (negócio `ismaieltech.com`).

## 📁 Arquivos Relevantes

- `PeakVault/app/billing.py` (corrigido: `.get()` vira `[]`/try-except — StripeObject não tem `.get()`)
- `PeakVault/scripts/stripe_setup.py`, `webhook_server.py`, `e2e_checkout.py`
- `PeakVault/.env` (**gitignored**; tem SK/PK/whsec/prices — NUNCA commitar), `.env.example`, `.gitignore`
- `PeakVault/data/peakvault.db` (dev; DB padrão `sqlite:///./data/peakvault.db`)
- `inventory-service/` → fonte do `IPRateLimiter`
- `/home/ismaeldev/.opencode/mcp/rag-mcp/get_real_model.py` → footer de modelo

## 🔐 Chaves de TESTE (só teste, NUNCA produção)
- **secret:** `sk_test_...` → valor real em `PeakVault/.env` (`STRIPE_SECRET_KEY`, gitignored — nunca commitar)
- **publishable:** `pk_test_...` → valor real em `PeakVault/.env` (`STRIPE_PUBLISHABLE_KEY`)
- **Produto:** `prod_VFAgg5gRnr3P9w` "PeakVault Pro"
- **Prices:** monthly `price_1UEgLNJAIJUM8Ur17ahlob73` (R$19,90/mês); lifetime `price_1UEgOEJAIJUM8Ur1NKpo916I` (R$290,00)
- **Webhook endpoint:** `we_1UEgRFJAIJUM8Ur1AyU8lGkt` (evento `checkout.session.completed`)
- **whsec:** em `PeakVault/.env` como `STRIPE_WEBHOOK_SECRET` (valor oculto; NÃO expor)
- **Cartão de teste:** `4242 4242 4242 4242`, exp `12/34`, CVC `123`

## 📋 Regras Operacionais (desta sessão)
- **Tool-call:** passar `command`/`target`/`text` como **parâmetros no topo** (NÃO aninhar em `{"arguments": {...}}`) → evita SchemaError.
- Processos longos (servidor/tunnel): usar `tmux new-session -d` (o bash tool dá timeout e mata filhos que segurem FD) — cloudflared usar `setsid -f`.
- Rodapé de resposta: `python3 /home/ismaeldev/.opencode/mcp/rag-mcp/get_real_model.py` (modelo real) + tempo de sessão.

---

## 🛡️ F0.5 (D4) — Segurança: ✅ COMPLETA (36 testes verdes)

**Data:** 2026-09-12 · Suite: `python3 -m pytest tests/ -q` = **36 passed** (23 antigos + 13 novos)

### Rate-limit de login (descoberta importante)
- **`inventory-service/app/services/rate_limiter.py` é `TokenBucketRateLimiter` por canal** (woocommerce/mercadolivre/shopee — limita chamadas a APIs externas), **NÃO é IP sliding-window**. Não servia para bruto-force de login.
- Criado **`PeakVault/app/ratelimit.py`**: `LoginRateLimiter` (sliding-window por IP, in-memory, `asyncio.Lock`, 10 falhas → bloqueio 60s) + exceção `LoginRateLimited(retry_after)` + singleton `login_rate_limiter`. Interface pensada para trocar por Redis depois (multi-instância).
- **`app/auth.py::login()`** agora aceita `ip: Optional[str] = None`: checa `is_blocked` antes (barato, nem hashia senha), registra falha em credencial inválida, limpa contador no sucesso. Sem `ip`, comportamento antigo intacto (backward compat).
- **UI (Streamlit) NÃO passa IP** — não há acesso confiável ao IP do cliente no Streamlit; em produção, o proxy/reverse-proxy deve injetar `X-Forwarded-For` e chamar `login(..., ip=...)`.

### Upload 10 MiB + sanitização de nome
- `app/plans.py`: `MAX_UPLOAD_BYTES = 10 * 1024 * 1024` + `can_upload_size(bytes)` (limite global, todos os planos).
- `app/storage.py`: `create_list`/`update_list` rejeitam payload > 10 MiB (`ValueError: Upload exceeds the 10 MiB limit` — virar 413 no handler HTTP). Novo `sanitize_name()` (basename + allow-list regex + strip dots + garante `.json`) — anti path traversal.
- `app.py` (Streamlit): `_safe_name()` delega ao `storage.sanitize_name`; `st.file_uploader` bloqueia `size > MAX_UPLOAD_BYTES` com `st.error` antes de ler o arquivo.

### Próximos passos sugeridos (VPS)
1. Deploy + apontar `PEAKVAULT_PASSWORD`/`JWT_SECRET`/`STRIPE_*` reais (ver seção chaves).
2. Integrar IP do cliente no login (X-Forwarded-For → `login(..., ip=...)`) atrás do proxy.
3. Migrar `LoginRateLimiter` p/ Redis se rodar multi-instância.
4. Onboarding Stripe pendente: `npx skills add https://docs.stripe.com`, MCP `https://mcp.stripe.com`, tool `stripe_implementation_planner` — revisar `billing.py` vs plano D3.