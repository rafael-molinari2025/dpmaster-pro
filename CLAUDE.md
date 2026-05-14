# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run locally (development):**
```bash
venv\Scripts\streamlit run app_dp.py
# or with explicit port:
venv\Scripts\streamlit run app_dp.py --server.port=8501
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
# Build and start full stack (Streamlit + Nginx + Certbot)
docker compose up -d --build

# View logs
docker compose logs -f dpmaster

# Rebuild after code changes
docker compose up -d --build dpmaster
```

**VPS first-time setup:**
```bash
sudo bash deploy/setup-server.sh   # installs Docker, UFW, fail2ban
bash deploy/init-ssl.sh            # obtains Let's Encrypt certificate
bash deploy/deploy.sh              # builds and starts the stack
```

## Architecture

The entire application lives in a single file: `app_dp.py` (~5000 lines). It is a Streamlit app with no external API calls or database — all persistence is file-based JSON in `data_dp/`.

### Sections of `app_dp.py` (in order)

| Lines | Section | Purpose |
|-------|---------|---------|
| 1–51 | Imports + `st.set_page_config` | Library imports with try/except fallbacks for optional deps (plotly, cryptography) |
| 53–100 | CONFIGURAÇÕES / LOGGING | Constants (`DATA_DIR`, file paths), logging setup |
| 103–229 | SEGURANÇA | Password hashing (SHA-256 + salt), session timeout (30 min), login lockout (5 attempts / 5 min) |
| 231–252 | CRIPTOGRAFIA | Fernet symmetric encryption; key auto-generated at `data_dp/.master.key` on first run |
| 255–530 | CARREGAR / SALVAR | JSON load/save functions for all entities; `usuarios` and `funcionarios` files are Fernet-encrypted; `tabelas` and `empresa` are plain JSON |
| 374–436 | eSocial FILA | Queue of eSocial events with status lifecycle: `Pendente → Aguardando → Transmitido / Rejeitado / Cancelado` |
| 438–530 | DOCUMENTOS | Per-employee document store under `data_dp/documentos/{func_id}/` with JSON metadata sidecar |
| 532–666 | CÁLCULOS | Brazilian payroll: `calcular_inss()` (progressive table), `calcular_irrf()` (table with deduction per dependent), VT discount (6% cap), 13th-salary ávos, vacation period |
| 668–1218 | GERAÇÃO DE PDF | ReportLab-based generators: contracheque, folha analítica, rescisão, décimo, férias, ficha cadastro, ficha financeira anual, resumo folha |
| 1219–1360 | eSocial XML | Generates S-2200 (admissão), S-2299 (desligamento), S-1200 (folha), S-2230 (férias) XML files |
| 1361–1455 | UI / CSS | `inject_global_css()` — all custom CSS injected via `st.markdown(..., unsafe_allow_html=True)` |
| 1456–1556 | LOGIN / INICIALIZAÇÃO | `tela_login()`, `tem_permissao()`, default user seeding on first run |
| 1557–end | MAIN | Navigation sidebar + all page renderers as `if menu == "..."` branches |

### Data layer

All data lives in `data_dp/` (excluded from git):

| File | Format | Encrypted |
|------|--------|-----------|
| `funcionarios.json` | List of employee dicts | Yes (Fernet) |
| `usuarios.json` | List of user dicts | Yes (Fernet) |
| `tabelas.json` | INSS/IRRF rate tables | No |
| `empresa.json` | Company config | No |
| `esocial_fila.json` | eSocial event queue | No |
| `documentos/{id}/` | Employee files + metadata | No |
| `.master.key` | Fernet key (binary) | — |

**Funcionário dict key fields:**
`id`, `nome`, `cpf`, `rg`, `data_nascimento`, `data_admissao`, `cargo`, `departamento`, `salario_base`, `dependentes`, `situacao` (`"Ativo"` / outros), `vt_mensal`, `folha_pagamento` (dict keyed by `"MM/YYYY"`), `pis`, `ctps`, `banco`, `agencia`, `conta`.

**Folha entry** (`func["folha_pagamento"]["04/2026"]`): `salario_base`, `inss`, `irrf`, `vt_desc`, `outros_desc`, `outros_acr`, `liquido`.

### Permission model

Three roles, hierarchical — `tem_permissao(nivel)` returns `True` for all levels below:

- `admin` — full access including user management, logs, table config, company settings, backup
- `coordenador` — employee CRUD, payroll, ponto, 13th, vacation, rescisão, eSocial, import
- `funcionario` — read-only (own data + reports)

Default credentials on first run: `admin / 123456`, `coordenador / 123456`, `funcionario / 123456`.

### Supporting modules

- **`backup_dp.py`** — `criar_backup(motivo)` zips `data_dp/` into `data_dp_backups/backup_{motivo}_{ts}.zip`; keeps last 10 (configurable via `MAX_BACKUPS`). Auto-triggered before rescisão, exclusão, and restauração.
- **`generators/generate_manual.py`** — holds the user manual as a Python string constant `MANUAL_UTILIZACAO`, imported directly into `app_dp.py` and rendered in the "Manual do Sistema" page.

### Production stack

```
Browser → Nginx (443/SSL, Let's Encrypt) → Streamlit :8501 (Docker internal)
                                         ↘ Certbot (auto-renew every 12h)
```

Data is persisted via named Docker volumes (`dpmaster_data`, `dpmaster_backups`), not bind-mounts, so data survives container rebuilds.

### Caching note

Only `carregar_tabelas()` uses `@st.cache_data`. All other data loaders (`carregar_funcionarios`, `carregar_usuarios`, etc.) read from disk on every call — this is intentional to avoid stale data after writes.
