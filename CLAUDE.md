# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run locally (development):**
```bash
venv\Scripts\streamlit run app_dp.py
venv\Scripts\streamlit run app_dp.py --server.port=8501
```

**Regenerate technical docs PDF:**
```bash
venv\Scripts\python gerar_docs_pdf.py
```

**Run backup manually:**
```bash
venv\Scripts\python backup_dp.py
```

**Install dependencies:**
```bash
venv\Scripts\pip install -r requirements.txt
```

**Docker (production):**
```bash
docker compose up -d --build          # build and start full stack
docker compose logs -f dpmaster        # follow logs
docker compose up -d --build dpmaster  # rebuild after code changes
```

**VPS first-time setup:**
```bash
sudo bash deploy/setup-server.sh   # installs Docker, UFW, fail2ban
bash deploy/init-ssl.sh            # obtains Let's Encrypt certificate
bash deploy/deploy.sh              # builds and starts the stack
```

## Architecture

The entire application lives in `app_dp.py` (~4200 lines). It is a Streamlit app with no external API calls or database — all persistence is file-based JSON in `data_dp/` (git-ignored).

### Sections of `app_dp.py` (by line)

| Lines | Section | Purpose |
|-------|---------|---------|
| 1–45 | Imports | `try/except` fallbacks for optional deps: `plotly`, `cryptography` |
| 46–108 | CONFIGURAÇÕES / LOGGING | Constants, file path vars, `log_acao()`, monthly log rotation |
| 109–236 | SEGURANÇA | SHA-256+salt hashing, session timeout (30 min), login lockout (5 attempts / 5 min) |
| 237–273 | CRIPTOGRAFIA | Fernet AES-256 encryption; key auto-generated at `data_dp/.master.key` |
| 274–484 | CARREGAR / SALVAR | All JSON load/save functions; `usuarios` and `funcionarios` are Fernet-encrypted; multi-company helpers |
| 485–567 | eSocial FILA | Event queue with lifecycle: `Pendente → Aguardando → Transmitido / Rejeitado / Cancelado` |
| 568–664 | DOCUMENTOS | Per-employee document store under `data_dp/documentos/{func_id}/` with `_metadados.json` sidecar |
| 665–858 | CÁLCULOS | Brazilian payroll: progressive INSS table, IRRF with dependent deduction, 6%-cap VT, 13th-salary ávos, vacation period |
| 859–1445 | GERAÇÃO DE PDF | ReportLab generators: contracheque, folha analítica, rescisão, décimo, férias, ficha cadastro, ficha financeira anual, resumo folha |
| 1446–1596 | eSocial XML | S-2200 admissão, S-2299 desligamento, S-1200 folha, S-2230 férias |
| 1597–1692 | UI / CSS | `inject_global_css()` — all custom CSS via `st.markdown(unsafe_allow_html=True)` |
| 1693–1854 | LOGIN / PERMISSÕES | `tela_login()` with company selector, `tem_permissao()`, `_set_flash()` / `_show_flash()` |
| 1836–1854 | INICIALIZAÇÃO | Default user seeding on first run; `carregar_empresas()` bootstraps `empresas.json` |
| 1855–end | MAIN | Sidebar navigation + all page renderers as `if menu == "..."` branches |

### Data layer

All data lives in `data_dp/` (excluded from git):

| File | Format | Encrypted |
|------|--------|-----------|
| `funcionarios.json` | List of employee dicts | Yes (Fernet) |
| `usuarios.json` | List of user dicts | Yes (Fernet) |
| `empresas.json` | List of company dicts | No |
| `tabelas.json` | INSS/IRRF rate tables | No |
| `empresa.json` | Legacy single-company config (kept for PDF fallback) | No |
| `esocial_fila.json` | eSocial event queue | No |
| `documentos/{id}/` | Employee files + `_metadados.json` | No |
| `logs/dpmaster_YYYYMM.log` | Monthly action log | No |
| `.master.key` | Fernet key (binary) | — |

**Key fields — Funcionário dict:**
`id`, `nome`, `cpf`, `rg`, `data_nascimento`, `data_admissao`, `cargo`, `departamento`, `salario_base`, `num_dependentes`, `situacao` (`"Ativo"` / outros), `valor_vt_mensal`, `tem_plano_saude`, `valor_plano`, `empresa_id`, `folha_pagamento` (dict keyed `"MM/YYYY"`).

**Folha entry** (`func["folha_pagamento"]["04/2026"]`):
`salario_base`, `inss`, `irrf`, `vt`, `plano_saude`, `itens_extras` (list of `{tipo, descricao, valor}`), `liquido`.

### Multi-company architecture

Each employee and user has an `empresa_id` field linking them to a record in `empresas.json`. The login screen shows a company selector; after login, `st.session_state.empresa_id` and `st.session_state.empresa_nome` are set.

- **Admin global**: users stored *without* an `empresa_id` field (not `None` — the key is absent) can select any company at login and see all data without filtering.
- **Read-only pages** (Dashboard, Relatórios, eSocial): use `get_funcionarios_empresa()` which returns an already-filtered list.
- **Write pages** (Folha, 13º, Férias, Rescisão, Ponto): call `carregar_funcionarios()` (full list) for correct saves, then apply a local `_eid` filter just for the display `funcs` variable. This ensures list-item mutations propagate to the full list on save.
- On first run, existing records without `empresa_id` are auto-migrated to `empresa_id=1`.

### Permission model

`tem_permissao(nivel)` — hierarchical, returns `True` for all levels at or below the user's role:

| Role | Access |
|------|--------|
| `admin` | Everything including user management, logs, table config, company settings, backup |
| `coordenador` | Employee CRUD, payroll, ponto, 13th, vacation, rescisão, eSocial, import |
| `funcionario` | Read-only (own data + reports) |

Default credentials on first run: `admin / 123456`, `coordenador / 123456`, `funcionario / 123456`.

### Flash message pattern

`st.success()` called immediately before `st.rerun()` is never rendered. Use the bridge pattern instead:

```python
_set_flash("success", "Operação realizada com sucesso!")
st.rerun()
# At the top of the page renderer, after st.header():
_show_flash()
```

### Supporting files

| File | Purpose |
|------|---------|
| `backup_dp.py` | `criar_backup(motivo)` zips `data_dp/` → `data_dp_backups/backup_{motivo}_{ts}.zip`; keeps last 10. Auto-triggered before rescisão, exclusão, restauração. |
| `generators/generate_manual.py` | User manual as string constant `MANUAL_UTILIZACAO`; imported into `app_dp.py` and rendered on the "Manual do Sistema" page. |
| `gerar_docs_pdf.py` | Extracts docstrings from `app_dp.py` via AST and generates `documentacao_tecnica.pdf`. Re-run after adding/editing docstrings. |
| `.streamlit/config.toml` | Streamlit theme (primary `#2563eb`), XSRF enabled, upload limit 10 MB, headless mode. |
| `assets/` | App icon and branding images referenced in UI. |
| `docs/` | `changelog.md` and `manual_utilizacao.md` (static exports). |

### Production stack

```
Browser → Nginx (443/SSL, Let's Encrypt) → Streamlit :8501 (Docker internal)
                                         ↘ Certbot (auto-renew every 12h)
```

Named Docker volumes (`dpmaster_data`, `dpmaster_backups`) persist data across container rebuilds. The Dockerfile uses `python:3.11-slim` and runs as a non-root `appuser`.

### Caching

Only `carregar_tabelas()` uses `@st.cache_data`. All other loaders read from disk on every call — intentional to avoid stale data after writes.
