# Deploy — PeakVault Web

O app web é Streamlit (`app.py`) com login por senha e persistência em arquivos
JSON dentro de `user_data/`. Dois caminhos de deploy suportados: **Docker**
(recomendado) ou **runtime nativo Python** no Render.

## Requisito obrigatório

| Variável | Obrigatória | Descrição |
|---|---|---|
| `PEAKVAULT_PASSWORD` | ✅ sim | Senha de acesso. **Sem ela o app nega login** (fail-closed). Nunca usar senha default no código. |

## Opção 1 — Docker (Render Blueprint / Web Service Docker)

O `Dockerfile` escuta em `$PORT` (com fallback 8080), então funciona no Render
sem configuração extra de porta.

1. Render Dashboard → **New → Web Service** → conectar `ismaeldouglasdev/PeakVault`
2. Runtime: **Docker**
3. Environment → adicionar `PEAKVAULT_PASSWORD=<senha forte>`
4. **Disco persistente**: Mount Path `/app/user_data`, tamanho 1 GB
   (sem isso, uploads somem a cada redeploy — filesystem é efêmero)
5. Health Check Path: `/`
6. Deploy e validar o checklist abaixo

## Opção 2 — Runtime nativo Python

O `Procfile` usa `$PORT` corretamente.

1. New → Web Service → runtime **Python 3**
2. Build: `pip install -r requirements.txt`
3. Start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
4. Mesmos passos 3–6 da opção Docker (disco persistente: mount no diretório do repo, ex.: `/opt/render/project/src/user_data`)

## Checklist pós-deploy

- [ ] Sem `PEAKVAULT_PASSWORD`: tela mostra aviso de servidor sem senha (não loga)
- [ ] Com senha errada: "Senha incorreta"
- [ ] Login OK → sidebar com uploader visível
- [ ] Upload de JSON → tabela renderiza + arquivo aparece em `📁 Arquivos salvos`
- [ ] Editar célula na tabela → recarregar página → edição persistiu (disco)
- [ ] Buscar algo → tabela vira somente leitura com aviso "limpe a busca para editar"
- [ ] 🗑️ em arquivo salvo pede confirmação em 2 cliques
- [ ] Redeploy → dados de `user_data/` sobrevivem (disco montado)

## Limitações conhecidas

- Header da tabela (glide-data-grid) usa um dark slate próprio do Streamlit;
  CSS vars/config.toml não alteram essa cor (verificado na versão 1.58).
- Auth de senha única = single-tenant. Para multiusuário real, ver
  `SAAS_ROADMAP.md`.
