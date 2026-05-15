import streamlit as st
import pandas as pd
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
from datetime import date, datetime, timedelta
import json
import os
import logging
import traceback
import base64
import hashlib
import secrets
import re
import time
import zipfile
from io import BytesIO
from pathlib import Path
try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
from backup_dp import criar_backup, listar_backups, restaurar_backup

# ReportLab para geração de PDFs
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import xml.etree.ElementTree as ET
from xml.dom import minidom
from generators.generate_manual import MANUAL_UTILIZACAO

# ====================== CONFIGURAÇÕES ======================
st.set_page_config(
    page_title="DPMaster Pro — Gestão de Departamento Pessoal",
    page_icon="🏢",
    layout="wide"
)

# ── Identidade Comercial ──────────────────────────────────
SISTEMA_NOME      = "DPMaster Pro"
SISTEMA_VERSAO    = "5.0"
SISTEMA_SLOGAN    = "Excelência em Gestão de Pessoal para Pequenas Empresas"

EMPRESA_NOME      = "PrimeTI Ltda"
EMPRESA_CNPJ      = "62.938.903/0001-75"
EMPRESA_ENDERECO  = "Belo Horizonte - MG"

DATA_DIR          = "data_dp"
USUARIOS_FILE     = os.path.join(DATA_DIR, "usuarios.json")
FUNCIONARIOS_FILE = os.path.join(DATA_DIR, "funcionarios.json")
ESOCIAL_DIR       = os.path.join(DATA_DIR, "esocial")
ESOCIAL_FILA_FILE = os.path.join(DATA_DIR, "esocial_fila.json")
LOG_DIR           = os.path.join(DATA_DIR, "logs")
DOCS_DIR          = os.path.join(DATA_DIR, "documentos")  # ← novo
TABELAS_FILE      = os.path.join(DATA_DIR, "tabelas.json")
EMPRESA_FILE      = os.path.join(DATA_DIR, "empresa.json")

for d in [DATA_DIR, ESOCIAL_DIR, LOG_DIR, DOCS_DIR]:
    os.makedirs(d, exist_ok=True)

# ====================== LOGGING ======================
LOG_FILE = os.path.join(LOG_DIR, f"dpmaster_{datetime.now().strftime('%Y%m')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DPMasterPro")


def log_acao(acao: str, detalhe: str = "", nivel: str = "info"):
    usuario = ""
    if "usuario_logado" in st.session_state:
        usuario = st.session_state.usuario_logado.get("username", "?")
    msg = f"[{usuario}] {acao}"
    if detalhe:
        msg += f" | {detalhe}"
    if nivel == "error":
        logger.error(msg)
    elif nivel == "warning":
        logger.warning(msg)
    else:
        logger.info(msg)


# ====================== SEGURANÇA ======================
SESSAO_TIMEOUT_MINUTOS = 30
MAX_TENTATIVAS_LOGIN = 5
LOCKOUT_MINUTOS = 5


def gerar_hash_senha(senha: str, salt: str = None) -> tuple:
    """Gera hash SHA-256 da senha com salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    hash_val = hashlib.sha256(f"{salt}{senha}".encode('utf-8')).hexdigest()
    return hash_val, salt


def verificar_senha(senha: str, hash_armazenado: str, salt: str) -> bool:
    """Verifica se a senha corresponde ao hash armazenado."""
    hash_calc = hashlib.sha256(f"{salt}{senha}".encode('utf-8')).hexdigest()
    return secrets.compare_digest(hash_calc, hash_armazenado)


def migrar_senhas_texto_puro(usuarios: list) -> bool:
    """Migra senhas em texto puro para hash SHA-256 (executa uma vez)."""
    migrados = 0
    for u in usuarios:
        if "salt" not in u:  # Senha ainda em texto puro
            senha_texto = u.get("senha", "")
            hash_val, salt = gerar_hash_senha(senha_texto)
            u["senha"] = hash_val
            u["salt"] = salt
            migrados += 1
    if migrados > 0:
        salvar_usuarios(usuarios)
        logger.info(f"Migração de senhas: {migrados} usuário(s) atualizados para hash.")
    return migrados > 0


def validar_cpf(cpf: str) -> bool:
    """Valida CPF usando o algoritmo oficial dos dígitos verificadores."""
    cpf_limpo = re.sub(r'[^0-9]', '', cpf)
    if len(cpf_limpo) != 11:
        return False
    # Rejeitar CPFs com todos os dígitos iguais
    if cpf_limpo == cpf_limpo[0] * 11:
        return False
    # Calcular primeiro dígito verificador
    soma = sum(int(cpf_limpo[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf_limpo[9]):
        return False
    # Calcular segundo dígito verificador
    soma = sum(int(cpf_limpo[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto == 10:
        resto = 0
    if resto != int(cpf_limpo[10]):
        return False
    return True


def formatar_cpf(cpf: str) -> str:
    """Formata CPF no padrão XXX.XXX.XXX-XX."""
    cpf_limpo = re.sub(r'[^0-9]', '', cpf)
    if len(cpf_limpo) == 11:
        return f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
    return cpf


def verificar_timeout_sessao() -> bool:
    """Verifica se a sessão expirou. Retorna True se ainda válida."""
    if "sessao_inicio" not in st.session_state:
        return False
    inicio = st.session_state.sessao_inicio
    agora = datetime.now()
    if (agora - inicio).total_seconds() > SESSAO_TIMEOUT_MINUTOS * 60:
        return False
    # Renovar timestamp a cada interação
    st.session_state.sessao_ultimo_acesso = agora
    return True


def verificar_bloqueio_login(username: str) -> tuple:
    """Verifica se o usuário está bloqueado por excesso de tentativas.
    Retorna (bloqueado: bool, tempo_restante_segundos: int)."""
    if "login_tentativas" not in st.session_state:
        st.session_state.login_tentativas = {}
    info = st.session_state.login_tentativas.get(username, {})
    tentativas = info.get("count", 0)
    ultimo = info.get("ultimo", 0)
    if tentativas >= MAX_TENTATIVAS_LOGIN:
        tempo_passado = time.time() - ultimo
        tempo_lockout = LOCKOUT_MINUTOS * 60
        if tempo_passado < tempo_lockout:
            return True, int(tempo_lockout - tempo_passado)
        else:
            # Lockout expirou, resetar
            st.session_state.login_tentativas[username] = {"count": 0, "ultimo": 0}
            return False, 0
    return False, 0


def registrar_tentativa_login(username: str, sucesso: bool):
    """Registra tentativa de login."""
    if "login_tentativas" not in st.session_state:
        st.session_state.login_tentativas = {}
    if sucesso:
        st.session_state.login_tentativas[username] = {"count": 0, "ultimo": 0}
    else:
        info = st.session_state.login_tentativas.get(username, {"count": 0, "ultimo": 0})
        info["count"] = info.get("count", 0) + 1
        info["ultimo"] = time.time()
        st.session_state.login_tentativas[username] = info


def validar_forca_senha(senha: str) -> tuple:
    """Avalia a força da senha. Retorna (valida: bool, mensagem: str)."""
    if len(senha) < 6:
        return False, "A senha deve ter pelo menos 6 caracteres."
    if len(senha) < 8:
        return True, "⚠️ Senha fraca — recomenda-se 8+ caracteres com números e letras."
    tem_letra = bool(re.search(r'[a-zA-Z]', senha))
    tem_numero = bool(re.search(r'[0-9]', senha))
    if tem_letra and tem_numero:
        return True, "✅ Senha forte."
    return True, "⚠️ Senha média — adicione letras e números para mais segurança."


# ====================== CRIPTOGRAFIA (FAILSAFE) ======================
KEY_FILE = os.path.join(DATA_DIR, ".master.key")

def obter_chave_mestra():
    if not CRYPTO_AVAILABLE: return b""
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as kf:
            kf.write(key)
        return key
    with open(KEY_FILE, "rb") as kf:
        return kf.read()

def criptografar_dados(dados_json: str) -> bytes:
    if not CRYPTO_AVAILABLE: return dados_json.encode('utf-8')
    fernet = Fernet(obter_chave_mestra())
    return fernet.encrypt(dados_json.encode('utf-8'))

def descriptografar_dados(dados_cripto: bytes) -> str:
    if not CRYPTO_AVAILABLE: return dados_cripto.decode('utf-8')
    fernet = Fernet(obter_chave_mestra())
    return fernet.decrypt(dados_cripto).decode('utf-8')


# ====================== CARREGAR / SALVAR ======================
@st.cache_data
def carregar_tabelas():
    try:
        if os.path.exists(TABELAS_FILE):
            with open(TABELAS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "inss": {
                "faixas": [
                    {"limite": 1518.00, "aliquota": 0.075},
                    {"limite": 2793.88, "aliquota": 0.09},
                    {"limite": 4190.83, "aliquota": 0.12},
                    {"limite": 8157.41, "aliquota": 0.14}
                ],
                "teto_base": 8157.41
            },
            "irrf": {
                "deducao_dependente": 189.59,
                "faixas": [
                    {"limite": 2259.20, "aliquota": 0.0, "deducao": 0.0},
                    {"limite": 2826.65, "aliquota": 0.075, "deducao": 169.44},
                    {"limite": 3751.05, "aliquota": 0.15, "deducao": 381.44},
                    {"limite": 4664.68, "aliquota": 0.225, "deducao": 662.77},
                    {"limite": 99999999.0, "aliquota": 0.275, "deducao": 896.00}
                ]
            }
        }
    except Exception as e:
        logger.error(f"Erro ao carregar tabelas: {e}")
        return {}

def salvar_tabelas(dados):
    try:
        with open(TABELAS_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar tabelas: {e}")
        return False

def carregar_dados_empresa():
    try:
        if os.path.exists(EMPRESA_FILE):
            with open(EMPRESA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "nome": EMPRESA_NOME, "cnpj": EMPRESA_CNPJ, "endereco": EMPRESA_ENDERECO,
            "regime": "Simples Nacional", "aliquota_patronal": 0.0,
            "aliquota_rat": 0.0, "aliquota_terceiros": 0.0
        }
    except Exception as e:
        logger.error(f"Erro carregar_dados_empresa: {e}")
        return {}

def salvar_dados_empresa(dados):
    try:
        with open(EMPRESA_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"Erro salvar_dados_empresa: {e}")
        return False

def carregar_usuarios():
    if not os.path.exists(USUARIOS_FILE):
        return []
    try:
        with open(USUARIOS_FILE, "rb") as f:
            conteudo = f.read()
            try:
                # Tentar ler como JSON plano (migração)
                dados = json.loads(conteudo.decode('utf-8'))
                salvar_usuarios(dados) # Salvar criptografado
                return dados
            except:
                return json.loads(descriptografar_dados(conteudo))
    except Exception as e:
        logger.error(f"Erro ao carregar usuários: {e}")
        return []

def salvar_usuarios(usuarios):
    try:
        dados_json = json.dumps(usuarios, indent=4, ensure_ascii=False)
        with open(USUARIOS_FILE, "wb") as f:
            f.write(criptografar_dados(dados_json))
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar usuários: {e}")
        return False

def carregar_funcionarios():
    if not os.path.exists(FUNCIONARIOS_FILE):
        return []
    try:
        with open(FUNCIONARIOS_FILE, "rb") as f:
            conteudo = f.read()
            try:
                # Tentar ler como JSON plano (migração)
                dados = json.loads(conteudo.decode('utf-8'))
                salvar_funcionarios(dados)
                return dados
            except:
                return json.loads(descriptografar_dados(conteudo))
    except Exception as e:
        logger.error(f"Erro ao carregar funcionários: {e}")
        return []

def salvar_funcionarios(funcs):
    try:
        dados_json = json.dumps(funcs, indent=4, ensure_ascii=False)
        with open(FUNCIONARIOS_FILE, "wb") as f:
            f.write(criptografar_dados(dados_json))
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar funcionários: {e}")
        return False


# ====================== eSocial FILA ======================
def carregar_fila_esocial() -> list:
    try:
        if os.path.exists(ESOCIAL_FILA_FILE):
            with open(ESOCIAL_FILA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Erro ao carregar fila eSocial: {e}")
        return []


def salvar_fila_esocial(fila: list):
    try:
        with open(ESOCIAL_FILA_FILE, "w", encoding="utf-8") as f:
            json.dump(fila, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Erro ao salvar fila eSocial: {e}")


def adicionar_evento_fila(tipo: str, grupo: str, descricao: str,
                          func_nome: str = "", func_id: int = 0,
                          arquivo_xml: str = "", dados_extras: dict = None):
    """Adiciona um evento à fila eSocial."""
    fila = carregar_fila_esocial()
    evento = {
        "id": max([e.get("id", 0) for e in fila], default=0) + 1,
        "tipo": tipo,           # ex: "S-2200", "S-1200"
        "grupo": grupo,         # "Periódico" ou "Não Periódico"
        "descricao": descricao,
        "func_nome": func_nome,
        "func_id": func_id,
        "arquivo_xml": arquivo_xml,
        "status": "Pendente",   # Pendente | Aguardando | Transmitido | Rejeitado | Cancelado
        "protocolo": "",
        "criado_em": datetime.now().isoformat(),
        "atualizado_em": datetime.now().isoformat(),
        "dados_extras": dados_extras or {},
        "historico": [{"status": "Pendente", "data": datetime.now().isoformat(), "obs": "Evento criado"}],
    }
    fila.append(evento)
    salvar_fila_esocial(fila)
    log_acao("ESOCIAL_FILA_ADD", f"{tipo} - {func_nome} - {descricao}")
    return evento["id"]


def atualizar_status_evento(evento_id: int, novo_status: str, obs: str = "", protocolo: str = ""):
    fila = carregar_fila_esocial()
    for ev in fila:
        if ev["id"] == evento_id:
            ev["status"] = novo_status
            ev["atualizado_em"] = datetime.now().isoformat()
            if protocolo:
                ev["protocolo"] = protocolo
            ev["historico"].append({
                "status": novo_status,
                "data": datetime.now().isoformat(),
                "obs": obs or f"Status alterado para {novo_status}"
            })
            break
    salvar_fila_esocial(fila)
    log_acao("ESOCIAL_STATUS", f"ID={evento_id} → {novo_status}")


# ====================== DOCUMENTOS DE FUNCIONÁRIOS ======================
def pasta_documentos_func(func_id: int) -> str:
    pasta = os.path.join(DOCS_DIR, str(func_id))
    os.makedirs(pasta, exist_ok=True)
    return pasta


def salvar_documento_func(func_id: int, arquivo_nome: str, conteudo: bytes,
                          tipo_doc: str, descricao: str = "") -> dict:
    """Salva arquivo físico e registra metadados."""
    pasta = pasta_documentos_func(func_id)
    # Nome seguro: timestamp + nome original
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    ext = Path(arquivo_nome).suffix.lower()
    nome_seguro = f"{ts}_{arquivo_nome.replace(' ', '_')}"
    caminho = os.path.join(pasta, nome_seguro)

    with open(caminho, "wb") as f:
        f.write(conteudo)

    meta = {
        "id": hashlib.md5(f"{func_id}{ts}{arquivo_nome}".encode()).hexdigest()[:12],
        "nome_original": arquivo_nome,
        "nome_arquivo": nome_seguro,
        "caminho": caminho,
        "tipo_doc": tipo_doc,
        "descricao": descricao,
        "tamanho_bytes": len(conteudo),
        "extensao": ext,
        "enviado_em": datetime.now().isoformat(),
        "enviado_por": st.session_state.get("usuario_logado", {}).get("username", "?"),
    }

    # Registrar no JSON de metadados da pasta
    meta_file = os.path.join(pasta, "_metadados.json")
    metas = []
    if os.path.exists(meta_file):
        with open(meta_file, "r", encoding="utf-8") as mf:
            metas = json.load(mf)
    metas.append(meta)
    with open(meta_file, "w", encoding="utf-8") as mf:
        json.dump(metas, mf, ensure_ascii=False, indent=2)

    log_acao("DOC_SALVO", f"FuncID={func_id} Tipo={tipo_doc} Arquivo={arquivo_nome}")
    return meta


def carregar_metadados_docs(func_id: int) -> list:
    pasta = pasta_documentos_func(func_id)
    meta_file = os.path.join(pasta, "_metadados.json")
    if os.path.exists(meta_file):
        with open(meta_file, "r", encoding="utf-8") as mf:
            return json.load(mf)
    return []


def excluir_documento(func_id: int, doc_id: str):
    pasta = pasta_documentos_func(func_id)
    meta_file = os.path.join(pasta, "_metadados.json")
    if not os.path.exists(meta_file):
        return
    with open(meta_file, "r", encoding="utf-8") as mf:
        metas = json.load(mf)
    doc = next((m for m in metas if m["id"] == doc_id), None)
    if doc:
        if os.path.exists(doc["caminho"]):
            os.remove(doc["caminho"])
        metas = [m for m in metas if m["id"] != doc_id]
        with open(meta_file, "w", encoding="utf-8") as mf:
            json.dump(metas, mf, ensure_ascii=False, indent=2)
        log_acao("DOC_EXCLUIDO", f"FuncID={func_id} DocID={doc_id}")


TIPOS_DOCUMENTO = [
    "Contrato de Trabalho",
    "RG / Identidade",
    "CPF",
    "Comprovante de Residência",
    "Foto 3x4",
    "Carteira de Trabalho (CTPS)",
    "Título de Eleitor",
    "Certificado de Reservista",
    "Comprovante Escolaridade",
    "Atestado Médico Admissional",
    "Declaração de Dependentes",
    "Declaração de Vale-Transporte",
    "Termo Aditivo",
    "Rescisão / TRCT",
    "Outros",
]

EXTENSOES_PERMITIDAS = [".pdf", ".jpg", ".jpeg", ".png"]


# ====================== CÁLCULOS ======================
def calcular_inss(salario: float) -> float:
    try:
        if salario <= 0:
            return 0.0
        
        tabelas = carregar_tabelas()
        dados_inss = tabelas.get("inss", {})
        faixas_raw = dados_inss.get("faixas", [])
        teto_base = dados_inss.get("teto_base", 8157.41)
        
        # Converter lista de dicts para lista de tuplas (limite, aliquota)
        faixas = [(f["limite"], f["aliquota"]) for f in faixas_raw]
        
        inss = 0.0
        anterior = 0.0
        for limite, aliquota in faixas:
            if salario <= limite:
                inss += (salario - anterior) * aliquota
                break
            else:
                inss += (limite - anterior) * aliquota
                anterior = limite
        else:
            inss += (teto_base - anterior) * 0.14 # Fallback para o teto se passar de todas as faixas
            
        return max(0.0, round(inss, 2))
    except Exception as e:
        logger.error(f"Erro calcular_inss: {e}")
        return 0.0


def calcular_irrf(base: float, dependentes: int = 0) -> float:
    try:
        if base <= 0:
            return 0.0
            
        tabelas = carregar_tabelas()
        dados_irrf = tabelas.get("irrf", {})
        ded_dep_val = dados_irrf.get("deducao_dependente", 189.59)
        faixas_raw = dados_irrf.get("faixas", [])
        
        ded_dep = dependentes * ded_dep_val
        base_calc = max(0.0, base - ded_dep)
        
        # Converter lista de dicts para lista de tuplas (limite, aliquota, deducao)
        faixas = [(f["limite"], f["aliquota"], f["deducao"]) for f in faixas_raw]
        
        for limite, aliquota, deducao in faixas:
            if base_calc <= limite:
                return max(0.0, round(base_calc * aliquota - deducao, 2))
        return 0.0
    except Exception as e:
        logger.error(f"Erro calcular_irrf: {e}")
        return 0.0


def calcular_vt(salario: float, vt_mensal: float) -> float:
    try:
        if vt_mensal <= 0:
            return 0.0
        return round(min(salario * 0.06, vt_mensal), 2)
    except Exception as e:
        logger.error(f"Erro calcular_vt: {e}")
        return 0.0


def calcular_avos(data_admissao, ano: int = 2026) -> int:
    try:
        if not data_admissao:
            return 12
        adm = datetime.fromisoformat(data_admissao) if isinstance(data_admissao, str) else data_admissao
        avos = 0
        for mes in range(1, 13):
            import calendar
            ultimo_dia_num = calendar.monthrange(ano, mes)[1]
            ultimo_dia = date(ano, mes, ultimo_dia_num)
            primeiro_dia = date(ano, mes, 1)
            if adm.date() > ultimo_dia:
                continue
            inicio_real = max(adm.date(), primeiro_dia)
            dias_trabalhados = (ultimo_dia - inicio_real).days + 1
            if dias_trabalhados >= 15:
                avos += 1
        return max(1, avos)
    except Exception as e:
        logger.error(f"Erro calcular_avos: {e}")
        return 12


def calcular_periodo_aquisitivo(data_admissao, mes_pagamento: str = "04/2026"):
    try:
        if not data_admissao:
            return 12, 2026, "Sem data de admissão"
        adm = datetime.fromisoformat(data_admissao) if isinstance(data_admissao, str) else data_admissao
        mes_ref, ano_ref = map(int, mes_pagamento.split('/'))
        data_ref = date(ano_ref, mes_ref, 1)
        ano_inicio = adm.year
        while True:
            inicio_periodo = date(ano_inicio, adm.month, adm.day)
            fim_periodo = date(ano_inicio + 1, adm.month, adm.day - 1 if adm.day > 1 else 1)
            if inicio_periodo <= data_ref:
                if data_ref >= fim_periodo:
                    ano_inicio += 1
                else:
                    break
            else:
                break
        inicio_periodo = date(ano_inicio, adm.month, adm.day)
        meses = (data_ref.year - inicio_periodo.year) * 12 + (data_ref.month - inicio_periodo.month)
        if data_ref.day >= inicio_periodo.day:
            meses += 1
        meses_trabalhados = max(1, min(12, meses))
        status = "Completo (12/12)" if meses_trabalhados >= 12 else f"Proporcional ({meses_trabalhados}/12)"
        return meses_trabalhados, ano_inicio, status
    except Exception as e:
        logger.error(f"Erro calcular_periodo_aquisitivo: {e}")
        return 12, 2026, "Erro no cálculo"


def fmt_brl(valor: float) -> str:
    try:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def fmt_tamanho(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val/1024:.1f} KB"
    else:
        return f"{bytes_val/(1024*1024):.1f} MB"


def _pdf_store(sk: str, buf) -> bool:
    """Armazena BytesIO de PDF no session_state. Retorna True se gerado com sucesso."""
    if buf is not None:
        st.session_state[sk] = buf.getvalue()
        return True
    st.error("Erro ao gerar PDF. Verifique os dados e tente novamente.")
    return False


def _pdf_btn(sk: str, filename: str, label: str = "⬇️ Baixar PDF") -> None:
    """Exibe botão de download se o PDF estiver salvo no session_state."""
    if sk in st.session_state:
        st.download_button(label, data=st.session_state[sk],
                           file_name=filename, mime="application/pdf",
                           key=f"_dl_{sk}")


def _xml_store(sk: str, caminho: str) -> bool:
    """Lê arquivo XML do disco e armazena no session_state."""
    try:
        with open(caminho, "rb") as f:
            st.session_state[sk] = f.read()
        return True
    except Exception as e:
        st.error(f"Erro ao ler XML: {e}")
        return False


def _xml_btn(sk: str, filename: str, label: str = "⬇️ Baixar XML") -> None:
    """Exibe botão de download de XML se estiver salvo no session_state."""
    if sk in st.session_state:
        st.download_button(label, data=st.session_state[sk],
                           file_name=filename, mime="application/xml",
                           key=f"_dl_{sk}")


# ====================== GERAÇÃO DE PDF (ReportLab) ======================
def _estilos():
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("TituloDoc", parent=styles["Title"],
                            fontSize=14, spaceAfter=4, alignment=TA_CENTER)
    subtitulo = ParagraphStyle("Subtitulo", parent=styles["Normal"],
                               fontSize=10, spaceAfter=2, alignment=TA_CENTER)
    secao = ParagraphStyle("Secao", parent=styles["Heading2"],
                           fontSize=11, spaceBefore=8, spaceAfter=4)
    normal = styles["Normal"]
    return titulo, subtitulo, secao, normal


def _header_empresa(titulo_doc: str, referencia: str = ""):
    titulo_s, subtitulo_s, secao_s, normal_s = _estilos()
    items = [
        Paragraph(EMPRESA_NOME, titulo_s),
        Paragraph(f"CNPJ: {EMPRESA_CNPJ}  |  {EMPRESA_ENDERECO}", subtitulo_s),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2c3e50")),
        Spacer(1, 4 * mm),
        Paragraph(titulo_doc, ParagraphStyle("TDoc", fontSize=13, fontName="Helvetica-Bold",
                                              alignment=TA_CENTER, spaceAfter=2)),
    ]
    if referencia:
        items.append(Paragraph(f"Referência: {referencia}", subtitulo_s))
    items.append(Spacer(1, 4 * mm))
    return items


def _tabela_itens(dados: list, col_widths=None):
    w = col_widths or [110 * mm, 60 * mm]
    table_data = [[Paragraph(f"<b>{r[0]}</b>", getSampleStyleSheet()["Normal"]),
                   Paragraph(r[1], ParagraphStyle("Val", alignment=TA_RIGHT,
                                                   parent=getSampleStyleSheet()["Normal"]))]
                  for r in dados]
    t = Table(table_data, colWidths=w)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f4f6f8"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def gerar_contracheque_pdf(func: dict, mes: str = "04/2026") -> BytesIO:
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=20*mm, leftMargin=20*mm,
                                topMargin=15*mm, bottomMargin=15*mm)
        titulo_s, subtitulo_s, secao_s, normal_s = _estilos()
        story = _header_empresa("CONTRACHEQUE / RECIBO DE PAGAMENTO", mes)

        # Tentar obter dados já calculados da folha
        folha = func.get("folha_pagamento", {}).get(mes, {})
        
        if folha:
            salario = folha.get("salario_base", 0)
            inss = folha.get("inss", 0)
            irrf = folha.get("irrf", 0)
            vt = folha.get("vt", 0)
            plano = folha.get("plano_saude", 0)
            liquido = folha.get("liquido", 0)
            itens_extras = folha.get("itens_extras", [])
        else:
            # Fallback para cálculo padrão se não houver folha salva
            salario = func.get("salario_base", 0)
            inss = calcular_inss(salario)
            base_irrf = salario - inss
            irrf = calcular_irrf(base_irrf, func.get("num_dependentes", 0))
            vt = calcular_vt(salario, func.get("valor_vt_mensal", 0))
            plano = func.get("valor_plano", 0) if func.get("tem_plano_saude") == "Sim" else 0
            liquido = round(salario - (inss + irrf + vt + plano), 2)
            itens_extras = []

        total_prov = salario + sum(i['valor'] for i in itens_extras if i['tipo'] == "Provento")
        total_desc = inss + irrf + vt + plano + sum(i['valor'] for i in itens_extras if i['tipo'] == "Desconto")

        story.append(Paragraph("<b>DADOS DO FUNCIONÁRIO</b>", secao_s))
        story.append(_tabela_itens([
            ["Nome", func.get("nome", "")],
            ["CPF", func.get("cpf", "")],
            ["Cargo", func.get("cargo", "")],
            ["Departamento", func.get("departamento", "")],
            ["Data Admissão", func.get("data_admissao", "")],
            ["Dependentes", str(func.get("num_dependentes", 0))],
        ]))
        story.append(Spacer(1, 5*mm))
        
        story.append(Paragraph("<b>PROVENTOS</b>", secao_s))
        prov_items = [["Salário Base", fmt_brl(salario)]]
        for item in itens_extras:
            if item['tipo'] == "Provento":
                prov_items.append([item['descricao'], fmt_brl(item['valor'])])
        prov_items.append(["TOTAL PROVENTOS", fmt_brl(total_prov)])
        story.append(_tabela_itens(prov_items))
        
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph("<b>DESCONTOS</b>", secao_s))
        desc_items = []
        if inss > 0:
            desc_items.append(["INSS", fmt_brl(inss)])
        if irrf > 0:
            # Tentar recuperar base de cálculo se estiver na folha
            base_irrf = folha.get("base_irrf", salario - inss) if folha else (salario - inss)
            desc_items.append([f"IRRF (Base: {fmt_brl(base_irrf)})", fmt_brl(irrf)])
        if vt > 0:
            desc_items.append(["Vale-Transporte (desc. 6%)", fmt_brl(vt)])
        if plano > 0:
            desc_items.append(["Plano de Saúde", fmt_brl(plano)])
            
        for item in itens_extras:
            if item['tipo'] == "Desconto":
                desc_items.append([item['descricao'], fmt_brl(item['valor'])])
                
        desc_items.append(["TOTAL DESCONTOS", fmt_brl(total_desc)])
        story.append(_tabela_itens(desc_items))
        story.append(Spacer(1, 4*mm))

        # --- Seção de Bases (Novo v5.0) ---
        base_style = ParagraphStyle("Base", fontSize=8, parent=normal_s, textColor=colors.grey)
        fgts_val = total_prov * 0.08
        story.append(Paragraph(f"Base FGTS: {fmt_brl(total_prov)} | FGTS do Mês (8%): {fmt_brl(fgts_val)}", base_style))
        story.append(Spacer(1, 6*mm))

        liq_style = ParagraphStyle("Liq", fontSize=13, fontName="Helvetica-Bold",
                                    alignment=TA_CENTER, textColor=colors.HexColor("#1a5276"),
                                    borderPadding=8, spaceAfter=4)
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2c3e50")))
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph(f"SALÁRIO LÍQUIDO: {fmt_brl(liquido)}", liq_style))
        story.append(Spacer(1, 12*mm))

        ass_data = [
            [Paragraph("______________________________", normal_s),
             Paragraph("______________________________", normal_s)],
            [Paragraph(f"{EMPRESA_NOME}", ParagraphStyle("Ass", alignment=TA_CENTER, fontSize=8, parent=normal_s)),
             Paragraph(func.get("nome", ""), ParagraphStyle("Ass", alignment=TA_CENTER, fontSize=8, parent=normal_s))],
        ]
        ass_t = Table(ass_data, colWidths=[85*mm, 85*mm])
        ass_t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(ass_t)
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", normal_s))
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Erro gerar_contracheque_pdf: {e}\n{traceback.format_exc()}")
        return None


def gerar_folha_analitica_pdf(funcs: list, mes: str) -> BytesIO:
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=15*mm, leftMargin=15*mm,
                                topMargin=15*mm, bottomMargin=15*mm)
        titulo_s, subtitulo_s, secao_s, normal_s = _estilos()
        story = _header_empresa("FOLHA DE PAGAMENTO ANALÍTICA", mes)
        header = ["Funcionário", "Salário Bruto", "INSS", "IRRF", "VT", "Plano", "Outros Prov.", "Outros Desc.", "Líquido"]
        tabela = [header]
        totais = [0.0] * 8
        for func in funcs:
            folha = func.get("folha_pagamento", {}).get(mes, {})
            if not folha:
                salario = func.get("salario_base", 0)
                inss = calcular_inss(salario)
                irrf = calcular_irrf(salario - inss, func.get("num_dependentes", 0))
                vt = calcular_vt(salario, func.get("valor_vt_mensal", 0))
                plano = func.get("valor_plano", 0) if func.get("tem_plano_saude") == "Sim" else 0
                outros_p = 0.0
                outros_d = 0.0
                liquido = round(salario - inss - irrf - vt - plano, 2)
            else:
                salario = folha.get("salario_base", 0)
                inss = folha.get("inss", 0)
                irrf = folha.get("irrf", 0)
                vt = folha.get("vt", 0)
                plano = folha.get("plano_saude", 0)
                extras = folha.get("itens_extras", [])
                outros_p = sum(i['valor'] for i in extras if i['tipo'] == "Provento")
                outros_d = sum(i['valor'] for i in extras if i['tipo'] == "Desconto")
                liquido = folha.get("liquido", 0)
            
            linha = [func.get("nome", ""), fmt_brl(salario), fmt_brl(inss),
                     fmt_brl(irrf), fmt_brl(vt), fmt_brl(plano), fmt_brl(outros_p), fmt_brl(outros_d), fmt_brl(liquido)]
            tabela.append(linha)
            for i, v in enumerate([salario, inss, irrf, vt, plano, outros_p, outros_d, liquido]):
                totais[i] += v
        tabela.append(["TOTAIS", fmt_brl(totais[0]), fmt_brl(totais[1]), fmt_brl(totais[2]),
                        fmt_brl(totais[3]), fmt_brl(totais[4]), fmt_brl(totais[5]), fmt_brl(totais[6]), fmt_brl(totais[7])])
        col_w = [45*mm, 20*mm, 18*mm, 18*mm, 15*mm, 15*mm, 18*mm, 18*mm, 20*mm]
        t = Table(tabela, colWidths=col_w)
        n = len(tabela)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, n-2), [colors.HexColor("#f4f6f8"), colors.white]),
            ("BACKGROUND", (0, n-1), (-1, n-1), colors.HexColor("#1a5276")),
            ("TEXTCOLOR", (0, n-1), (-1, n-1), colors.white),
            ("FONTNAME", (0, n-1), (-1, n-1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph(f"Total de funcionários: {len(funcs)}", normal_s))
        story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", normal_s))
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Erro gerar_folha_analitica_pdf: {e}\n{traceback.format_exc()}")
        return None


def gerar_rescisao_pdf(func: dict, data_desligamento, motivo: str, valores: dict) -> BytesIO:
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=20*mm, leftMargin=20*mm,
                                topMargin=15*mm, bottomMargin=15*mm)
        titulo_s, subtitulo_s, secao_s, normal_s = _estilos()
        story = _header_empresa("TERMO DE RESCISÃO DO CONTRATO DE TRABALHO", str(data_desligamento))
        story.append(Paragraph("<b>DADOS DO VÍNCULO</b>", secao_s))
        story.append(_tabela_itens([
            ["Funcionário", func.get("nome", "")],
            ["CPF", func.get("cpf", "")],
            ["Cargo", func.get("cargo", "")],
            ["Data de Admissão", func.get("data_admissao", "")],
            ["Data de Desligamento", str(data_desligamento)],
            ["Motivo da Rescisão", motivo],
        ]))
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph("<b>VERBAS RESCISÓRIAS</b>", secao_s))
        verbas = []
        mapa = [
            ("saldo_salario", "Saldo de Salário"),
            ("ferias_vencidas", "Férias Vencidas + 1/3"),
            ("ferias_proporcionais", "Férias Proporcionais + 1/3"),
            ("decimo_proporcional", "13º Salário Proporcional"),
            ("aviso_previo", "Aviso Prévio Indenizado"),
            ("fgts_deposito", "FGTS do Período"),
            ("fgts_multa", "Multa FGTS 40%"),
        ]
        total_bruto = 0.0
        for chave, label in mapa:
            v = valores.get(chave, 0)
            if v > 0:
                verbas.append([label, fmt_brl(v)])
                total_bruto += v
        verbas.append(["TOTAL BRUTO", fmt_brl(total_bruto)])
        if valores.get("inss_rescisao", 0) > 0:
            verbas.append(["(-) INSS", fmt_brl(valores["inss_rescisao"])])
        if valores.get("irrf_rescisao", 0) > 0:
            verbas.append(["(-) IRRF", fmt_brl(valores["irrf_rescisao"])])
        story.append(_tabela_itens(verbas))
        story.append(Spacer(1, 5*mm))
        liq_style = ParagraphStyle("Liq", fontSize=13, fontName="Helvetica-Bold",
                                    alignment=TA_CENTER, textColor=colors.HexColor("#1a5276"), spaceAfter=4)
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2c3e50")))
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph(f"TOTAL LÍQUIDO A RECEBER: {fmt_brl(valores.get('liquido', 0))}", liq_style))
        story.append(Spacer(1, 8*mm))
        story.append(Paragraph("Esta rescisão está sujeita à homologação conforme legislação vigente.",
                                ParagraphStyle("Obs", fontSize=8, parent=normal_s, textColor=colors.grey)))
        story.append(Spacer(1, 10*mm))
        ass_data = [
            [Paragraph("______________________________", normal_s),
             Paragraph("______________________________", normal_s)],
            [Paragraph(f"Representante — {EMPRESA_NOME}",
                       ParagraphStyle("Ass", alignment=TA_CENTER, fontSize=8, parent=normal_s)),
             Paragraph(f"Funcionário — {func.get('nome', '')}",
                       ParagraphStyle("Ass", alignment=TA_CENTER, fontSize=8, parent=normal_s))],
        ]
        ass_t = Table(ass_data, colWidths=[85*mm, 85*mm])
        ass_t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(ass_t)
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", normal_s))
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Erro gerar_rescisao_pdf: {e}\n{traceback.format_exc()}")
        return None


def gerar_decimo_pdf(func: dict, ano: int, tipo: str, valor: float, avos: int = 12) -> BytesIO:
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=20*mm, leftMargin=20*mm,
                                topMargin=15*mm, bottomMargin=15*mm)
        titulo_s, subtitulo_s, secao_s, normal_s = _estilos()
        story = _header_empresa(f"13º SALÁRIO — {tipo.upper()}", str(ano))
        story.append(Paragraph("<b>DADOS DO FUNCIONÁRIO</b>", secao_s))
        story.append(_tabela_itens([
            ["Nome", func.get("nome", "")],
            ["CPF", func.get("cpf", "")],
            ["Cargo", func.get("cargo", "")],
            ["Salário Base", fmt_brl(func.get("salario_base", 0))],
        ]))
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph("<b>CÁLCULO</b>", secao_s))
        inss_13 = calcular_inss(valor) if tipo.lower() == "final" else 0.0
        irrf_13 = calcular_irrf(valor - inss_13, func.get("num_dependentes", 0)) if tipo.lower() == "final" else 0.0
        liquido_13 = round(valor - inss_13 - irrf_13, 2)
        itens = [
            ["Salário Base", fmt_brl(func.get("salario_base", 0))],
            [f"Avos Trabalhados ({avos}/12)", ""],
            ["Valor Bruto 13º", fmt_brl(valor)],
        ]
        if inss_13 > 0:
            itens.append(["(-) INSS", fmt_brl(inss_13)])
        if irrf_13 > 0:
            itens.append(["(-) IRRF", fmt_brl(irrf_13)])
        itens.append(["VALOR LÍQUIDO", fmt_brl(liquido_13)])
        story.append(_tabela_itens(itens))
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", normal_s))
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Erro gerar_decimo_pdf: {e}\n{traceback.format_exc()}")
        return None


def gerar_ferias_pdf(func: dict, mes: str, valores_ferias: dict) -> BytesIO:
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=20*mm, leftMargin=20*mm,
                                topMargin=15*mm, bottomMargin=15*mm)
        titulo_s, subtitulo_s, secao_s, normal_s = _estilos()
        story = _header_empresa("RECIBO DE FÉRIAS", mes)
        story.append(Paragraph("<b>DADOS DO FUNCIONÁRIO</b>", secao_s))
        story.append(_tabela_itens([
            ["Nome", func.get("nome", "")],
            ["CPF", func.get("cpf", "")],
            ["Cargo", func.get("cargo", "")],
            ["Data Admissão", func.get("data_admissao", "")],
            ["Período Aquisitivo", valores_ferias.get("status_periodo", "")],
        ]))
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph("<b>CÁLCULO DAS FÉRIAS</b>", secao_s))
        itens = [
            ["Dias de Férias", str(valores_ferias.get("dias_ferias", 30))],
            ["Férias Base", fmt_brl(valores_ferias.get("ferias_base", 0))],
            ["1/3 Constitucional", fmt_brl(valores_ferias.get("terco", 0))],
        ]
        if valores_ferias.get("dias_abono", 0) > 0:
            itens.append([f"Abono Pecuniário ({valores_ferias['dias_abono']} dias)",
                          fmt_brl(valores_ferias.get("abono_total", 0))])
        if valores_ferias.get("decimo_ferias", 0) > 0:
            itens.append(["13º nas Férias (1/12)", fmt_brl(valores_ferias.get("decimo_ferias", 0))])
        itens.append(["TOTAL BRUTO", fmt_brl(valores_ferias.get("total_bruto", 0))])
        if valores_ferias.get("inss_ferias", 0) > 0:
            itens.append(["(-) INSS", fmt_brl(valores_ferias["inss_ferias"])])
        if valores_ferias.get("irrf_ferias", 0) > 0:
            itens.append(["(-) IRRF", fmt_brl(valores_ferias["irrf_ferias"])])
        itens.append(["TOTAL LÍQUIDO", fmt_brl(valores_ferias.get("total_liquido", 0))])
        story.append(_tabela_itens(itens))
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", normal_s))
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Erro gerar_ferias_pdf: {e}\n{traceback.format_exc()}")
        return None


def gerar_ficha_cadastro_pdf(func: dict) -> BytesIO:
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=20*mm, leftMargin=20*mm,
                                topMargin=15*mm, bottomMargin=15*mm)
        titulo_s, subtitulo_s, secao_s, normal_s = _estilos()
        story = _header_empresa("FICHA DE CADASTRO — FUNCIONÁRIO",
                                f"Emitido em {datetime.now().strftime('%d/%m/%Y')}")
        story.append(Paragraph("<b>DADOS PESSOAIS</b>", secao_s))
        story.append(_tabela_itens([
            ["Nome Completo", func.get("nome", "")],
            ["CPF", func.get("cpf", "")],
            ["RG", func.get("rg", "")],
            ["Data de Nascimento", func.get("data_nascimento", "")],
        ]))
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph("<b>DADOS PROFISSIONAIS</b>", secao_s))
        story.append(_tabela_itens([
            ["Cargo", func.get("cargo", "")],
            ["Departamento", func.get("departamento", "")],
            ["Data de Admissão", func.get("data_admissao", "")],
            ["Situação", func.get("situacao", "Ativo")],
            ["Salário Base", fmt_brl(func.get("salario_base", 0))],
            ["Número de Dependentes", str(func.get("num_dependentes", 0))],
        ]))
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph("<b>BENEFÍCIOS</b>", secao_s))
        story.append(_tabela_itens([
            ["Plano de Saúde", func.get("tem_plano_saude", "Não")],
            ["Valor Plano Saúde", fmt_brl(func.get("valor_plano", 0))],
            ["Vale-Transporte Mensal", fmt_brl(func.get("valor_vt_mensal", 0))],
        ]))

        # Documentos arquivados
        docs = carregar_metadados_docs(func.get("id", 0))
        if docs:
            story.append(Spacer(1, 4*mm))
            story.append(Paragraph("<b>DOCUMENTOS ARQUIVADOS</b>", secao_s))
            doc_itens = [[d["tipo_doc"], d["nome_original"]] for d in docs]
            story.append(_tabela_itens(doc_itens))

        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", normal_s))
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Erro gerar_ficha_cadastro_pdf: {e}\n{traceback.format_exc()}")
        return None


def gerar_ficha_financeira_anual_pdf(func: dict, ano: int) -> BytesIO:
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=15*mm, leftMargin=15*mm,
                                topMargin=15*mm, bottomMargin=15*mm)
        titulo_s, subtitulo_s, secao_s, normal_s = _estilos()
        story = _header_empresa(f"FICHA FINANCEIRA ANUAL — {ano}", func.get("nome", ""))
        meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                       "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        header = ["Mês", "Sal. Bruto", "INSS", "IRRF", "VT", "Plano", "Líquido"]
        tabela = [header]
        totais = [0.0] * 6
        for i, nome_mes in enumerate(meses_nomes, 1):
            chave = f"{i:02d}/{ano}"
            folha = func.get("folha_pagamento", {}).get(chave, {})
            if folha:
                sb = folha.get("salario_base", 0)
                in_ = folha.get("inss", 0)
                ir = folha.get("irrf", 0)
                vt = folha.get("vt", 0)
                pl = folha.get("plano_saude", 0)
                lq = folha.get("liquido", 0)
            else:
                sb = in_ = ir = vt = pl = lq = 0.0
            tabela.append([nome_mes, fmt_brl(sb), fmt_brl(in_), fmt_brl(ir),
                           fmt_brl(vt), fmt_brl(pl), fmt_brl(lq)])
            for j, v in enumerate([sb, in_, ir, vt, pl, lq]):
                totais[j] += v
        tabela.append(["TOTAL", fmt_brl(totais[0]), fmt_brl(totais[1]),
                        fmt_brl(totais[2]), fmt_brl(totais[3]),
                        fmt_brl(totais[4]), fmt_brl(totais[5])])
        col_w = [18*mm, 27*mm, 24*mm, 24*mm, 20*mm, 20*mm, 26*mm]
        t = Table(tabela, colWidths=col_w)
        n = len(tabela)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, n-2), [colors.HexColor("#f4f6f8"), colors.white]),
            ("BACKGROUND", (0, n-1), (-1, n-1), colors.HexColor("#1a5276")),
            ("TEXTCOLOR", (0, n-1), (-1, n-1), colors.white),
            ("FONTNAME", (0, n-1), (-1, n-1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", normal_s))
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Erro gerar_ficha_financeira_anual_pdf: {e}\n{traceback.format_exc()}")
        return None


def gerar_resumo_folha_pdf(funcs: list, mes: str) -> BytesIO:
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=20*mm, leftMargin=20*mm,
                                topMargin=15*mm, bottomMargin=15*mm)
        titulo_s, subtitulo_s, secao_s, normal_s = _estilos()
        story = _header_empresa("RESUMO GERAL DA FOLHA DE PAGAMENTO", mes)
        
        empresa = carregar_dados_empresa()
        regime = empresa.get("regime", "Simples Nacional")
        aliq_patronal = empresa.get("aliquota_patronal", 20.0) / 100
        aliq_rat = empresa.get("aliquota_rat", 2.0) / 100
        aliq_terc = empresa.get("aliquota_terceiros", 5.8) / 100
        
        total_b = total_inss = total_irrf = total_vt = total_pl = total_lq = 0.0
        for func in funcs:
            folha = func.get("folha_pagamento", {}).get(mes, {})
            sb = folha.get("salario_base", func.get("salario_base", 0)) if folha else func.get("salario_base", 0)
            in_ = folha.get("inss", calcular_inss(sb)) if folha else calcular_inss(sb)
            ir = folha.get("irrf", 0) if folha else calcular_irrf(sb - in_, func.get("num_dependentes", 0))
            vt = folha.get("vt", 0) if folha else calcular_vt(sb, func.get("valor_vt_mensal", 0))
            pl = folha.get("plano_saude", 0) if folha else (func.get("valor_plano", 0) if func.get("tem_plano_saude") == "Sim" else 0)
            lq = folha.get("liquido", 0) if folha else round(sb - in_ - ir - vt - pl, 2)
            total_b += sb; total_inss += in_; total_irrf += ir
            total_vt += vt; total_pl += pl; total_lq += lq
        
        total_encargos = total_b * (aliq_patronal + aliq_rat + aliq_terc)
        total_fgts = total_b * 0.08
        
        story.append(Paragraph("<b>TOTALIZADORES</b>", secao_s))
        story.append(_tabela_itens([
            ["Número de Funcionários", str(len(funcs))],
            ["Total Salários Brutos", fmt_brl(total_b)],
            ["Total INSS (funcionários)", fmt_brl(total_inss)],
            ["Total IRRF", fmt_brl(total_irrf)],
            ["Total Vale-Transporte", fmt_brl(total_vt)],
            ["Total Plano de Saúde", fmt_brl(total_pl)],
            ["Total Líquido a Pagar", fmt_brl(total_lq)],
            [f"Total Encargos Patronais ({regime})", fmt_brl(round(total_encargos, 2))],
            ["Total FGTS Patronal (8%)", fmt_brl(round(total_fgts, 2))],
            ["<b>CUSTO TOTAL DA FOLHA</b>", fmt_brl(round(total_b + total_encargos + total_fgts, 2))],
        ]))
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", normal_s))
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Erro gerar_resumo_folha_pdf: {e}\n{traceback.format_exc()}")
        return None


# ====================== eSocial XML ======================
def gerar_xml_admissao(func: dict):
    try:
        root = ET.Element("eSocial", xmlns="http://www.esocial.gov.br/schema/evt/evtAdmissao/v03_01_00_00")
        evt = ET.SubElement(root, "evtAdmissao", Id=f"ID1{datetime.now().strftime('%Y%m%d%H%M%S')}")
        ideEvento = ET.SubElement(evt, "ideEvento")
        ET.SubElement(ideEvento, "tpAmb").text = "2"
        ET.SubElement(ideEvento, "procEmi").text = "1"
        ET.SubElement(ideEvento, "verProc").text = "1.0"
        ideEmpregador = ET.SubElement(evt, "ideEmpregador")
        ET.SubElement(ideEmpregador, "tpInsc").text = "1"
        ET.SubElement(ideEmpregador, "nrInsc").text = EMPRESA_CNPJ.replace(".", "").replace("/", "").replace("-", "")
        trabalhador = ET.SubElement(evt, "trabalhador")
        ET.SubElement(trabalhador, "cpfTrab").text = func.get("cpf", "").replace(".", "").replace("-", "")
        ET.SubElement(trabalhador, "nmTrab").text = func.get("nome", "")
        ET.SubElement(trabalhador, "dtNascto").text = func.get("data_nascimento", "1990-01-01")
        vinculo = ET.SubElement(evt, "vinculo")
        ET.SubElement(vinculo, "matricula").text = str(func.get("id", ""))
        ET.SubElement(vinculo, "dtAdm").text = func.get("data_admissao", str(date.today()))
        ET.SubElement(vinculo, "cargo").text = func.get("cargo", "")
        remuneracao = ET.SubElement(vinculo, "remuneracao")
        ET.SubElement(remuneracao, "vrSalFx").text = str(func.get("salario_base", 0))
        ET.SubElement(remuneracao, "undSalFixo").text = "5"
        xml_str = minidom.parseString(ET.tostring(root, encoding="unicode")).toprettyxml(indent="  ")
        nome_arq = f"eSocial_S2200_{func.get('nome','').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xml"
        caminho = os.path.join(ESOCIAL_DIR, nome_arq)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(xml_str)
        return caminho, nome_arq, xml_str
    except Exception as e:
        logger.error(f"Erro gerar_xml_admissao: {e}")
        st.error(f"Erro ao gerar XML: {e}")
        return None, None, None


def gerar_xml_desligamento(func: dict, data_desligamento, motivo: str):
    try:
        root = ET.Element("eSocial", xmlns="http://www.esocial.gov.br/schema/evt/evtDeslig/v03_01_00_00")
        evt = ET.SubElement(root, "evtDeslig", Id=f"ID1{datetime.now().strftime('%Y%m%d%H%M%S')}")
        ideEvento = ET.SubElement(evt, "ideEvento")
        ET.SubElement(ideEvento, "tpAmb").text = "2"
        ET.SubElement(ideEvento, "procEmi").text = "1"
        ET.SubElement(ideEvento, "verProc").text = "1.0"
        ideEmpregador = ET.SubElement(evt, "ideEmpregador")
        ET.SubElement(ideEmpregador, "tpInsc").text = "1"
        ET.SubElement(ideEmpregador, "nrInsc").text = EMPRESA_CNPJ.replace(".", "").replace("/", "").replace("-", "")
        ideVinculo = ET.SubElement(evt, "ideVinculo")
        ET.SubElement(ideVinculo, "cpfTrab").text = func.get("cpf", "").replace(".", "").replace("-", "")
        ET.SubElement(ideVinculo, "matricula").text = str(func.get("id", ""))
        infoDeslig = ET.SubElement(evt, "infoDeslig")
        ET.SubElement(infoDeslig, "dtDeslig").text = str(data_desligamento)
        cod = "01" if "sem Justa Causa" in motivo else "02" if "Pedido" in motivo else "01"
        ET.SubElement(infoDeslig, "mtvDeslig").text = cod
        xml_str = minidom.parseString(ET.tostring(root, encoding="unicode")).toprettyxml(indent="  ")
        nome_arq = f"eSocial_S2299_{func.get('nome','').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xml"
        caminho = os.path.join(ESOCIAL_DIR, nome_arq)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(xml_str)
        return caminho, nome_arq, xml_str
    except Exception as e:
        logger.error(f"Erro gerar_xml_desligamento: {e}")
        return None, None, None


def gerar_xml_folha_pagamento(funcs: list, mes: str):
    """S-1200 — Remuneração do Trabalhador (evento periódico)."""
    try:
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        root = ET.Element("eSocial", xmlns="http://www.esocial.gov.br/schema/evt/evtRemun/v03_01_00_00")
        evt = ET.SubElement(root, "evtRemun", Id=f"ID1{ts}")
        ideEvento = ET.SubElement(evt, "ideEvento")
        ET.SubElement(ideEvento, "indRetif").text = "1"
        ET.SubElement(ideEvento, "perApur").text = mes.replace("/", "-")[:7]
        ET.SubElement(ideEvento, "tpAmb").text = "2"
        ET.SubElement(ideEvento, "procEmi").text = "1"
        ET.SubElement(ideEvento, "verProc").text = "1.0"
        ideEmpregador = ET.SubElement(evt, "ideEmpregador")
        ET.SubElement(ideEmpregador, "tpInsc").text = "1"
        ET.SubElement(ideEmpregador, "nrInsc").text = EMPRESA_CNPJ.replace(".", "").replace("/", "").replace("-", "")
        for func in funcs:
            folha = func.get("folha_pagamento", {}).get(mes, {})
            if not folha:
                continue
            dmDev = ET.SubElement(evt, "dmDev")
            ET.SubElement(dmDev, "ideDmDev").text = f"M{mes.replace('/', '')}"
            ET.SubElement(dmDev, "codCateg").text = "101"
            ideTrabalhador = ET.SubElement(dmDev, "ideTrabalhador")
            ET.SubElement(ideTrabalhador, "cpfTrab").text = func.get("cpf", "").replace(".", "").replace("-", "")
            infoPerApur = ET.SubElement(dmDev, "infoPerApur")
            ideEstabLot = ET.SubElement(infoPerApur, "ideEstabLot")
            ET.SubElement(ideEstabLot, "tpInsc").text = "1"
            ET.SubElement(ideEstabLot, "nrInsc").text = EMPRESA_CNPJ.replace(".", "").replace("/", "").replace("-", "")
            ET.SubElement(ideEstabLot, "codLotacao").text = func.get("departamento", "GERAL")[:20]
            detVerbas = ET.SubElement(ideEstabLot, "detVerbas")
            ET.SubElement(detVerbas, "codRubr").text = "0001"
            ET.SubElement(detVerbas, "ideTabRubr").text = "S"
            ET.SubElement(detVerbas, "qtdRubr").text = "1"
            ET.SubElement(detVerbas, "vrRubr").text = str(folha.get("salario_base", 0))

        xml_str = minidom.parseString(ET.tostring(root, encoding="unicode")).toprettyxml(indent="  ")
        nome_arq = f"eSocial_S1200_{mes.replace('/', '')}_{ts}.xml"
        caminho = os.path.join(ESOCIAL_DIR, nome_arq)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(xml_str)
        return caminho, nome_arq, xml_str
    except Exception as e:
        logger.error(f"Erro gerar_xml_folha: {e}")
        return None, None, None


def gerar_xml_ferias(func: dict, mes: str, valores_ferias: dict):
    """S-2230 — Afastamento Temporário (Férias)."""
    try:
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        root = ET.Element("eSocial", xmlns="http://www.esocial.gov.br/schema/evt/evtAfastTemp/v03_01_00_00")
        evt = ET.SubElement(root, "evtAfastTemp", Id=f"ID1{ts}")
        ideEvento = ET.SubElement(evt, "ideEvento")
        ET.SubElement(ideEvento, "indRetif").text = "1"
        ET.SubElement(ideEvento, "tpAmb").text = "2"
        ET.SubElement(ideEvento, "procEmi").text = "1"
        ET.SubElement(ideEvento, "verProc").text = "1.0"
        ideEmpregador = ET.SubElement(evt, "ideEmpregador")
        ET.SubElement(ideEmpregador, "tpInsc").text = "1"
        ET.SubElement(ideEmpregador, "nrInsc").text = EMPRESA_CNPJ.replace(".", "").replace("/", "").replace("-", "")
        ideVinculo = ET.SubElement(evt, "ideVinculo")
        ET.SubElement(ideVinculo, "cpfTrab").text = func.get("cpf", "").replace(".", "").replace("-", "")
        ET.SubElement(ideVinculo, "matricula").text = str(func.get("id", ""))
        infoAfastamento = ET.SubElement(evt, "infoAfastamento")
        inicio = ET.SubElement(infoAfastamento, "iniAfastamento")
        ET.SubElement(inicio, "dtIniAfast").text = f"{mes[-4:]}-{mes[:2]}-01"
        ET.SubElement(inicio, "codMotAfast").text = "15"  # Férias
        xml_str = minidom.parseString(ET.tostring(root, encoding="unicode")).toprettyxml(indent="  ")
        nome_arq = f"eSocial_S2230_{func.get('nome','').replace(' ','_')}_{ts}.xml"
        caminho = os.path.join(ESOCIAL_DIR, nome_arq)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(xml_str)
        return caminho, nome_arq, xml_str
    except Exception as e:
        logger.error(f"Erro gerar_xml_ferias: {e}")
        return None, None, None


# ====================== UI / CSS ======================
def inject_global_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700&display=swap');

    :root {
        --primary:    #2563eb;
        --text-main:  #1e293b;
        --text-muted: #475569;
    }

    /* Tipografia */
    .stApp { font-family: 'Inter', sans-serif; }
    h1,h2,h3,h4,h5,h6 {
        font-family: 'Outfit',sans-serif !important;
        color: #0f172a !important;
        font-weight: 700 !important;
    }

    /* Cards Métrica */
    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.9);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(203,213,225,0.7);
        padding: 1.4rem !important;
        border-radius: 18px !important;
        box-shadow: 0 4px 16px rgba(0,0,0,0.06);
        transition: all 0.3s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 28px rgba(0,0,0,0.10);
        border-color: #2563eb;
    }
    [data-testid="stMetricLabel"] { color: #475569 !important; font-weight: 500 !important; }
    [data-testid="stMetricValue"] { color: #0f172a !important; font-weight: 700 !important; }

    /* Alertas */
    div[data-testid="stAlert"] { border-radius: 12px !important; }

    /* Botões */
    .stButton > button       { border-radius: 10px !important; font-weight: 600 !important; transition: all 0.25s ease !important; }
    .stDownloadButton > button { border-radius: 8px !important; font-weight: 600 !important; }

    /* ── SIDEBAR ESCURA ── */
    section[data-testid="stSidebar"] {
        background-color: #0f172a !important;
        box-shadow: 4px 0 12px rgba(0,0,0,0.15);
    }
    section[data-testid="stSidebar"] * { color: #f1f5f9 !important; }
    section[data-testid="stSidebar"] .stButton > button {
        background-color: rgba(255,255,255,0.07) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        color: #f1f5f9 !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: rgba(255,255,255,0.14) !important;
        border-color: #2563eb !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] > div {
        background-color: rgba(255,255,255,0.09) !important;
        border-color: rgba(255,255,255,0.18) !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] * { color: #f1f5f9 !important; }

    /* Notificações dashboard */
    .notification-card {
        padding: 14px 18px; background: #fff;
        border-left: 5px solid #2563eb; border-radius: 12px;
        margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        color: #1e293b; transition: transform 0.2s;
    }
    .notification-card:hover   { transform: scale(1.015); }
    .notification-birthday     { border-left-color: #ec4899; background: #fff1f2; }
    .notification-probation    { border-left-color: #f59e0b; background: #fffbeb; }
    .notification-vacation     { border-left-color: #10b981; background: #f0fdf4; }

    /* Tabelas */
    .stDataFrame, [data-testid="stTable"] {
        border-radius: 12px !important;
        overflow: hidden !important;
        border: 1px solid #e2e8f0 !important;
    }

    /* Expanders */
    div[data-testid="stExpander"] {
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        background-color: rgba(255,255,255,0.7) !important;
    }

    </style>
    """, unsafe_allow_html=True)

# ====================== LOGIN / PERMISSÕES ======================
def tela_login():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Source+Sans+3:wght@300;400;600&display=swap');
    .login-brand { font-family: 'Playfair Display', serif; font-size: 2.6rem;
                   color: #1a3a5c; letter-spacing: -1px; text-align: center; }
    .login-slogan { font-family: 'Source Sans 3', sans-serif; font-size: 0.95rem;
                    color: #607080; text-align: center; margin-bottom: 2rem; }
    .login-version { font-family: 'Source Sans 3', sans-serif; font-size: 0.75rem;
                     color: #a0b0c0; text-align: center; }
    .login-security { font-family: 'Source Sans 3', sans-serif; font-size: 0.7rem;
                      color: #90a0b0; text-align: center; margin-top: 1rem; }
    </style>
    """, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(f'<p class="login-brand">🏢 {SISTEMA_NOME}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="login-slogan">{SISTEMA_SLOGAN}</p>', unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Usuário", placeholder="Digite seu usuário")
            senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            if st.form_submit_button("Entrar →", type="primary", use_container_width=True):
                if not username or not senha:
                    st.error("Preencha usuário e senha.")
                else:
                    # Verificar bloqueio por excesso de tentativas
                    bloqueado, tempo_rest = verificar_bloqueio_login(username.lower())
                    if bloqueado:
                        minutos = tempo_rest // 60
                        segundos = tempo_rest % 60
                        st.error(f"🔒 Conta bloqueada por excesso de tentativas. Tente novamente em {minutos}min {segundos}s.")
                        log_acao("LOGIN_BLOQUEADO", f"Usuário: {username}", nivel="warning")
                    else:
                        usuarios = carregar_usuarios()
                        # Migrar senhas em texto puro (primeira execução após atualização)
                        migrar_senhas_texto_puro(usuarios)
                        
                        login_ok = False
                        for u in usuarios:
                            if u.get("username", "").lower() == username.lower():
                                # Verificar senha com hash
                                if "salt" in u:
                                    if verificar_senha(senha, u["senha"], u["salt"]):
                                        login_ok = True
                                else:
                                    # Fallback para texto puro (não deveria ocorrer após migração)
                                    if u.get("senha") == senha:
                                        login_ok = True
                                
                                if login_ok:
                                    st.session_state.usuario_logado = u
                                    st.session_state.sessao_inicio = datetime.now()
                                    st.session_state.sessao_ultimo_acesso = datetime.now()
                                    registrar_tentativa_login(username.lower(), True)
                                    log_acao("LOGIN", f"Login bem-sucedido: {username}")
                                    st.success(f"Bem-vindo, {u['nome']}!")
                                    st.rerun()
                                break
                        
                        if not login_ok:
                            registrar_tentativa_login(username.lower(), False)
                            tentativas_rest = MAX_TENTATIVAS_LOGIN - st.session_state.login_tentativas.get(
                                username.lower(), {}).get("count", 0)
                            logger.warning(f"Login falhou: {username}")
                            if tentativas_rest > 0:
                                st.error(f"Usuário ou senha incorretos! ({tentativas_rest} tentativa(s) restante(s))")
                            else:
                                st.error(f"🔒 Conta bloqueada por {LOCKOUT_MINUTOS} minutos.")
        st.markdown(f'<p class="login-version">{SISTEMA_NOME} v{SISTEMA_VERSAO}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="login-security">🔒 Conexão segura | Sessão expira em {SESSAO_TIMEOUT_MINUTOS} min</p>', unsafe_allow_html=True)


def tem_permissao(nivel: str) -> bool:
    if "usuario_logado" not in st.session_state:
        return False
    perfil = st.session_state.usuario_logado.get("perfil", "")
    if perfil == "admin":
        return True
    if perfil == "coordenador" and nivel in ["coordenador", "visualizar"]:
        return True
    if perfil == "funcionario" and nivel == "visualizar":
        return True
    return False


# ====================== INICIALIZAÇÃO ======================
if not os.path.exists(USUARIOS_FILE):
    usuarios_iniciais = []
    for uid, nome, uname, perfil_init in [
        (1, "Administrador",    "admin",       "admin"),
        (2, "Coordenador RH",   "coordenador", "coordenador"),
        (3, "Funcionário Teste", "funcionario", "funcionario"),
    ]:
        hash_val, salt = gerar_hash_senha("123456")
        usuarios_iniciais.append({
            "id": uid, "nome": nome, "username": uname,
            "senha": hash_val, "salt": salt, "perfil": perfil_init
        })
    salvar_usuarios(usuarios_iniciais)

# ====================== MAIN ======================
inject_global_css()

if "usuario_logado" not in st.session_state:
    tela_login()
else:
    # ── Verificar timeout de sessão ──
    if not verificar_timeout_sessao():
        log_acao("SESSAO_EXPIRADA", "Sessão expirou por inatividade")
        for key in ["usuario_logado", "sessao_inicio", "sessao_ultimo_acesso"]:
            st.session_state.pop(key, None)
        st.warning(f"⏰ Sua sessão expirou após {SESSAO_TIMEOUT_MINUTOS} minutos de inatividade. Faça login novamente.")
        tela_login()
        st.stop()

    usuario = st.session_state.usuario_logado
    perfil  = usuario.get("perfil", "funcionario")

    # ─── Sidebar ────────────────────────────────────────────────
    st.sidebar.markdown(f"### 🏢 {SISTEMA_NOME}")
    st.sidebar.markdown(f"*{SISTEMA_SLOGAN}*")
    st.sidebar.divider()
    st.sidebar.success(f"👤 {usuario['nome']} ({perfil.upper()})")

    # Botão de logout
    if st.sidebar.button("🚪 Sair"):
        log_acao("LOGOUT", usuario['username'])
        for key in ["usuario_logado", "sessao_inicio", "sessao_ultimo_acesso"]:
            st.session_state.pop(key, None)
        st.rerun()

    # ── Alterar Senha ──
    with st.sidebar.expander("🔑 Alterar Senha"):
        with st.form("form_alterar_senha"):
            senha_atual = st.text_input("Senha Atual", type="password", key="pwd_atual")
            senha_nova = st.text_input("Nova Senha", type="password", key="pwd_nova")
            senha_confirma = st.text_input("Confirmar Nova Senha", type="password", key="pwd_confirma")
            if st.form_submit_button("Alterar"):
                if not senha_atual or not senha_nova:
                    st.error("Preencha todos os campos.")
                elif senha_nova != senha_confirma:
                    st.error("A nova senha e a confirmação não coincidem.")
                else:
                    valida, msg_forca = validar_forca_senha(senha_nova)
                    if not valida:
                        st.error(msg_forca)
                    else:
                        usuarios_lst = carregar_usuarios()
                        u_atual = next((u for u in usuarios_lst if u["username"] == usuario["username"]), None)
                        if u_atual:
                            # Verificar senha atual
                            if "salt" in u_atual:
                                senha_ok = verificar_senha(senha_atual, u_atual["senha"], u_atual["salt"])
                            else:
                                senha_ok = (u_atual.get("senha") == senha_atual)
                            if not senha_ok:
                                st.error("Senha atual incorreta.")
                            else:
                                hash_novo, salt_novo = gerar_hash_senha(senha_nova)
                                u_atual["senha"] = hash_novo
                                u_atual["salt"] = salt_novo
                                salvar_usuarios(usuarios_lst)
                                log_acao("SENHA_ALTERADA", f"Usuário: {usuario['username']}")
                                st.success("✅ Senha alterada com sucesso!")
                                st.info(msg_forca)

    # ── Backup Rápido (admin) ──
    if tem_permissao("admin"):
        with st.sidebar.expander("💾 Backup"):
            if st.button("📦 Criar Backup Agora", key="btn_backup_sidebar"):
                resultado = criar_backup(motivo="manual")
                if resultado:
                    st.success(f"✅ Backup criado!")
                else:
                    st.error("Erro ao criar backup.")
            backups = listar_backups()
            if backups:
                st.caption(f"Último: {backups[0]['data']} ({backups[0]['tamanho_legivel']})")

    st.sidebar.divider()

    menu_opcoes = ["🏠 Dashboard", "📖 Manual do Sistema"]
    
    if tem_permissao("admin"):

        menu_opcoes.append("👥 Gerenciar Usuários")
    
    if tem_permissao("coordenador"):
        menu_opcoes.extend([
            "👤 Cadastro de Funcionários",
            "💰 Folha de Pagamento",
            "🕒 Gestão de Ponto",
            "🎄 13º Salário",
            "🏖️ Férias",
            "⚖️ Rescisão",
            "📤 eSocial — Painel de Transmissão",
            "📥 Importação de Dados",
        ])
    
    menu_opcoes.append("📄 Relatórios")
    
    if tem_permissao("admin"):
        menu_opcoes.append("📋 Logs do Sistema")
        menu_opcoes.append("⚙️ Configuração de Tabelas")
        menu_opcoes.append("🏢 Configurações da Empresa")
        menu_opcoes.append("💾 Backup e Restauração")

    menu = st.sidebar.selectbox("Funcionalidade:", menu_opcoes)
    st.sidebar.divider()
    st.sidebar.caption(f"{SISTEMA_NOME} v{SISTEMA_VERSAO} | {perfil.upper()}")
    st.sidebar.caption(f"Log: {os.path.basename(LOG_FILE)}")

    # ====================== DASHBOARD ======================
    # ====================== DASHBOARD AVANÇADO ======================
    if menu == "🏠 Dashboard":
        st.header(f"🏠 Dashboard — {SISTEMA_NOME}")
        try:
            funcs = carregar_funcionarios()
            ativos   = [f for f in funcs if f.get("situacao") == "Ativo"]
            inativos = [f for f in funcs if f.get("situacao") != "Ativo"]
            
            # Métricas Principais
            total_folha_base = sum(f.get("salario_base", 0) for f in ativos)
            fila = carregar_fila_esocial()
            pendentes_esocial = len([e for e in fila if e["status"] in ["Pendente", "Aguardando"]])
            
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Funcionários Ativos",   len(ativos))
            col2.metric("Funcionários Inativos", len(inativos))
            col3.metric("Total Folha Base",      fmt_brl(total_folha_base))
            col4.metric("Média Salarial",        fmt_brl(total_folha_base / len(ativos) if ativos else 0))
            col5.metric("eSocial Pendente",      pendentes_esocial)

            st.divider()

            # ── Gráficos Avançados ──
            if not PLOTLY_AVAILABLE:
                st.warning("⚠️ **Gráficos Desativados:** A biblioteca 'Plotly' não foi encontrada. Para ativar os gráficos, execute o arquivo `CORRIGIR_DEPENDENCIAS.bat` na pasta do sistema.")
            
            col_g1, col_g2 = st.columns([2, 1])

            with col_g1:
                st.subheader("📈 Evolução de Custos (Últimos Meses)")
                if not PLOTLY_AVAILABLE:
                    st.info("Gráfico indisponível (Plotly ausente).")
                else:
                    # Agregar dados de todas as folhas calculadas
                    dados_historicos = []
                    meses_ref = [f"{m:02d}/2026" for m in range(1, 13)] # Simplificado para 2026
                    for mes in meses_ref:
                        total_mes = 0
                        for f in funcs:
                            folha = f.get("folha_pagamento", {}).get(mes, {})
                            total_mes += folha.get("liquido", 0)
                        if total_mes > 0:
                            dados_historicos.append({"Mês": mes, "Custo Total (R$)": total_mes})
                    
                    if dados_historicos:
                        df_hist = pd.DataFrame(dados_historicos)
                        fig_evol = px.line(df_hist, x="Mês", y="Custo Total (R$)", 
                                          markers=True, template="plotly_white",
                                          color_discrete_sequence=["#2563eb"])
                        st.plotly_chart(fig_evol, use_container_width=True)
                    else:
                        st.info("Aguardando cálculos de folha para gerar gráfico de evolução.")

            with col_g2:
                st.subheader("🏢 Por Departamento")
                if not PLOTLY_AVAILABLE:
                    st.info("Gráfico indisponível.")
                else:
                    deps = [f.get("departamento", "N/A") for f in ativos]
                    if deps:
                        df_deps = pd.DataFrame(deps, columns=["Depto"])
                        fig_deps = px.pie(df_deps, names="Depto", hole=0.4, 
                                         color_discrete_sequence=px.colors.qualitative.Safe)
                        fig_deps.update_layout(showlegend=False)
                        st.plotly_chart(fig_deps, use_container_width=True)

            st.divider()
            col_g3, col_g4 = st.columns(2)
            
            with col_g3:
                st.subheader("👥 Status da Equipe")
                if not PLOTLY_AVAILABLE:
                    st.info("Gráfico indisponível.")
                else:
                    status_data = {"Status": ["Ativo", "Inativo"], "Qtd": [len(ativos), len(inativos)]}
                    fig_status = px.bar(status_data, x="Status", y="Qtd", 
                                       color="Status", color_discrete_map={"Ativo": "#10b981", "Inativo": "#ef4444"})
                    st.plotly_chart(fig_status, use_container_width=True)
            
            with col_g4:
                st.subheader("💰 Distribuição Salarial")
                if not PLOTLY_AVAILABLE:
                    st.info("Gráfico indisponível.")
                elif ativos:
                    salarios = [f.get("salario_base", 0) for f in ativos]
                    fig_sal = px.histogram(salarios, nbins=10, labels={'value':'Salário (R$)'},
                                         color_discrete_sequence=["#8b5cf6"])
                    st.plotly_chart(fig_sal, use_container_width=True)
                else:
                    st.info("Sem dados para histograma.")

            # ─── Centro de Notificações ──────────────────────────
            st.divider()
            c_notif, c_charts = st.columns([1, 2])
            
            with c_notif:
                st.subheader("🔔 Notificações")
                hj = date.today()
                prox_30 = hj.replace(day=28) # Simplificação para cálculo de mês
                
                notificacoes = []
                for f in ativos:
                    # Aniversários
                    nasc = date.fromisoformat(f.get("data_nascimento", "1990-01-01"))
                    if nasc.month == hj.month:
                        notificacoes.append({
                            "tipo": "birthday",
                            "msg": f"🎂 **Aniversário:** {f['nome']} ({nasc.day:02d}/{nasc.month:02d})"
                        })
                    
                    # Experiência (45 e 90 dias)
                    adm = date.fromisoformat(f.get("data_admissao", str(hj)))
                    dias_casa = (hj - adm).days
                    if dias_casa in range(40, 46):
                        notificacoes.append({
                            "tipo": "probation",
                            "msg": f"⏳ **Fim Experiência (45d):** {f['nome']} em {45 - dias_casa} dias"
                        })
                    elif dias_casa in range(85, 91):
                        notificacoes.append({
                            "tipo": "probation",
                            "msg": f"⚠️ **Fim Experiência (90d):** {f['nome']} em {90 - dias_casa} dias"
                        })
                    
                    # Férias (Vencimento do período aquisitivo - 11 meses)
                    if dias_casa >= 330 and (dias_casa % 365) >= 330:
                        notificacoes.append({
                            "tipo": "vacation",
                            "msg": f"🏖️ **Férias Próximas:** {f['nome']} (Período de 1 ano quase completo)"
                        })

                if not notificacoes:
                    st.info("Sem notificações para hoje.")
                else:
                    for n in notificacoes:
                        st.markdown(f'<div class="notification-card notification-{n["tipo"]}">{n["msg"]}</div>', unsafe_allow_html=True)

            with c_charts:
                st.subheader("📊 Distribuição de Custos")
                if ativos:
                    df_setores = pd.DataFrame([{
                        "Departamento": f.get("departamento", "Geral"),
                        "Salário": f.get("salario_base", 0)
                    } for f in ativos])
                    chart_data = df_setores.groupby("Departamento")["Salário"].sum().reset_index()
                    st.bar_chart(chart_data, x="Departamento", y="Salário", color="#2563eb")
                else:
                    st.info("Dados insuficientes para gerar gráficos.")
            if ativos:
                st.subheader("Funcionários Ativos")
                df_dash = pd.DataFrame([{
                    "Nome": f["nome"],
                    "Cargo": f.get("cargo", ""),
                    "Departamento": f.get("departamento", ""),
                    "Salário Base": fmt_brl(f.get("salario_base", 0)),
                    "Admissão": f.get("data_admissao", ""),
                    "Docs": len(carregar_metadados_docs(f.get("id", 0))),
                } for f in ativos])
                st.dataframe(df_dash, use_container_width=True)
        except Exception as e:
            logger.error(f"Erro Dashboard: {e}")
            st.error(f"Erro: {e}")

    # ====================== MANUAL DO SISTEMA ======================
    elif menu == "📖 Manual do Sistema":
        st.header("📖 Manual do Sistema")
        try:
            data_str = datetime.now().strftime("%d/%m/%Y")
            conteudo = MANUAL_UTILIZACAO.format(data_atual=data_str)
            st.markdown(conteudo)
            
            st.divider()
            if st.button("📄 Gerar Manual em PDF"):
                try:
                    buf_manual = BytesIO()
                    doc_m = SimpleDocTemplate(buf_manual, pagesize=A4,
                                              rightMargin=20*mm, leftMargin=20*mm,
                                              topMargin=15*mm, bottomMargin=15*mm)
                    styles_m = getSampleStyleSheet()
                    h1_s = ParagraphStyle("H1m", parent=styles_m["Heading1"], fontSize=14, spaceAfter=4)
                    h2_s = ParagraphStyle("H2m", parent=styles_m["Heading2"], fontSize=12, spaceAfter=3)
                    body_s = ParagraphStyle("Bodym", parent=styles_m["Normal"], fontSize=9, spaceAfter=2)
                    story_m = [Paragraph(f"<b>{SISTEMA_NOME} v{SISTEMA_VERSAO} — Manual de Utilização</b>",
                                         ParagraphStyle("Tm", fontSize=16, alignment=TA_CENTER, spaceAfter=6))]
                    for linha in conteudo.split("\n"):
                        linha = linha.strip()
                        if not linha:
                            story_m.append(Spacer(1, 3*mm))
                            continue
                        # Escapar caracteres XML
                        linha_esc = linha.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        if linha_esc.startswith("## "):
                            story_m.append(Paragraph(linha_esc[3:], h2_s))
                        elif linha_esc.startswith("# "):
                            story_m.append(Paragraph(linha_esc[2:], h1_s))
                        else:
                            # Converter **negrito** simples
                            linha_esc = linha_esc.replace("**", "<b>", 1).replace("**", "</b>", 1)
                            story_m.append(Paragraph(linha_esc, body_s))
                    doc_m.build(story_m)
                    buf_manual.seek(0)
                    _pdf_store("_pdf_manual", buf_manual)
                except Exception as em:
                    st.error(f"Erro ao gerar PDF do manual: {em}")
            _pdf_btn("_pdf_manual", f"manual_{SISTEMA_NOME.replace(' ','_')}_v{SISTEMA_VERSAO}.pdf",
                     label="⬇️ Baixar Manual PDF")
        except Exception as e:
            st.error(f"Erro ao carregar manual: {e}")

    # ====================== GERENCIAR USUÁRIOS ======================
    elif menu == "👥 Gerenciar Usuários":
        if not tem_permissao("admin"):
            st.error("Acesso negado.")
        else:
            st.header("👥 Gerenciar Usuários")
            try:
                usuarios = carregar_usuarios()
                with st.expander("➕ Novo Usuário"):
                    with st.form("novo_usuario"):
                        nome_u = st.text_input("Nome Completo")
                        username_u = st.text_input("Usuário")
                        senha_u = st.text_input("Senha", type="password")
                        perfil_u = st.selectbox("Perfil", ["admin", "coordenador", "funcionario"])
                        if st.form_submit_button("Cadastrar"):
                            if nome_u and username_u and senha_u:
                                valida, msg_forca = validar_forca_senha(senha_u)
                                if not valida:
                                    st.error(msg_forca)
                                elif any(u["username"].lower() == username_u.lower() for u in usuarios):
                                    st.error("Nome de usuário já existe!")
                                else:
                                    hash_val, salt = gerar_hash_senha(senha_u)
                                    novo = {
                                        "id": max([u.get("id", 0) for u in usuarios], default=0) + 1,
                                        "nome": nome_u, "username": username_u,
                                        "senha": hash_val, "salt": salt, "perfil": perfil_u
                                    }
                                    usuarios.append(novo)
                                    salvar_usuarios(usuarios)
                                    log_acao("USUARIO_NOVO", f"{username_u} ({perfil_u})")
                                    st.success("Usuário cadastrado!")
                                    st.info(msg_forca)
                                    st.rerun()
                            else:
                                st.warning("Preencha todos os campos.")
                st.subheader("Usuários Cadastrados")
                for u in usuarios:
                    cols = st.columns([3, 2, 1])
                    cols[0].write(f"**{u['nome']}** — `{u['username']}`")
                    cols[1].write(u["perfil"].upper())
                    if cols[2].button("🗑️", key=f"del_u_{u['id']}"):
                        if u["username"] == usuario["username"]:
                            st.error("Não é possível excluir o próprio usuário!")
                        else:
                            usuarios = [x for x in usuarios if x["id"] != u["id"]]
                            salvar_usuarios(usuarios)
                            log_acao("USUARIO_EXCLUIDO", u['username'])
                            st.success("Usuário excluído!")
                            st.rerun()
            except Exception as e:
                logger.error(f"Erro Gerenciar Usuários: {e}")
                st.error(f"Erro: {e}")

    # ====================== CADASTRO DE FUNCIONÁRIOS ======================
    elif menu == "👤 Cadastro de Funcionários":
        if not tem_permissao("coordenador"):
            st.error("Você não tem permissão para acessar esta tela.")
        else:
            st.header("👤 Cadastro de Funcionários")
            try:
                funcs = carregar_funcionarios()
                edit_id = st.session_state.get("edit_id", None)
                func_edit = next((f for f in funcs if f.get("id") == edit_id), {})

                # ── Abas: Dados / Documentos / Assistente ────────────────────────
                tab_dados, tab_docs, tab_assist = st.tabs([
                    "📋 Dados Cadastrais", 
                    "📁 Documentos do Funcionário",
                    "🚀 Assistente de Admissão"
                ])

                with tab_dados:
                    with st.form("cadastro_form"):
                        st.subheader("Dados do Funcionário" + (" — Editando" if edit_id else " — Novo"))
                        col1, col2 = st.columns(2)
                        with col1:
                            nome     = st.text_input("Nome Completo *",   value=func_edit.get("nome", ""))
                            cpf      = st.text_input("CPF *",             value=func_edit.get("cpf", ""))
                            rg       = st.text_input("RG",                value=func_edit.get("rg", ""))
                            data_nasc = st.date_input("Data de Nascimento",
                                                       value=date.fromisoformat(func_edit.get("data_nascimento", "1990-01-01")))
                            data_adm  = st.date_input("Data de Admissão",
                                                       value=date.fromisoformat(func_edit.get("data_admissao", date.today().isoformat())))
                            cargo     = st.text_input("Cargo",        value=func_edit.get("cargo", ""))
                            departamento = st.text_input("Departamento", value=func_edit.get("departamento", ""))
                        with col2:
                            salario    = st.number_input("Salário Base (R$)", min_value=0.0, step=100.0,
                                                          value=float(func_edit.get("salario_base", 0)))
                            dependentes = st.number_input("Dependentes", min_value=0,
                                                           value=int(func_edit.get("num_dependentes", 0)))
                            plano_saude = st.checkbox("Tem Plano de Saúde?",
                                                       value=func_edit.get("tem_plano_saude") == "Sim")
                            valor_plano = st.number_input("Valor Plano Saúde (R$)", min_value=0.0, step=10.0,
                                                           value=float(func_edit.get("valor_plano", 0)))
                            vt_mensal   = st.number_input("Valor VT Mensal (R$)", min_value=0.0, step=10.0,
                                                           value=float(func_edit.get("valor_vt_mensal", 0)))
                            situacao    = st.selectbox("Situação", ["Ativo", "Inativo"],
                                                       index=0 if func_edit.get("situacao", "Ativo") == "Ativo" else 1)

                        submitted = st.form_submit_button("💾 Atualizar" if edit_id else "💾 Salvar",
                                                          type="primary")
                        if submitted:
                            if not nome or not cpf:
                                st.error("Nome e CPF são obrigatórios!")
                            elif not validar_cpf(cpf):
                                st.error("❌ CPF inválido! Verifique os dígitos informados.")
                            else:
                                cpf_formatado = formatar_cpf(cpf)
                                # Verificar duplicidade de CPF (apenas para novos cadastros)
                                if not edit_id:
                                    cpf_limpo_check = re.sub(r'[^0-9]', '', cpf)
                                    cpfs_existentes = [re.sub(r'[^0-9]', '', f.get("cpf", "")) for f in funcs]
                                    if cpf_limpo_check in cpfs_existentes:
                                        st.error("⚠️ Já existe um funcionário com este CPF!")
                                        st.stop()
                                dados_func = {
                                    "nome": nome.strip(), "cpf": cpf_formatado, "rg": rg.strip(),
                                    "data_nascimento": str(data_nasc),
                                    "data_admissao": str(data_adm),
                                    "cargo": cargo.strip(), "departamento": departamento.strip(),
                                    "salario_base": round(salario, 2),
                                    "num_dependentes": int(dependentes),
                                    "tem_plano_saude": "Sim" if plano_saude else "Não",
                                    "valor_plano": round(valor_plano, 2),
                                    "valor_vt_mensal": round(vt_mensal, 2),
                                    "situacao": situacao,
                                }
                                if edit_id:
                                    for f in funcs:
                                        if f["id"] == edit_id:
                                            f.update(dados_func)
                                            break
                                    log_acao("FUNC_ATUALIZADO", f"ID={edit_id} Nome={nome}")
                                    st.success("Funcionário atualizado!")
                                    st.session_state.edit_id = None
                                else:
                                    novo_id = max([f.get("id", 0) for f in funcs], default=0) + 1
                                    dados_func["id"] = novo_id
                                    dados_func["folha_pagamento"] = {}
                                    funcs.append(dados_func)
                                    log_acao("FUNC_CADASTRADO", f"Nome={nome}")
                                    st.success(f"Funcionário cadastrado! ID: {novo_id}")
                                    # Criar pasta de documentos
                                    pasta_documentos_func(novo_id)
                                salvar_funcionarios(funcs)
                                st.rerun()

                    if edit_id and st.button("❌ Cancelar Edição"):
                        st.session_state.edit_id = None
                        st.rerun()

                    st.subheader("Lista de Funcionários")
                    for func in funcs:
                        n_docs = len(carregar_metadados_docs(func.get("id", 0)))
                        c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
                        c1.write(f"**{func['nome']}** — {func.get('cargo', '')} | {fmt_brl(func.get('salario_base', 0))}")
                        c2.write(f"ID: {func['id']} | {func.get('situacao', 'Ativo')} | 📁 {n_docs} doc(s)")
                        if c3.button("✏️", key=f"edit_{func['id']}"):
                            st.session_state.edit_id = func["id"]
                            st.rerun()
                        if c4.button("🗑️", key=f"del_{func['id']}"):
                            funcs = [f for f in funcs if f["id"] != func["id"]]
                            salvar_funcionarios(funcs)
                            log_acao("FUNC_EXCLUIDO", f"ID={func['id']}")
                            st.success("Excluído!")
                            st.rerun()


                # ── Aba Documentos ──────────────────────────────────
                with tab_docs:
                    st.subheader("📁 Gestão de Documentos de Funcionários")

                    # Seletor de funcionário para documentos
                    if funcs:
                        nomes_funcs = [f["nome"] for f in funcs]
                        nome_doc_sel = st.selectbox("Selecione o Funcionário", nomes_funcs,
                                                     key="doc_func_sel")
                        func_doc = next(f for f in funcs if f["nome"] == nome_doc_sel)
                        func_id_doc = func_doc["id"]

                        # ── Gerador de Kit de Admissão (ZIP) ──
                        st.divider()
                        st.subheader("📦 Kit de Documentos Automático")
                        if st.button("🎁 Gerar Kit Admissão Completo (ZIP)", key="btn_kit_zip"):
                            try:
                                zip_buffer = BytesIO()
                                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                                    # 1. Ficha de Registro
                                    _buf_ficha = gerar_ficha_cadastro_pdf(func_doc)
                                    pdf_ficha = _buf_ficha.getvalue() if _buf_ficha else b""
                                    zip_file.writestr(f"01_Ficha_Registro_{func_doc['nome'].replace(' ','_')}.pdf", pdf_ficha)

                                    # 2. Contrato de Trabalho (Baseado na ficha por enquanto)
                                    zip_file.writestr(f"02_Contrato_Trabalho_{func_doc['nome'].replace(' ','_')}.pdf", pdf_ficha)
                                    
                                st.download_button(
                                    "⬇️ Baixar Kit ZIP",
                                    zip_buffer.getvalue(),
                                    file_name=f"Kit_Admissao_{func_doc['nome'].replace(' ','_')}.zip",
                                    mime="application/zip",
                                    key="dl_kit_zip_btn"
                                )
                                st.success("Kit gerado com sucesso!")
                                log_acao("KIT_GERADO", f"Func: {func_doc['nome']}")
                            except Exception as ez:
                                st.error(f"Erro ao gerar kit: {ez}")
                        st.divider()

                        # ── Upload de novo documento ────────────────
                        with st.expander("➕ Enviar Novo Documento", expanded=True):
                            col_up1, col_up2 = st.columns(2)
                            with col_up1:
                                tipo_doc_sel = st.selectbox("Tipo de Documento *", TIPOS_DOCUMENTO,
                                                             key="tipo_doc_upload")
                            with col_up2:
                                descricao_doc = st.text_input("Descrição / Observação",
                                                               placeholder="Ex: CTPS digital — série 0001",
                                                               key="descricao_doc_upload")
                            arquivo_up = st.file_uploader(
                                "Selecione o arquivo (PDF, JPG, PNG — máx. 10 MB)",
                                type=["pdf", "jpg", "jpeg", "png"],
                                key="file_uploader_doc"
                            )
                            if arquivo_up is not None:
                                tamanho = len(arquivo_up.getvalue())
                                if tamanho > 10 * 1024 * 1024:
                                    st.error("❌ Arquivo muito grande! Máximo permitido: 10 MB.")
                                else:
                                    st.info(f"📄 **{arquivo_up.name}** — {fmt_tamanho(tamanho)}")
                                    # Pré-visualização para imagens
                                    ext_up = Path(arquivo_up.name).suffix.lower()
                                    if ext_up in [".jpg", ".jpeg", ".png"]:
                                        st.image(arquivo_up, caption="Pré-visualização", width=300)
                                    elif ext_up == ".pdf":
                                        st.success("📋 Arquivo PDF pronto para envio.")

                                    if st.button("💾 Salvar Documento", type="primary",
                                                  key="btn_salvar_doc"):
                                        conteudo = arquivo_up.getvalue()
                                        meta = salvar_documento_func(
                                            func_id=func_id_doc,
                                            arquivo_nome=arquivo_up.name,
                                            conteudo=conteudo,
                                            tipo_doc=tipo_doc_sel,
                                            descricao=descricao_doc,
                                        )
                                        log_acao("DOC_UPLOAD", f"{func_doc['nome']} — {tipo_doc_sel} — {arquivo_up.name}")
                                        st.success(f"✅ Documento salvo com sucesso! ID: {meta['id']}")
                                        st.rerun()

                        # ── Lista de documentos existentes ──────────
                        st.divider()
                        docs_existentes = carregar_metadados_docs(func_id_doc)
                        st.subheader(f"📂 Documentos de {func_doc['nome']} ({len(docs_existentes)} arquivo(s))")

                        if not docs_existentes:
                            st.info("Nenhum documento arquivado para este funcionário.")
                        else:
                            # Agrupar por tipo
                            por_tipo: dict = {}
                            for d in docs_existentes:
                                t = d.get("tipo_doc", "Outros")
                                por_tipo.setdefault(t, []).append(d)

                            for tipo_grupo, lista_docs in por_tipo.items():
                                st.markdown(f"**📌 {tipo_grupo}** ({len(lista_docs)} arquivo(s))")
                                for doc_meta in lista_docs:
                                    col_d1, col_d2, col_d3, col_d4 = st.columns([3, 2, 1, 1])
                                    nome_exib = doc_meta["nome_original"]
                                    if len(nome_exib) > 40:
                                        nome_exib = nome_exib[:37] + "..."
                                    col_d1.write(f"📄 `{nome_exib}`")
                                    col_d2.write(
                                        f"{fmt_tamanho(doc_meta.get('tamanho_bytes', 0))} | "
                                        f"{doc_meta.get('enviado_em', '')[:10]}"
                                    )
                                    # Botão download
                                    if os.path.exists(doc_meta.get("caminho", "")):
                                        with open(doc_meta["caminho"], "rb") as arq_f:
                                            ext_icon = "🖼️" if doc_meta["extensao"] in [".jpg", ".jpeg", ".png"] else "📋"
                                            col_d3.download_button(
                                                f"{ext_icon} Baixar",
                                                data=arq_f.read(),
                                                file_name=doc_meta["nome_original"],
                                                key=f"dl_doc_{doc_meta['id']}",
                                                mime="application/octet-stream"
                                            )
                                    else:
                                        col_d3.write("⚠️ Não encontrado")
                                    if col_d4.button("🗑️", key=f"del_doc_{doc_meta['id']}"):
                                        excluir_documento(func_id_doc, doc_meta["id"])
                                        log_acao("DOC_EXCLUIDO", f"{func_doc['nome']} — {doc_meta['nome_original']}")
                                        st.success("Documento excluído!")
                                        st.rerun()
                                    if doc_meta.get("descricao"):
                                        col_d1.caption(f"  ↳ {doc_meta['descricao']}")
                                st.markdown("---")

                            # Resumo de tamanho total
                            total_bytes = sum(d.get("tamanho_bytes", 0) for d in docs_existentes)
                            st.caption(f"💾 Espaço total utilizado: {fmt_tamanho(total_bytes)}")
                    else:
                        st.warning("Cadastre funcionários primeiro.")

                # ── Aba Assistente de Admissão ──────────────────────
                with tab_assist:
                    st.subheader("🚀 Guia Rápido para Nova Admissão")
                    st.info("Siga estes passos para garantir que a contratação esteja em conformidade.")
                    
                    col_as1, col_as2 = st.columns(2)
                    with col_as1:
                        st.markdown("""
                        ### 1. Documentação Necessária
                        - [ ] Carteira de Trabalho (Digital ou Física)
                        - [ ] RG e CPF
                        - [ ] Comprovante de Residência
                        - [ ] Certificado de Escolaridade
                        - [ ] Título de Eleitor
                        - [ ] Certificado de Reservista (homens)
                        - [ ] Certidão de Nascimento/Casamento
                        - [ ] CPF dos Dependentes (obrigatório para eSocial)
                        - [ ] Atestado Médico Admissional (ASO)
                        """)
                    
                    with col_as2:
                        st.markdown("""
                        ### 2. Prazos eSocial
                        *   **Registro de Empregado (S-2200):** Deve ser enviado até o dia anterior ao início das atividades.
                        *   **Exame Admissional:** Deve ser realizado antes do início do trabalho.
                        
                        ### 3. Integração
                        *   [ ] Entrega do Regulamento Interno
                        *   [ ] Assinatura do Contrato de Trabalho
                        *   [ ] Opção de Vale-Transporte
                        *   [ ] Cadastro no sistema DPMaster Pro
                        """)
                    
                    st.divider()
                    st.warning("⚠️ **Lembre-se:** Pequenas empresas com até 10 funcionários podem ter processos simplificados, mas a documentação legal é obrigatória para todos.")
                    
                    if st.button("📝 Gerar Kit de Admissão (Checklist PDF)"):
                        st.info("Esta funcionalidade está sendo preparada para a próxima atualização.")

            except Exception as e:
                logger.error(f"Erro Cadastro: {e}\n{traceback.format_exc()}")
                st.error(f"Erro: {e}")

    # ====================== FOLHA DE PAGAMENTO ======================
    elif menu == "💰 Folha de Pagamento":
        if not tem_permissao("coordenador"):
            st.error("Acesso negado.")
            st.stop()
        st.header("💰 Folha de Pagamento — Mês a Mês")
        try:
            todos_funcs = carregar_funcionarios()
            funcs = [f for f in todos_funcs if f.get("situacao") == "Ativo"]
            if not funcs:
                st.warning("Nenhum funcionário ativo.")
            else:
                mes = st.selectbox("Mês de Referência", [f"{i:02d}/2026" for i in range(1, 13)], index=3)
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("🔄 Calcular Todos", type="primary"):
                        for func in funcs:
                            if "folha_pagamento" not in func:
                                func["folha_pagamento"] = {}
                            
                            s = func.get("salario_base", 0)
                            v_hora = round(s / 220, 2)
                            
                            # ── Processar Ponto ──
                            he_50_val = 0.0
                            he_100_val = 0.0
                            faltas_val = 0.0
                            dsr_he = 0.0
                            ponto_mes = func.get("ponto", {}).get(mes, {})
                            
                            if ponto_mes:
                                q_50 = ponto_mes.get("he_50", 0.0)
                                q_100 = ponto_mes.get("he_100", 0.0)
                                q_faltas = ponto_mes.get("faltas", 0)
                                
                                he_50_val = round((v_hora * 1.5) * q_50, 2)
                                he_100_val = round((v_hora * 2.0) * q_100, 2)
                                dsr_he = round((he_50_val + he_100_val) / 6, 2) # Simplificado (1/6)
                                faltas_val = round((s / 30) * q_faltas, 2)

                            # Encargos Legais (sobre Salário + HE + DSR)
                            base_calculo = s + he_50_val + he_100_val + dsr_he
                            inss = calcular_inss(base_calculo)
                            irrf = calcular_irrf(base_calculo - inss, func.get("num_dependentes", 0))
                            vt = calcular_vt(s, func.get("valor_vt_mensal", 0))
                            plano = func.get("valor_plano", 0) if func.get("tem_plano_saude") == "Sim" else 0
                            
                            liquido = round(base_calculo - inss - irrf - vt - plano - faltas_val, 2)
                            
                            func["folha_pagamento"][mes] = {
                                "salario_base": s,
                                "he_50": he_50_val,
                                "he_100": he_100_val,
                                "dsr_he": dsr_he,
                                "faltas_desconto": faltas_val,
                                "inss": inss, "irrf": irrf,
                                "vt": vt, "plano_saude": plano, "liquido": liquido,
                                "calculado_em": datetime.now().isoformat()
                            }
                        salvar_funcionarios(todos_funcs)
                        # Gerar evento S-1200 e adicionar à fila
                        caminho_xml, nome_xml, _ = gerar_xml_folha_pagamento(funcs, mes)
                        if nome_xml:
                            ev_id = adicionar_evento_fila(
                                tipo="S-1200",
                                grupo="Periódico",
                                descricao=f"Remuneração dos trabalhadores — {mes}",
                                arquivo_xml=nome_xml,
                                dados_extras={"mes": mes, "qtd_func": len(funcs)}
                            )
                            st.info(f"📤 Evento S-1200 adicionado à fila eSocial (ID #{ev_id})")
                        log_acao("FOLHA_CALCULADA", f"{mes} — {len(funcs)} func.")
                        st.success(f"Folha de {mes} calculada!")
                        st.rerun()
                with col_b:
                    if st.button("🗑️ Cancelar Todos", type="secondary"):
                        cancelados = 0
                        for func in funcs:
                            if mes in func.get("folha_pagamento", {}):
                                del func["folha_pagamento"][mes]
                                cancelados += 1
                        salvar_funcionarios(todos_funcs)
                        st.success(f"Cancelado para {cancelados} funcionários!")
                        st.rerun()
                st.divider()
                for func in funcs:
                    folha = func.get("folha_pagamento", {}).get(mes, {})
                    status_icon = "✅" if folha else "⏳"
                    with st.expander(f"{status_icon} {func['nome']} — {fmt_brl(func.get('salario_base', 0))}"):
                        if folha:
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.write(f"**Salário Base:** {fmt_brl(folha.get('salario_base', 0))}")
                                if folha.get("he_50", 0) > 0:
                                    st.write(f"➕ **HE 50%:** {fmt_brl(folha['he_50'])}")
                                if folha.get("he_100", 0) > 0:
                                    st.write(f"➕ **HE 100%:** {fmt_brl(folha['he_100'])}")
                                if folha.get("dsr_he", 0) > 0:
                                    st.write(f"➕ **DSR s/ HE:** {fmt_brl(folha['dsr_he'])}")
                            with c2:
                                st.write(f"**INSS:** {fmt_brl(folha.get('inss', 0))}")
                                st.write(f"**IRRF:** {fmt_brl(folha.get('irrf', 0))}")
                                if folha.get("faltas_desconto", 0) > 0:
                                    st.write(f"➖ **Faltas:** {fmt_brl(folha['faltas_desconto'])}")
                            with c3:
                                st.write(f"**VT:** {fmt_brl(folha.get('vt', 0))}")
                                st.write(f"**Plano:** {fmt_brl(folha.get('plano_saude', 0))}")
                                st.success(f"**Líquido:** {fmt_brl(folha.get('liquido', 0))}")
                            
                            # Mostrar itens extras se existirem
                            extras = folha.get("itens_extras", [])
                            if extras:
                                with st.expander("📝 Detalhes dos Itens Extras"):
                                    for item in extras:
                                        cor = "green" if item['tipo'] == "Provento" else "red"
                                        st.write(f":{cor}[{item['tipo']}: {item['descricao']} — {fmt_brl(item['valor'])}]")
                            if folha.get("calculado_em"):
                                st.caption(f"Calculado em: {folha['calculado_em'][:16].replace('T',' ')}")
                            col_pdf, col_cancel = st.columns(2)
                            _sk_cc = f"_pdf_cc_{func['id']}_{mes}"
                            with col_pdf:
                                if st.button("📄 Contracheque PDF", key=f"pdf_{func['id']}_{mes}"):
                                    _pdf_store(_sk_cc, gerar_contracheque_pdf(func, mes))
                                _pdf_btn(_sk_cc,
                                         f"contracheque_{func['nome'].replace(' ','_')}_{mes.replace('/','')}.pdf")
                            with col_cancel:
                                if st.button("🗑️ Cancelar", key=f"cancel_{func['id']}_{mes}"):
                                    del func["folha_pagamento"][mes]
                                    salvar_funcionarios(todos_funcs)
                                    st.success("Cancelado!")
                                    st.rerun()
                        else:
                            st.info("Folha não calculada para este mês.")
                            with st.form(key=f"form_manual_{func.get('id')}"):
                                st.caption("Configurações Individuais:")
                                s_m = st.number_input("Salário Base", value=float(func.get("salario_base", 0)), key=f"sal_{func['id']}")
                                vt_m = st.number_input("VT Mensal", value=float(func.get("valor_vt_mensal", 0)), key=f"vt_{func['id']}")
                                pl_m = st.number_input("Plano de Saúde",
                                                        value=float(func.get("valor_plano", 0) if func.get("tem_plano_saude") == "Sim" else 0),
                                                        key=f"plano_{func['id']}")
                                
                                st.write("**Itens Extras (Proventos e Descontos)**")
                                df_default = pd.DataFrame(columns=["descricao", "valor", "tipo"])
                                # Se já houver itens extras salvos, carregar (mas o form limpa ao recarregar, então usamos session_state se necessário)
                                # Para simplicidade dentro do expander, vamos permitir adicionar aqui
                                manual_items = st.data_editor(df_default, num_rows="dynamic", 
                                                              column_config={
                                                                  "tipo": st.column_config.SelectboxColumn(options=["Provento", "Desconto"])
                                                              },
                                                              key=f"editor_manual_{func['id']}_{mes}")

                                if st.form_submit_button("💾 Calcular e Salvar"):
                                    inss = calcular_inss(s_m)
                                    irrf = calcular_irrf(s_m - inss, func.get("num_dependentes", 0))
                                    vt = calcular_vt(s_m, vt_m)
                                    
                                    # Processar itens extras
                                    itens_list = manual_items.to_dict('records')
                                    total_prov_extra = sum(i['valor'] for i in itens_list if i['tipo'] == "Provento" and i['valor'])
                                    total_desc_extra = sum(i['valor'] for i in itens_list if i['tipo'] == "Desconto" and i['valor'])
                                    
                                    liquido = round((s_m + total_prov_extra) - (inss + irrf + vt + pl_m + total_desc_extra), 2)
                                    
                                    if "folha_pagamento" not in func:
                                        func["folha_pagamento"] = {}
                                    func["folha_pagamento"][mes] = {
                                        "salario_base": s_m, 
                                        "inss": inss, 
                                        "irrf": irrf,
                                        "base_irrf": s_m - inss,
                                        "vt": vt, 
                                        "plano_saude": pl_m, 
                                        "itens_extras": itens_list,
                                        "liquido": liquido,
                                        "calculado_em": datetime.now().isoformat()
                                    }
                                    salvar_funcionarios(todos_funcs)
                                    st.success(f"Líquido: {fmt_brl(liquido)}")
                                    st.rerun()
        except Exception as e:
            logger.error(f"Erro Folha: {e}")
            st.error(f"Erro: {e}")

    # ====================== 13º SALÁRIO ======================
    elif menu == "🎄 13º Salário":
        if not tem_permissao("coordenador"):
            st.error("Acesso negado.")
            st.stop()
        st.header("🎄 Cálculo do 13º Salário")
        try:
            todos_funcs = carregar_funcionarios()
            funcs = [f for f in todos_funcs if f.get("situacao") == "Ativo"]
            if not funcs:
                st.warning("Nenhum funcionário ativo.")
            else:
                col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
                with col_cfg1:
                    ano = st.selectbox("Ano", [2024, 2025, 2026], index=2)
                with col_cfg2:
                    tipo = st.radio("Tipo", ["Adiantamento (1ª Parcela)", "Final (2ª Parcela — com avos)"])
                with col_cfg3:
                    mes_ref = st.selectbox("Mês de Pagamento", [f"{i:02d}/{ano}" for i in range(1, 13)],
                                           index=5 if "Adiantamento" in tipo else 11)
                percentual = 50
                if "Adiantamento" in tipo:
                    percentual = st.slider("Percentual do Adiantamento (%)", 10, 100, 50)

                if st.button("🔄 Calcular 13º para Todos", type="primary"):
                    for func in funcs:
                        if "folha_pagamento" not in func:
                            func["folha_pagamento"] = {}
                        if "Final" in tipo:
                            avos = calcular_avos(func.get("data_admissao"), ano)
                            valor_bruto = round(func.get("salario_base", 0) * (avos / 12), 2)
                            inss_13 = calcular_inss(valor_bruto)
                            irrf_13 = calcular_irrf(valor_bruto - inss_13, func.get("num_dependentes", 0))
                            liquido_13 = round(valor_bruto - inss_13 - irrf_13, 2)
                        else:
                            avos = 12
                            valor_bruto = round(func.get("salario_base", 0) * (percentual / 100), 2)
                            inss_13 = irrf_13 = 0.0
                            liquido_13 = valor_bruto
                        func["folha_pagamento"][mes_ref] = {
                            "decimo_terceiro_bruto": valor_bruto, "inss_13": inss_13,
                            "irrf_13": irrf_13, "decimo_terceiro_liquido": liquido_13,
                            "avos_13": avos, "tipo_13": tipo,
                            "calculado_em": datetime.now().isoformat()
                        }
                    salvar_funcionarios(todos_funcs)
                    log_acao("DECIMO_CALCULADO", f"{mes_ref} — {tipo}")
                    st.success(f"13º calculado para {len(funcs)} funcionários!")
                    st.rerun()

                st.divider()
                for func in funcs:
                    folha_13 = func.get("folha_pagamento", {}).get(mes_ref, {})
                    tem_calc = "decimo_terceiro_bruto" in folha_13
                    with st.expander(f"{'✅' if tem_calc else '⏳'} {func['nome']} — {fmt_brl(func.get('salario_base', 0))}"):
                        if tem_calc:
                            st.write(f"**Tipo:** {folha_13.get('tipo_13','')}")
                            st.write(f"**Avos:** {folha_13.get('avos_13',12)}/12")
                            st.write(f"**Bruto:** {fmt_brl(folha_13.get('decimo_terceiro_bruto',0))}")
                            if folha_13.get("inss_13", 0) > 0:
                                st.write(f"**(-) INSS:** {fmt_brl(folha_13['inss_13'])}")
                            if folha_13.get("irrf_13", 0) > 0:
                                st.write(f"**(-) IRRF:** {fmt_brl(folha_13['irrf_13'])}")
                            st.success(f"**Líquido:** {fmt_brl(folha_13.get('decimo_terceiro_liquido',0))}")
                            col_pdf, col_cancel = st.columns(2)
                            _sk_13 = f"_pdf_13_{func['id']}_{mes_ref}"
                            with col_pdf:
                                if st.button("📄 PDF 13º", key=f"pdf_13_{func['id']}_{mes_ref}"):
                                    _pdf_store(_sk_13, gerar_decimo_pdf(func, ano, tipo,
                                                                         folha_13.get("decimo_terceiro_bruto", 0),
                                                                         folha_13.get("avos_13", 12)))
                                _pdf_btn(_sk_13,
                                         f"13salario_{func['nome'].replace(' ','_')}_{mes_ref.replace('/','')}.pdf",
                                         label="⬇️ Baixar")
                            with col_cancel:
                                if st.button("🗑️ Cancelar 13º", key=f"cancel_13_{func['id']}_{mes_ref}"):
                                    del func["folha_pagamento"][mes_ref]
                                    salvar_funcionarios(todos_funcs)
                                    st.success("Cancelado!")
                                    st.rerun()
                        else:
                            st.info("13º não calculado. Use o botão acima.")
        except Exception as e:
            logger.error(f"Erro 13º: {e}")
            st.error(f"Erro: {e}")

    # ====================== FÉRIAS ======================
    elif menu == "🏖️ Férias":
        if not tem_permissao("coordenador"):
            st.error("Acesso negado.")
            st.stop()
        st.header("🏖️ Cálculo de Férias — CLT")
        try:
            todos_funcs = carregar_funcionarios()
            funcs = [f for f in todos_funcs if f.get("situacao") == "Ativo"]
            if not funcs:
                st.warning("Nenhum funcionário ativo.")
            else:
                col_cfg1, col_cfg2 = st.columns(2)
                with col_cfg1:
                    mes = st.selectbox("Mês de Pagamento", [f"{i:02d}/2026" for i in range(1, 13)], index=6)
                with col_cfg2:
                    nome_sel = st.selectbox("Funcionário", [f["nome"] for f in funcs])
                func = next(f for f in funcs if f["nome"] == nome_sel)
                salario = func.get("salario_base", 0)
                meses_trab, ano_p, status_periodo = calcular_periodo_aquisitivo(func.get("data_admissao"), mes)
                st.info(f"**Período Aquisitivo:** {status_periodo}")
                col1, col2, col3 = st.columns(3)
                with col1:
                    incluir_abono = st.checkbox("Incluir Abono Pecuniário?")
                    dias_abono = 0
                    if incluir_abono:
                        dias_abono = st.number_input("Dias de Abono (máx 10)", min_value=0, max_value=10, value=10)
                with col2:
                    incluir_decimo = st.checkbox("Incluir 13º nas Férias?", value=True)
                with col3:
                    calcular_inss_ferias = st.checkbox("Descontar INSS?", value=True)
                    calcular_irrf_ferias_chk = st.checkbox("Descontar IRRF?", value=True)

                if st.button("🔄 Calcular Férias", type="primary"):
                    try:
                        dias_ferias = 30 - dias_abono
                        ferias_base = round(salario * (meses_trab / 12) * (dias_ferias / 30), 2)
                        terco = round(ferias_base / 3, 2)
                        ferias_com_terco = round(ferias_base + terco, 2)
                        abono_total = round((salario / 30) * dias_abono * (4 / 3), 2) if dias_abono > 0 else 0.0
                        decimo_ferias = round(salario * (meses_trab / 12) / 12, 2) if incluir_decimo else 0.0
                        total_bruto = round(ferias_com_terco + abono_total + decimo_ferias, 2)
                        inss_ferias = calcular_inss(ferias_com_terco + decimo_ferias) if calcular_inss_ferias else 0.0
                        base_irrf_f = (ferias_com_terco + decimo_ferias) - inss_ferias
                        irrf_ferias = calcular_irrf(base_irrf_f, func.get("num_dependentes", 0)) if calcular_irrf_ferias_chk else 0.0
                        total_liquido = round(total_bruto - inss_ferias - irrf_ferias, 2)
                        st.session_state[f"ferias_calc_{func['id']}"] = {
                            "dias_ferias": dias_ferias, "dias_abono": dias_abono,
                            "ferias_base": ferias_base, "terco": terco,
                            "ferias_com_terco": ferias_com_terco, "abono_total": abono_total,
                            "decimo_ferias": decimo_ferias, "total_bruto": total_bruto,
                            "inss_ferias": inss_ferias, "irrf_ferias": irrf_ferias,
                            "total_liquido": total_liquido, "meses_trab": meses_trab,
                            "status_periodo": status_periodo,
                        }
                        log_acao("FERIAS_CALC", f"{func['nome']} — {mes}")
                    except Exception as e:
                        logger.error(f"Erro férias: {e}")
                        st.error(f"Erro: {e}")

                calc_key = f"ferias_calc_{func['id']}"
                if calc_key in st.session_state:
                    vf = st.session_state[calc_key]
                    st.divider()
                    st.subheader("Resultado")
                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        st.write(f"**Dias de Férias:** {vf['dias_ferias']}")
                        st.write(f"**Férias Base ({vf['meses_trab']}/12):** {fmt_brl(vf['ferias_base'])}")
                        st.write(f"**1/3 Constitucional:** {fmt_brl(vf['terco'])}")
                        if vf["dias_abono"] > 0:
                            st.write(f"**Abono ({vf['dias_abono']} dias):** {fmt_brl(vf['abono_total'])}")
                        if vf["decimo_ferias"] > 0:
                            st.write(f"**13º nas Férias:** {fmt_brl(vf['decimo_ferias'])}")
                        st.write(f"**Total Bruto:** {fmt_brl(vf['total_bruto'])}")
                    with col_r2:
                        if vf["inss_ferias"] > 0:
                            st.write(f"**(-) INSS:** {fmt_brl(vf['inss_ferias'])}")
                        if vf["irrf_ferias"] > 0:
                            st.write(f"**(-) IRRF:** {fmt_brl(vf['irrf_ferias'])}")
                        st.success(f"**LÍQUIDO: {fmt_brl(vf['total_liquido'])}**")
                    col_salvar, col_pdf = st.columns(2)
                    with col_salvar:
                        if st.button("💾 Salvar Férias"):
                            if "folha_pagamento" not in func:
                                func["folha_pagamento"] = {}
                            func["folha_pagamento"][mes] = {**vf, "calculado_em": datetime.now().isoformat()}
                            salvar_funcionarios(todos_funcs)
                            # Evento S-2230
                            caminho_xml, nome_xml, _ = gerar_xml_ferias(func, mes, vf)
                            if nome_xml:
                                ev_id = adicionar_evento_fila(
                                    tipo="S-2230",
                                    grupo="Não Periódico",
                                    descricao=f"Afastamento (Férias) — {func['nome']} — {mes}",
                                    func_nome=func["nome"], func_id=func["id"],
                                    arquivo_xml=nome_xml,
                                )
                                st.info(f"📤 Evento S-2230 adicionado à fila eSocial (ID #{ev_id})")
                            log_acao("FERIAS_SALVAS", f"{func['nome']} — {mes}")
                            st.success("Férias salvas!")
                            del st.session_state[calc_key]
                            st.rerun()
                    _sk_fv = f"_pdf_fv_{func['id']}_{mes}"
                    with col_pdf:
                        if st.button("📄 PDF Férias"):
                            _pdf_store(_sk_fv, gerar_ferias_pdf(func, mes, vf))
                        _pdf_btn(_sk_fv,
                                 f"ferias_{func['nome'].replace(' ','_')}_{mes.replace('/','')}.pdf")
        except Exception as e:
            logger.error(f"Erro Férias: {e}")
            st.error(f"Erro: {e}")

    # ====================== RESCISÃO ======================
    elif menu == "⚖️ Rescisão":
        if not tem_permissao("coordenador"):
            st.error("Acesso negado.")
            st.stop()
        st.header("⚖️ Cálculo de Rescisão Contratual")
        try:
            todos_funcs = carregar_funcionarios()
            funcs = [f for f in todos_funcs if f.get("situacao") == "Ativo"]
            if not funcs:
                st.warning("Nenhum funcionário ativo.")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    nome_sel = st.selectbox("Funcionário", [f["nome"] for f in funcs])
                    func = next(f for f in funcs if f["nome"] == nome_sel)
                with col2:
                    data_des = st.date_input("Data de Desligamento", value=date.today())
                    motivo = st.selectbox("Motivo", [
                        "Demissão sem Justa Causa",
                        "Pedido de Demissão",
                        "Acordo entre as partes (§ 484-A CLT)",
                        "Justa Causa pelo Empregador",
                    ])
                st.info(f"**Admissão:** {func.get('data_admissao','N/A')} | **Salário:** {fmt_brl(func.get('salario_base',0))}")

                if st.button("🔄 Calcular Rescisão", type="primary"):
                    try:
                        import calendar
                        salario = func.get("salario_base", 0)
                        adm_date = date.fromisoformat(func.get("data_admissao", str(date.today())))
                        des_date = data_des
                        dias_no_mes = calendar.monthrange(des_date.year, des_date.month)[1]
                        dia_inicio_mes = adm_date.day if (adm_date.year == des_date.year and adm_date.month == des_date.month) else 1
                        dias_trab = des_date.day - dia_inicio_mes + 1
                        saldo_salario = round(salario / dias_no_mes * dias_trab, 2)
                        meses_total = (des_date.year - adm_date.year) * 12 + (des_date.month - adm_date.month)
                        if des_date.day < adm_date.day:
                            meses_total -= 1
                        meses_total = max(0, meses_total)
                        anos_serv = meses_total // 12
                        avos_ferias = max(1, min(12, meses_total % 12 + (1 if des_date.day >= adm_date.day else 0))) if meses_total > 0 else 0
                        ferias_prop = round(salario * (avos_ferias / 12), 2)
                        ferias_prop_total = round(ferias_prop * (4 / 3), 2)
                        ferias_vencidas = 0.0
                        avos_13 = calcular_avos(str(adm_date), des_date.year)
                        decimo_prop = round(salario * (avos_13 / 12), 2)
                        aviso_previo = 0.0
                        if "sem Justa Causa" in motivo or "Acordo" in motivo:
                            dias_aviso = 30 + min(60, anos_serv * 3)
                            aviso_previo = round(salario / 30 * dias_aviso, 2)
                            if "Acordo" in motivo:
                                aviso_previo = round(aviso_previo / 2, 2)
                        fgts_estimado = round(salario * 0.08 * meses_total, 2)
                        fgts_multa = 0.0
                        if "sem Justa Causa" in motivo:
                            fgts_multa = round(fgts_estimado * 0.40, 2)
                        elif "Acordo" in motivo:
                            fgts_multa = round(fgts_estimado * 0.20, 2)
                        total_bruto = round(saldo_salario + ferias_vencidas + ferias_prop_total + decimo_prop + aviso_previo + fgts_multa, 2)
                        base_inss = round(saldo_salario + ferias_prop_total + decimo_prop + aviso_previo, 2)
                        inss_resc = calcular_inss(min(base_inss, 8157.41))
                        base_irrf = round(base_inss - inss_resc, 2)
                        irrf_resc = calcular_irrf(base_irrf, func.get("num_dependentes", 0))
                        liquido = round(total_bruto - inss_resc - irrf_resc, 2)
                        valores = {
                            "saldo_salario": saldo_salario,
                            "ferias_vencidas": ferias_vencidas,
                            "ferias_proporcionais": ferias_prop_total,
                            "decimo_proporcional": decimo_prop,
                            "aviso_previo": aviso_previo,
                            "fgts_deposito": fgts_estimado,
                            "fgts_multa": fgts_multa,
                            "total_bruto": total_bruto,
                            "inss_rescisao": inss_resc,
                            "irrf_rescisao": irrf_resc,
                            "liquido": liquido,
                        }
                        st.session_state["rescisao_valores"] = valores
                        st.session_state["rescisao_func"] = func
                        st.session_state["rescisao_data"] = str(data_des)
                        st.session_state["rescisao_motivo"] = motivo
                        log_acao("RESCISAO_CALC", f"{func['nome']} — {data_des}")
                    except Exception as e:
                        logger.error(f"Erro rescisão: {e}")
                        st.error(f"Erro: {e}")

                if ("rescisao_valores" in st.session_state
                        and st.session_state.get("rescisao_func", {}).get("id") == func.get("id")):
                    valores = st.session_state["rescisao_valores"]
                    st.divider()
                    st.subheader("Verbas Rescisórias")
                    mapa_exib = [
                        ("saldo_salario","Saldo de Salário"),
                        ("ferias_proporcionais","Férias Proporcionais + 1/3"),
                        ("ferias_vencidas","Férias Vencidas + 1/3"),
                        ("decimo_proporcional","13º Proporcional"),
                        ("aviso_previo","Aviso Prévio Indenizado"),
                        ("fgts_deposito","FGTS do Período"),
                        ("fgts_multa","Multa FGTS"),
                    ]
                    col_v1, col_v2 = st.columns(2)
                    with col_v1:
                        for k, label in mapa_exib[:4]:
                            if valores.get(k, 0) > 0:
                                st.write(f"**{label}:** {fmt_brl(valores[k])}")
                    with col_v2:
                        for k, label in mapa_exib[4:]:
                            if valores.get(k, 0) > 0:
                                st.write(f"**{label}:** {fmt_brl(valores[k])}")
                        st.write(f"**(-) INSS:** {fmt_brl(valores.get('inss_rescisao',0))}")
                        st.write(f"**(-) IRRF:** {fmt_brl(valores.get('irrf_rescisao',0))}")
                    st.success(f"**LÍQUIDO A RECEBER: {fmt_brl(valores.get('liquido',0))}**")

                    col_pdf_r, col_xml_r = st.columns(2)
                    _sk_resc = f"_pdf_resc_{func['id']}"
                    with col_pdf_r:
                        if st.button("📄 PDF Rescisão"):
                            _pdf_store(_sk_resc, gerar_rescisao_pdf(func, data_des, motivo, valores))
                        _pdf_btn(_sk_resc,
                                 f"rescisao_{func['nome'].replace(' ','_')}_{str(data_des).replace('-','')}.pdf")
                    with col_xml_r:
                        if st.button("📤 XML eSocial + Fila"):
                            caminho, arq, _ = gerar_xml_desligamento(func, str(data_des), motivo)
                            if caminho:
                                ev_id = adicionar_evento_fila(
                                    tipo="S-2299",
                                    grupo="Não Periódico",
                                    descricao=f"Desligamento — {func['nome']} — {motivo}",
                                    func_nome=func["nome"], func_id=func["id"],
                                    arquivo_xml=arq,
                                    dados_extras={"motivo": motivo, "data_desligamento": str(data_des)}
                                )
                                st.success(f"✅ XML gerado e adicionado à fila eSocial (ID #{ev_id})")
                                _xml_store("_xml_resc_data", caminho)
                                st.session_state["_xml_resc_arq"] = arq
                        _xml_btn("_xml_resc_data",
                                 st.session_state.get("_xml_resc_arq", "S-2299.xml"),
                                 label="⬇️ Baixar XML")

                    if st.button("⚠️ Confirmar Desligamento (Inativar)"):
                        func["situacao"] = "Inativo"
                        func["data_desligamento"] = str(data_des)
                        func["motivo_desligamento"] = motivo
                        salvar_funcionarios(todos_funcs)
                        log_acao("FUNC_INATIVADO", f"{func['nome']} — {data_des}")
                        st.success(f"Funcionário {func['nome']} inativado!")
                        for k in ["rescisao_valores","rescisao_func","rescisao_data","rescisao_motivo"]:
                            st.session_state.pop(k, None)
                        st.rerun()
        except Exception as e:
            logger.error(f"Erro Rescisão: {e}")
            st.error(f"Erro: {e}")

    # ====================== eSocial — PAINEL DE TRANSMISSÃO ======================
    elif menu == "📤 eSocial — Painel de Transmissão":
        if not tem_permissao("coordenador"):
            st.error("Acesso negado.")
            st.stop()
        st.header("📤 eSocial — Painel de Controle e Transmissão")

        STATUS_CORES = {
            "Pendente":     "🟡",
            "Aguardando":   "🔵",
            "Transmitido":  "🟢",
            "Rejeitado":    "🔴",
            "Cancelado":    "⚫",
        }
        GRUPO_ICONES = {
            "Periódico":     "📅",
            "Não Periódico": "⚡",
        }

        try:
            tab_painel, tab_novo, tab_xml = st.tabs([
                "📊 Painel Geral",
                "➕ Gerar Evento Manual",
                "🔧 Geração de XMLs",
            ])

            # ── Painel Geral ────────────────────────────────────
            with tab_painel:
                fila = carregar_fila_esocial()

                # Métricas
                col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
                col_m1.metric("Total Eventos", len(fila))
                col_m2.metric("🟡 Pendentes",  len([e for e in fila if e["status"] == "Pendente"]))
                col_m3.metric("🔵 Aguardando", len([e for e in fila if e["status"] == "Aguardando"]))
                col_m4.metric("🟢 Transmitidos", len([e for e in fila if e["status"] == "Transmitido"]))
                col_m5.metric("🔴 Rejeitados",   len([e for e in fila if e["status"] == "Rejeitado"]))

                st.divider()

                # Filtros
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    filtro_status = st.selectbox("Filtrar por Status",
                                                  ["Todos", "Pendente", "Aguardando", "Transmitido", "Rejeitado", "Cancelado"])
                with col_f2:
                    filtro_grupo = st.selectbox("Filtrar por Grupo",
                                                 ["Todos", "Periódico", "Não Periódico"])
                with col_f3:
                    filtro_tipo = st.selectbox("Filtrar por Tipo",
                                                ["Todos", "S-1200", "S-2200", "S-2230", "S-2299", "Outro"])

                fila_filtrada = fila
                if filtro_status != "Todos":
                    fila_filtrada = [e for e in fila_filtrada if e["status"] == filtro_status]
                if filtro_grupo != "Todos":
                    fila_filtrada = [e for e in fila_filtrada if e["grupo"] == filtro_grupo]
                if filtro_tipo != "Todos":
                    fila_filtrada = [e for e in fila_filtrada if e["tipo"] == filtro_tipo]

                # Tabela de eventos
                if not fila_filtrada:
                    st.info("Nenhum evento encontrado para os filtros selecionados.")
                else:
                    st.subheader(f"{len(fila_filtrada)} evento(s) encontrado(s)")

                    for ev in sorted(fila_filtrada, key=lambda x: x["id"], reverse=True):
                        icone_status = STATUS_CORES.get(ev["status"], "⚪")
                        icone_grupo  = GRUPO_ICONES.get(ev["grupo"], "📌")
                        with st.expander(
                            f"{icone_status} #{ev['id']} | {icone_grupo} {ev['tipo']} — {ev['descricao'][:60]}"
                        ):
                            col_info1, col_info2 = st.columns(2)
                            with col_info1:
                                st.write(f"**Tipo:** `{ev['tipo']}`")
                                st.write(f"**Grupo:** {ev['grupo']}")
                                st.write(f"**Status:** {icone_status} {ev['status']}")
                                st.write(f"**Funcionário:** {ev.get('func_nome','—')}")
                            with col_info2:
                                st.write(f"**Criado em:** {ev.get('criado_em','')[:16].replace('T',' ')}")
                                st.write(f"**Atualizado:** {ev.get('atualizado_em','')[:16].replace('T',' ')}")
                                if ev.get("protocolo"):
                                    st.write(f"**Protocolo:** `{ev['protocolo']}`")
                                if ev.get("arquivo_xml"):
                                    st.write(f"**Arquivo XML:** `{ev['arquivo_xml']}`")

                            # Histórico
                            with st.expander("📜 Histórico de Status"):
                                for h in ev.get("historico", []):
                                    st.markdown(
                                        f"- `{h['data'][:16].replace('T',' ')}` → **{h['status']}** — {h.get('obs','')}"
                                    )

                            # Ações
                            st.markdown("**Ações:**")
                            col_a1, col_a2, col_a3, col_a4 = st.columns(4)

                            # Simular transmissão
                            if ev["status"] in ["Pendente", "Aguardando", "Rejeitado"]:
                                if col_a1.button("▶️ Simular Envio", key=f"send_{ev['id']}"):
                                    import random, string
                                    protocolo = "PROTO" + ''.join(random.choices(string.digits, k=12))
                                    atualizar_status_evento(ev["id"], "Transmitido",
                                                             obs=f"Transmissão simulada — protocolo gerado",
                                                             protocolo=protocolo)
                                    st.success(f"✅ Evento transmitido! Protocolo: {protocolo}")
                                    st.rerun()

                            # Marcar aguardando
                            if ev["status"] == "Pendente":
                                if col_a2.button("🔵 Aguardando", key=f"wait_{ev['id']}"):
                                    atualizar_status_evento(ev["id"], "Aguardando",
                                                             obs="Marcado como aguardando retificação/complemento")
                                    st.rerun()

                            # Marcar rejeitado
                            if ev["status"] in ["Pendente", "Aguardando", "Transmitido"]:
                                if col_a3.button("🔴 Rejeitar", key=f"rej_{ev['id']}"):
                                    atualizar_status_evento(ev["id"], "Rejeitado",
                                                             obs="Marcado manualmente como rejeitado")
                                    st.rerun()

                            # Cancelar
                            if ev["status"] not in ["Cancelado", "Transmitido"]:
                                if col_a4.button("⚫ Cancelar", key=f"canc_{ev['id']}"):
                                    atualizar_status_evento(ev["id"], "Cancelado",
                                                             obs="Cancelado pelo operador")
                                    st.rerun()

                            # Download do XML se existir
                            arq_xml = ev.get("arquivo_xml", "")
                            if arq_xml:
                                caminho_xml_ev = os.path.join(ESOCIAL_DIR, arq_xml)
                                if os.path.exists(caminho_xml_ev):
                                    _sk_ev = f"_xml_fila_{ev['id']}"
                                    if _sk_ev not in st.session_state:
                                        _xml_store(_sk_ev, caminho_xml_ev)
                                    _xml_btn(_sk_ev, arq_xml)

                # Ação em lote
                st.divider()
                st.subheader("⚡ Ações em Lote")
                col_lote1, col_lote2, col_lote3 = st.columns(3)
                with col_lote1:
                    if st.button("▶️ Transmitir Todos Pendentes", type="primary"):
                        import random, string
                        pendentes = [e for e in fila if e["status"] == "Pendente"]
                        for ev in pendentes:
                            protocolo = "PROTO" + ''.join(random.choices(string.digits, k=12))
                            atualizar_status_evento(ev["id"], "Transmitido",
                                                     obs="Transmissão em lote",
                                                     protocolo=protocolo)
                        st.success(f"✅ {len(pendentes)} evento(s) transmitido(s)!")
                        st.rerun()
                with col_lote2:
                    if st.button("⚫ Cancelar Todos Pendentes", type="secondary"):
                        pendentes = [e for e in fila if e["status"] == "Pendente"]
                        for ev in pendentes:
                            atualizar_status_evento(ev["id"], "Cancelado", obs="Cancelado em lote")
                        st.warning(f"{len(pendentes)} evento(s) cancelado(s).")
                        st.rerun()
                with col_lote3:
                    if st.button("🗑️ Limpar Transmitidos/Cancelados"):
                        fila_atual = carregar_fila_esocial()
                        fila_nova = [e for e in fila_atual if e["status"] not in ["Transmitido", "Cancelado"]]
                        removidos = len(fila_atual) - len(fila_nova)
                        salvar_fila_esocial(fila_nova)
                        log_acao("ESOCIAL_LIMPEZA", f"{removidos} eventos removidos")
                        st.success(f"🧹 {removidos} evento(s) removido(s) da fila.")
                        st.rerun()

            # ── Gerar Evento Manual ─────────────────────────────
            with tab_novo:
                st.subheader("➕ Adicionar Evento Manualmente à Fila")
                funcs_todos = carregar_funcionarios()

                col_n1, col_n2 = st.columns(2)
                with col_n1:
                    tipo_manual = st.selectbox("Tipo de Evento", [
                        "S-1200 — Remuneração do Trabalhador",
                        "S-1210 — Pagamentos de Rendimentos do Trabalho",
                        "S-2200 — Cadastramento Inicial / Admissão",
                        "S-2205 — Alteração de Dados Cadastrais",
                        "S-2206 — Alteração de Contrato de Trabalho",
                        "S-2230 — Afastamento Temporário",
                        "S-2299 — Desligamento",
                        "S-2400 — Cadastramento de Benefício",
                        "S-3000 — Exclusão de Eventos",
                    ])
                    grupo_manual = st.selectbox("Grupo", ["Periódico", "Não Periódico"])
                with col_n2:
                    desc_manual = st.text_area("Descrição do Evento *",
                                                placeholder="Descreva o evento eSocial...", height=80)
                    func_manual_nome = st.selectbox("Funcionário Relacionado (opcional)",
                                                     ["— Nenhum —"] + [f["nome"] for f in funcs_todos])
                obs_manual = st.text_input("Observação inicial")

                if st.button("➕ Adicionar à Fila", type="primary"):
                    if not desc_manual:
                        st.error("Preencha a descrição do evento!")
                    else:
                        tipo_cod = tipo_manual.split(" — ")[0]
                        func_ev = next((f for f in funcs_todos if f["nome"] == func_manual_nome), {})
                        ev_id = adicionar_evento_fila(
                            tipo=tipo_cod,
                            grupo=grupo_manual,
                            descricao=desc_manual,
                            func_nome=func_ev.get("nome", ""),
                            func_id=func_ev.get("id", 0),
                            dados_extras={"obs": obs_manual}
                        )
                        st.success(f"✅ Evento adicionado à fila com ID #{ev_id}!")
                        st.rerun()

            # ── Geração de XMLs ─────────────────────────────────
            with tab_xml:
                st.subheader("🔧 Geração de Arquivos XML eSocial")
                funcs_todos = carregar_funcionarios()
                funcs_ativos = [f for f in funcs_todos if f.get("situacao") == "Ativo"]

                sub_xml_tab1, sub_xml_tab2, sub_xml_tab3 = st.tabs([
                    "📅 S-1200 Folha (Periódico)",
                    "🆕 S-2200 Admissão",
                    "🚪 S-2299 Desligamento",
                ])

                with sub_xml_tab1:
                    st.write("**S-1200 — Remuneração do Trabalhador** (Evento Periódico)")
                    mes_1200 = st.selectbox("Mês de Referência", [f"{i:02d}/2026" for i in range(1, 13)], index=3, key="xml_1200_mes")
                    funcs_com_folha = [f for f in funcs_ativos if f.get("folha_pagamento", {}).get(mes_1200)]
                    st.info(f"{len(funcs_com_folha)} funcionário(s) com folha calculada para {mes_1200}.")
                    if funcs_com_folha:
                        if st.button("📄 Gerar XML S-1200", key="gerar_1200"):
                            caminho, arq, xml_str = gerar_xml_folha_pagamento(funcs_com_folha, mes_1200)
                            if arq:
                                ev_id = adicionar_evento_fila(
                                    tipo="S-1200", grupo="Periódico",
                                    descricao=f"Remuneração {mes_1200} — {len(funcs_com_folha)} func.",
                                    arquivo_xml=arq,
                                    dados_extras={"mes": mes_1200}
                                )
                                st.success(f"✅ XML gerado e adicionado à fila (ID #{ev_id})")
                                st.code(xml_str[:2000] + ("\n... [truncado]" if len(xml_str) > 2000 else ""), language="xml")
                                _xml_store("_xml_1200_data", caminho)
                                st.session_state["_xml_1200_arq"] = arq
                        _xml_btn("_xml_1200_data",
                                 st.session_state.get("_xml_1200_arq", "S-1200.xml"),
                                 label="⬇️ Baixar XML S-1200")
                    else:
                        st.warning("Calcule a folha de pagamento antes de gerar o XML.")

                with sub_xml_tab2:
                    st.write("**S-2200 — Cadastramento Inicial / Admissão** (Evento Não Periódico)")
                    if not funcs_todos:
                        st.warning("Nenhum funcionário cadastrado.")
                    else:
                        nome_adm = st.selectbox("Funcionário", [f["nome"] for f in funcs_todos], key="xml_2200")
                        func_adm = next(f for f in funcs_todos if f["nome"] == nome_adm)
                        st.json({
                            "nome": func_adm.get("nome"),
                            "cpf": func_adm.get("cpf"),
                            "data_admissao": func_adm.get("data_admissao"),
                            "cargo": func_adm.get("cargo"),
                            "salario": fmt_brl(func_adm.get("salario_base", 0)),
                        })
                        if st.button("📄 Gerar XML S-2200", key="gerar_2200"):
                            caminho, arq, xml_str = gerar_xml_admissao(func_adm)
                            if arq:
                                ev_id = adicionar_evento_fila(
                                    tipo="S-2200", grupo="Não Periódico",
                                    descricao=f"Admissão — {func_adm['nome']}",
                                    func_nome=func_adm["nome"], func_id=func_adm["id"],
                                    arquivo_xml=arq
                                )
                                st.success(f"✅ XML gerado e adicionado à fila (ID #{ev_id})")
                                st.code(xml_str[:2000] + ("\n... [truncado]" if len(xml_str) > 2000 else ""), language="xml")
                                _xml_store("_xml_2200_data", caminho)
                                st.session_state["_xml_2200_arq"] = arq
                        _xml_btn("_xml_2200_data",
                                 st.session_state.get("_xml_2200_arq", "S-2200.xml"),
                                 label="⬇️ Baixar XML S-2200")

                with sub_xml_tab3:
                    st.write("**S-2299 — Desligamento** (Evento Não Periódico)")
                    if not funcs_ativos:
                        st.warning("Nenhum funcionário ativo.")
                    else:
                        nome_desl = st.selectbox("Funcionário", [f["nome"] for f in funcs_ativos], key="xml_2299")
                        func_desl = next(f for f in funcs_ativos if f["nome"] == nome_desl)
                        data_desl_xml = st.date_input("Data de Desligamento", value=date.today(), key="xml_dt_2299")
                        motivo_desl_xml = st.selectbox("Motivo", [
                            "Demissão sem Justa Causa",
                            "Pedido de Demissão",
                            "Acordo entre as partes",
                            "Justa Causa",
                        ], key="xml_motivo_2299")
                        if st.button("📄 Gerar XML S-2299", key="gerar_2299"):
                            caminho, arq, xml_str = gerar_xml_desligamento(func_desl, str(data_desl_xml), motivo_desl_xml)
                            if arq:
                                ev_id = adicionar_evento_fila(
                                    tipo="S-2299", grupo="Não Periódico",
                                    descricao=f"Desligamento — {func_desl['nome']} — {motivo_desl_xml}",
                                    func_nome=func_desl["nome"], func_id=func_desl["id"],
                                    arquivo_xml=arq,
                                    dados_extras={"data": str(data_desl_xml), "motivo": motivo_desl_xml}
                                )
                                st.success(f"✅ XML gerado e adicionado à fila (ID #{ev_id})")
                                st.code(xml_str[:2000] + ("\n... [truncado]" if len(xml_str) > 2000 else ""), language="xml")
                                _xml_store("_xml_2299_data", caminho)
                                st.session_state["_xml_2299_arq"] = arq
                        _xml_btn("_xml_2299_data",
                                 st.session_state.get("_xml_2299_arq", "S-2299.xml"),
                                 label="⬇️ Baixar XML S-2299")

        except Exception as e:
            logger.error(f"Erro eSocial Painel: {e}\n{traceback.format_exc()}")
            st.error(f"Erro: {e}")

    # ====================== GESTÃO DE PONTO ======================
    elif menu == "🕒 Gestão de Ponto":
        if not tem_permissao("coordenador"):
            st.error("Acesso negado.")
            st.stop()
        
        st.header("🕒 Gestão de Ponto")
        st.info("Registre horas extras e faltas para serem processadas automaticamente na folha de pagamento.")
        
        try:
            funcs = carregar_funcionarios()
            ativos = [f for f in funcs if f.get("situacao") == "Ativo"]
            
            if not ativos:
                st.warning("Nenhum funcionário ativo para lançar ponto.")
            else:
                col_p1, col_p2 = st.columns([1, 1])
                with col_p1:
                    nome_p = st.selectbox("Selecione o Funcionário", [f["nome"] for f in ativos])
                    func_p = next(f for f in ativos if f["nome"] == nome_p)
                with col_p2:
                    mes_p = st.selectbox("Mês de Referência", [f"{i:02d}/2026" for i in range(1, 13)], 
                                        index=datetime.now().month - 1)

                st.subheader(f"Lançamentos para {nome_p} — {mes_p}")
                
                # Garantir estrutura de ponto
                if "ponto" not in func_p:
                    func_p["ponto"] = {}
                if mes_p not in func_p["ponto"]:
                    func_p["ponto"][mes_p] = {"he_50": 0.0, "he_100": 0.0, "faltas": 0, "dsr_sobre_he": 0.0}

                with st.form("form_ponto"):
                    c1, c2, c3 = st.columns(3)
                    he50 = c1.number_input("Horas Extras 50% (Qtd)", min_value=0.0, step=0.5, value=float(func_p["ponto"][mes_p]["he_50"]))
                    he100 = c2.number_input("Horas Extras 100% (Qtd)", min_value=0.0, step=0.5, value=float(func_p["ponto"][mes_p]["he_100"]))
                    faltas = c3.number_input("Faltas (Dias)", min_value=0, step=1, value=int(func_p["ponto"][mes_p]["faltas"]))
                    
                    obs_p = st.text_area("Observações", value=func_p["ponto"][mes_p].get("obs", ""))
                    
                    if st.form_submit_button("💾 Salvar Lançamentos", type="primary"):
                        func_p["ponto"][mes_p] = {
                            "he_50": he50, "he_100": he100, "faltas": faltas, "obs": obs_p,
                            "atualizado_em": datetime.now().isoformat()
                        }
                        salvar_funcionarios(funcs)
                        st.success(f"✅ Lançamentos salvos para {nome_p}!")
                        log_acao("PONTO_ATUALIZADO", f"{nome_p} ({mes_p}) - HE50:{he50} HE100:{he100} Faltas:{faltas}")

                # Tabela de lançamentos recentes
                st.divider()
                st.subheader("Resumo de Lançamentos do Mês")
                resumo_ponto = []
                for f in ativos:
                    if "ponto" in f and mes_p in f["ponto"]:
                        p = f["ponto"][mes_p]
                        if p["he_50"] > 0 or p["he_100"] > 0 or p["faltas"] > 0:
                            resumo_ponto.append({
                                "Funcionário": f["nome"],
                                "HE 50%": p["he_50"],
                                "HE 100%": p["he_100"],
                                "Faltas": p["faltas"]
                            })
                
                if resumo_ponto:
                    st.table(pd.DataFrame(resumo_ponto))
                else:
                    st.caption("Nenhum lançamento registrado para este mês.")

        except Exception as e:
            logger.error(f"Erro Gestão de Ponto: {e}")
            st.error(f"Erro: {e}")

    # ====================== IMPORTAÇÃO DE DADOS ======================
    elif menu == "📥 Importação de Dados":
        if not tem_permissao("coordenador"):
            st.error("Acesso negado.")
            st.stop()
        
        st.header("📥 Importação de Dados via Planilha")
        tab_func, tab_folha = st.tabs(["👥 Importar Funcionários", "💰 Importar Itens de Folha"])
        
        with tab_func:
            st.subheader("Importação de Cadastro")
            st.info("A planilha deve conter as colunas: nome, cpf, rg, data_nascimento, data_admissao, cargo, departamento, salario_base, dependentes.")
            
            # Gerar CSV de exemplo
            df_modelo = pd.DataFrame(columns=["nome", "cpf", "rg", "data_nascimento", "data_admissao", "cargo", "departamento", "salario_base", "dependentes"])
            csv_modelo = df_modelo.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Baixar Modelo CSV (Cadastro)", csv_modelo, "modelo_cadastro.csv", "text/csv")
            
            arq_f = st.file_uploader("Selecione o arquivo CSV de Cadastro", type=["csv"], key="up_func")
            if arq_f:
                try:
                    df_up = pd.read_csv(arq_f)
                    st.write("Prévia dos dados:")
                    st.dataframe(df_up.head())
                    
                    if st.button("🚀 Confirmar Importação de Cadastro"):
                        funcs_atuais = carregar_funcionarios()
                        cpfs_existentes = {re.sub(r'[^0-9]', '', str(f.get("cpf", ""))) for f in funcs_atuais}
                        sucesso = 0
                        erros = 0
                        cpfs_invalidos = 0
                        
                        for _, row in df_up.iterrows():
                            cpf_orig = str(row['cpf']).strip()
                            cpf_limpo = re.sub(r'[^0-9]', '', cpf_orig)
                            
                            # Validar CPF
                            if not validar_cpf(cpf_limpo):
                                cpfs_invalidos += 1
                                continue
                                
                            if cpf_limpo in cpfs_existentes:
                                erros += 1
                                continue
                            
                            novo_id = max([f.get("id", 0) for f in funcs_atuais], default=0) + 1
                            novo_f = {
                                "id": novo_id,
                                "nome": str(row['nome']).strip(),
                                "cpf": formatar_cpf(cpf_limpo),
                                "rg": str(row.get('rg', '')).strip(),
                                "data_nascimento": str(row.get('data_nascimento', '1990-01-01')),
                                "data_admissao": str(row.get('data_admissao', date.today().isoformat())),
                                "cargo": str(row.get('cargo', '')).strip(),
                                "departamento": str(row.get('departamento', '')).strip(),
                                "salario_base": round(float(row.get('salario_base', 0)), 2),
                                "num_dependentes": int(row.get('dependentes', 0)),
                                "tem_plano_saude": "Não",
                                "valor_plano": 0.0,
                                "valor_vt_mensal": 0.0,
                                "situacao": "Ativo",
                                "folha_pagamento": {}
                            }
                            funcs_atuais.append(novo_f)
                            cpfs_existentes.add(cpf_limpo)
                            pasta_documentos_func(novo_id)
                            sucesso += 1
                            
                        salvar_funcionarios(funcs_atuais)
                        if sucesso > 0:
                            st.success(f"✅ Importação concluída: {sucesso} novos funcionários.")
                        if erros > 0:
                            st.warning(f"⚠️ {erros} CPFs já cadastrados foram ignorados.")
                        if cpfs_invalidos > 0:
                            st.error(f"❌ {cpfs_invalidos} CPFs inválidos foram ignorados.")
                        log_acao("IMPORT_CADASTRO", f"{sucesso} func. importados, {erros} duplicados, {cpfs_invalidos} inválidos")
                except Exception as e:
                    st.error(f"Erro ao processar arquivo: {e}")
                    logger.error(f"Erro Import Cadastro: {e}")

        with tab_folha:
            st.subheader("Importação de Itens de Folha")
            st.info("A planilha deve conter as colunas: cpf, mes, descricao, valor, tipo (Provento ou Desconto).")
            
            # Gerar CSV de exemplo
            df_modelo_f = pd.DataFrame(columns=["cpf", "mes", "descricao", "valor", "tipo"])
            csv_modelo_f = df_modelo_f.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Baixar Modelo CSV (Folha)", csv_modelo_f, "modelo_folha.csv", "text/csv")
            
            arq_folha = st.file_uploader("Selecione o arquivo CSV de Folha", type=["csv"], key="up_folha")
            if arq_folha:
                try:
                    df_folha = pd.read_csv(arq_folha)
                    st.write("Prévia dos dados:")
                    st.dataframe(df_folha.head())
                    
                    if st.button("🚀 Confirmar Importação de Itens de Folha"):
                        funcs_atuais = carregar_funcionarios()
                        importados = 0
                        nao_encontrados = 0
                        
                        for _, row in df_folha.iterrows():
                            cpf_v = str(row['cpf']).strip()
                            mes_v = str(row['mes']).strip() # Ex: 04/2026
                            
                            f_alvo = next((f for f in funcs_atuais if str(f["cpf"]).strip() == cpf_v), None)
                            if not f_alvo:
                                nao_encontrados += 1
                                continue
                            
                            if "folha_pagamento" not in f_alvo:
                                f_alvo["folha_pagamento"] = {}
                            
                            # Se a folha não estiver calculada, criar estrutura básica
                            if mes_v not in f_alvo["folha_pagamento"]:
                                s = f_alvo.get("salario_base", 0)
                                inss = calcular_inss(s)
                                irrf = calcular_irrf(s - inss, f_alvo.get("num_dependentes", 0))
                                vt = calcular_vt(s, f_alvo.get("valor_vt_mensal", 0))
                                p = f_alvo.get("valor_plano", 0) if f_alvo.get("tem_plano_saude") == "Sim" else 0
                                f_alvo["folha_pagamento"][mes_v] = {
                                    "salario_base": s, "inss": inss, "irrf": irrf, "base_irrf": s - inss,
                                    "vt": vt, "plano_saude": p, "itens_extras": [],
                                    "calculado_em": datetime.now().isoformat()
                                }
                            
                            novo_item = {
                                "descricao": str(row['descricao']),
                                "valor": float(row['valor']),
                                "tipo": str(row['tipo']).capitalize() # Provento ou Desconto
                            }
                            
                            if "itens_extras" not in f_alvo["folha_pagamento"][mes_v]:
                                f_alvo["folha_pagamento"][mes_v]["itens_extras"] = []
                            
                            f_alvo["folha_pagamento"][mes_v]["itens_extras"].append(novo_item)
                            
                            # Recalcular líquido
                            folha = f_alvo["folha_pagamento"][mes_v]
                            s_b = folha["salario_base"]
                            ins = folha["inss"]
                            irr = folha["irrf"]
                            vtt = folha["vt"]
                            pla = folha["plano_saude"]
                            ext = folha["itens_extras"]
                            
                            tp = sum(i['valor'] for i in ext if i['tipo'] == "Provento")
                            td = sum(i['valor'] for i in ext if i['tipo'] == "Desconto")
                            folha["liquido"] = round((s_b + tp) - (ins + irr + vtt + pla + td), 2)
                            
                            importados += 1
                            
                        salvar_funcionarios(funcs_atuais)
                        st.success(f"Importação de folha concluída: {importados} itens processados. ({nao_encontrados} CPFs não encontrados)")
                        log_acao("IMPORT_FOLHA", f"{importados} itens importados")
                except Exception as e:
                    st.error(f"Erro ao processar arquivo: {e}")

    # ====================== RELATÓRIOS ======================
    elif menu == "📄 Relatórios":
        st.header("📄 Relatórios")
        try:
            funcs_todos = carregar_funcionarios()
            mostrar_inativos = st.checkbox("Incluir Inativos")
            funcs = funcs_todos if mostrar_inativos else [f for f in funcs_todos if f.get("situacao") == "Ativo"]
            if not funcs:
                st.warning("Nenhum funcionário.")
            else:
                tipo = st.selectbox("Tipo de Relatório", [
                    "Memória de Cálculo",
                    "Folha Analítica (Tabela)",
                    "Folha Analítica PDF",
                    "Resumo Geral da Folha",
                    "Ficha de Cadastro PDF",
                    "Ficha Financeira Anual PDF",
                    "13º Salário PDF",
                    "Férias PDF",
                ])
                mes = st.selectbox("Mês de Referência", [f"{i:02d}/2026" for i in range(1, 13)], index=3)

                if tipo == "Memória de Cálculo":
                    nome_m = st.selectbox("Funcionário", [f["nome"] for f in funcs])
                    func_m = next(f for f in funcs if f["nome"] == nome_m)
                    salario = func_m.get("salario_base", 0)
                    inss = calcular_inss(salario)
                    base_ir = salario - inss
                    irrf = calcular_irrf(base_ir, func_m.get("num_dependentes", 0))
                    vt = calcular_vt(salario, func_m.get("valor_vt_mensal", 0))
                    plano = func_m.get("valor_plano", 0) if func_m.get("tem_plano_saude") == "Sim" else 0
                    liquido = round(salario - inss - irrf - vt - plano, 2)
                    st.subheader(f"Memória de Cálculo — {func_m['nome']}")
                    for k, v in {
                        "Salário Base": fmt_brl(salario),
                        "INSS": fmt_brl(inss),
                        "Base IRRF": fmt_brl(base_ir),
                        "IRRF": fmt_brl(irrf),
                        "Vale-Transporte": fmt_brl(vt),
                        "Plano de Saúde": fmt_brl(plano),
                        "Total Descontos": fmt_brl(inss+irrf+vt+plano),
                        "Salário Líquido": fmt_brl(liquido),
                    }.items():
                        st.write(f"**{k}:** {v}")

                elif tipo == "Folha Analítica (Tabela)":
                    dados_t = []
                    for func in funcs:
                        folha = func.get("folha_pagamento", {}).get(mes, {})
                        s = folha.get("salario_base", func.get("salario_base", 0)) if folha else func.get("salario_base", 0)
                        inss = folha.get("inss", calcular_inss(s)) if folha else calcular_inss(s)
                        irrf = folha.get("irrf", 0) if folha else calcular_irrf(s - inss, func.get("num_dependentes", 0))
                        vt = folha.get("vt", 0) if folha else calcular_vt(s, func.get("valor_vt_mensal", 0))
                        plano = folha.get("plano_saude", 0) if folha else (func.get("valor_plano", 0) if func.get("tem_plano_saude") == "Sim" else 0)
                        extras = folha.get("itens_extras", [])
                        op = sum(i['valor'] for i in extras if i['tipo'] == "Provento")
                        od = sum(i['valor'] for i in extras if i['tipo'] == "Desconto")
                        liq = folha.get("liquido", 0) if folha else round(s - inss - irrf - vt - plano, 2)
                        dados_t.append({"Nome": func["nome"], "Cargo": func.get("cargo",""),
                                        "Salário Bruto": s, "INSS": inss, "IRRF": irrf,
                                        "VT": vt, "Plano": plano, "Outros Prov.": op, "Outros Desc.": od, "Líquido": liq})
                    df = pd.DataFrame(dados_t)
                    st.dataframe(df.style.format({c: "R$ {:,.2f}" for c in ["Salário Bruto","INSS","IRRF","VT","Plano", "Outros Prov.", "Outros Desc.", "Líquido"]}),
                                 use_container_width=True)

                elif tipo == "Folha Analítica PDF":
                    if st.button("📄 Gerar"):
                        _pdf_store("_pdf_folha_analitica", gerar_folha_analitica_pdf(funcs, mes))
                    _pdf_btn("_pdf_folha_analitica",
                             f"folha_analitica_{mes.replace('/','')}.pdf")

                elif tipo == "Resumo Geral da Folha":
                    total_b = 0.0
                    total_inss = 0.0
                    total_irrf = 0.0
                    total_vt = 0.0
                    total_plano = 0.0
                    total_extras_p = 0.0
                    total_extras_d = 0.0
                    total_liq = 0.0
                    
                    for f in funcs:
                        folha = f.get("folha_pagamento", {}).get(mes, {})
                        if folha:
                            total_b += folha.get("salario_base", 0)
                            total_inss += folha.get("inss", 0)
                            total_irrf += folha.get("irrf", 0)
                            total_vt += folha.get("vt", 0)
                            total_plano += folha.get("plano_saude", 0)
                            ex = folha.get("itens_extras", [])
                            total_extras_p += sum(i['valor'] for i in ex if i['tipo'] == "Provento")
                            total_extras_d += sum(i['valor'] for i in ex if i['tipo'] == "Desconto")
                            total_liq += folha.get("liquido", 0)
                        else:
                            s = f.get("salario_base", 0)
                            i = calcular_inss(s)
                            ir = calcular_irrf(s - i, f.get("num_dependentes", 0))
                            v = calcular_vt(s, f.get("valor_vt_mensal", 0))
                            p = f.get("valor_plano", 0) if f.get("tem_plano_saude") == "Sim" else 0
                            total_b += s
                            total_inss += i
                            total_irrf += ir
                            total_vt += v
                            total_plano += p
                            total_liq += round(s - i - ir - v - p, 2)
                    
                    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                    col_r1.metric("Total Bruto", fmt_brl(total_b))
                    col_r1.metric("Outros Prov.", fmt_brl(total_extras_p))
                    col_r2.metric("Total INSS", fmt_brl(total_inss))
                    col_r2.metric("Total IRRF", fmt_brl(total_irrf))
                    col_r3.metric("Total VT", fmt_brl(total_vt))
                    col_r3.metric("Total Plano", fmt_brl(total_plano))
                    col_r4.metric("Outros Desc.", fmt_brl(total_extras_d))
                    col_r4.metric("Total Líquido", fmt_brl(total_liq))
                    empresa = carregar_dados_empresa()
                    regime = empresa.get("regime", "Simples Nacional")
                    aliq_patronal = empresa.get("aliquota_patronal", 20.0) / 100
                    aliq_rat = empresa.get("aliquota_rat", 2.0) / 100
                    aliq_terc = empresa.get("aliquota_terceiros", 5.8) / 100
                    
                    encargos_patronais = total_b * (aliq_patronal + aliq_rat + aliq_terc)
                    fgts_patronal = total_b * 0.08
                    
                    st.metric(f"Encargos Patronais ({regime})", fmt_brl(round(encargos_patronais, 2)))
                    st.metric("FGTS Patronal (8%)", fmt_brl(round(fgts_patronal, 2)))
                    st.metric("CUSTO TOTAL ESTIMADO", fmt_brl(round(total_b + encargos_patronais + fgts_patronal, 2)))
                    if st.button("📄 Exportar PDF"):
                        _pdf_store("_pdf_resumo_folha", gerar_resumo_folha_pdf(funcs, mes))
                    _pdf_btn("_pdf_resumo_folha",
                             f"resumo_folha_{mes.replace('/','')}.pdf")

                elif tipo == "Ficha de Cadastro PDF":
                    nome_fc = st.selectbox("Funcionário", [f["nome"] for f in funcs], key="ficha_cad_sel")
                    func_fc = next(f for f in funcs if f["nome"] == nome_fc)
                    if st.button("📄 Gerar"):
                        _pdf_store("_pdf_ficha_cad", gerar_ficha_cadastro_pdf(func_fc))
                    _pdf_btn("_pdf_ficha_cad",
                             f"ficha_{func_fc['nome'].replace(' ','_')}.pdf")

                elif tipo == "Ficha Financeira Anual PDF":
                    nome_ffa = st.selectbox("Funcionário", [f["nome"] for f in funcs], key="ffa_sel")
                    func_ffa = next(f for f in funcs if f["nome"] == nome_ffa)
                    ano_ffa = st.selectbox("Ano", [2024,2025,2026], index=2, key="ffa_ano")
                    if st.button("📄 Gerar"):
                        _pdf_store("_pdf_ficha_fin", gerar_ficha_financeira_anual_pdf(func_ffa, ano_ffa))
                    _pdf_btn("_pdf_ficha_fin",
                             f"ficha_financeira_{func_ffa['nome'].replace(' ','_')}_{ano_ffa}.pdf")

                elif tipo == "13º Salário PDF":
                    nome_13 = st.selectbox("Funcionário", [f["nome"] for f in funcs], key="r13_sel")
                    func_13 = next(f for f in funcs if f["nome"] == nome_13)
                    mes_13 = st.selectbox("Mês", [f"{i:02d}/2026" for i in range(1,13)], index=10, key="r13_mes")
                    folha_13 = func_13.get("folha_pagamento",{}).get(mes_13,{})
                    if "decimo_terceiro_bruto" in folha_13:
                        if st.button("📄 Gerar"):
                            _pdf_store("_pdf_rel_13", gerar_decimo_pdf(
                                func_13, int(mes_13.split("/")[1]),
                                folha_13.get("tipo_13","Final"),
                                folha_13.get("decimo_terceiro_bruto",0),
                                folha_13.get("avos_13",12)))
                        _pdf_btn("_pdf_rel_13",
                                 f"13salario_{func_13['nome'].replace(' ','_')}_{mes_13.replace('/','')}.pdf",
                                 label="⬇️ Baixar")
                    else:
                        st.warning("13º não calculado para este mês.")

                elif tipo == "Férias PDF":
                    nome_fv = st.selectbox("Funcionário", [f["nome"] for f in funcs], key="rfv_sel")
                    func_fv = next(f for f in funcs if f["nome"] == nome_fv)
                    folha_fv = func_fv.get("folha_pagamento",{}).get(mes,{})
                    if "total_liquido" in folha_fv:
                        if st.button("📄 Gerar"):
                            _pdf_store("_pdf_rel_fv", gerar_ferias_pdf(func_fv, mes, folha_fv))
                        _pdf_btn("_pdf_rel_fv",
                                 f"ferias_{func_fv['nome'].replace(' ','_')}_{mes.replace('/','')}.pdf",
                                 label="⬇️ Baixar")
                    else:
                        st.warning("Férias não calculadas para este mês.")

        except Exception as e:
            logger.error(f"Erro Relatórios: {e}")
            st.error(f"Erro: {e}")

    # ====================== CONFIGURAÇÕES DA EMPRESA ======================
    elif menu == "🏢 Configurações da Empresa":
        if not tem_permissao("admin"):
            st.error("Acesso negado.")
        else:
            st.header("🏢 Configurações da Empresa")
            empresa = carregar_dados_empresa()
            
            with st.form("form_empresa"):
                st.subheader("Dados Cadastrais")
                col1, col2 = st.columns(2)
                with col1:
                    emp_nome = st.text_input("Razão Social", value=empresa.get("nome", ""))
                    emp_cnpj = st.text_input("CNPJ", value=empresa.get("cnpj", ""))
                    emp_end  = st.text_input("Endereço", value=empresa.get("endereco", ""))
                with col2:
                    emp_regime = st.selectbox("Regime Tributário", 
                                             ["Simples Nacional", "Lucro Presumido", "Lucro Real"],
                                             index=0 if empresa.get("regime") == "Simples Nacional" else 1)
                    st.caption("ℹ️ Simples Nacional (exceto Anexo IV) não recolhe INSS Patronal (20%).")
                
                st.divider()
                st.subheader("Configuração de Encargos Patronais")
                c1, c2, c3 = st.columns(3)
                with c1:
                    aliq_p = st.number_input("INSS Patronal (%)", value=float(empresa.get("aliquota_patronal", 0.0)), step=1.0)
                with c2:
                    aliq_r = st.number_input("RAT / FAP (%)", value=float(empresa.get("aliquota_rat", 0.0)), step=0.1)
                with c3:
                    aliq_t = st.number_input("Terceiros (%)", value=float(empresa.get("aliquota_terceiros", 0.0)), step=0.1)
                
                if st.form_submit_button("💾 Salvar Configurações", type="primary"):
                    empresa.update({
                        "nome": emp_nome, "cnpj": emp_cnpj, "endereco": emp_end, "regime": emp_regime,
                        "aliquota_patronal": aliq_p, "aliquota_rat": aliq_r, "aliquota_terceiros": aliq_t
                    })
                    salvar_dados_empresa(empresa)
                    log_acao("CONFIG_EMPRESA", f"Regime: {emp_regime}")
                    st.success("Configurações da empresa salvas com sucesso!")
                    st.rerun()

    # ====================== LOGS ======================
    elif menu == "📋 Logs do Sistema":
        if not tem_permissao("admin"):
            st.error("Acesso reservado ao administrador.")
        else:
            st.header("📋 Logs do Sistema")
            try:
                log_files = sorted([f for f in os.listdir(LOG_DIR) if f.endswith(".log")], reverse=True)
                if not log_files:
                    st.info("Nenhum log encontrado.")
                else:
                    arq_sel = st.selectbox("Arquivo de Log", log_files)
                    caminho_log = os.path.join(LOG_DIR, arq_sel)
                    with open(caminho_log, "r", encoding="utf-8") as lf:
                        linhas = lf.readlines()
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        filtro_nivel = st.selectbox("Nível", ["TODOS","INFO","WARNING","ERROR"])
                    with col_f2:
                        filtro_texto = st.text_input("Buscar texto")
                    with col_f3:
                        qtd = st.number_input("Últimas N linhas", min_value=10, max_value=5000, value=200)
                    linhas_filt = linhas
                    if filtro_nivel != "TODOS":
                        linhas_filt = [l for l in linhas_filt if filtro_nivel in l]
                    if filtro_texto:
                        linhas_filt = [l for l in linhas_filt if filtro_texto.lower() in l.lower()]
                    linhas_filt = linhas_filt[-int(qtd):]
                    st.metric("Linhas exibidas", len(linhas_filt))
                    st.code("".join(linhas_filt), language="text")
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        with open(caminho_log, "rb") as lf:
                            st.download_button("⬇️ Baixar Log", lf, file_name=arq_sel,
                                               mime="text/plain", key="dl_log")
            except Exception as e:
                logger.error(f"Erro Logs: {e}")
                st.error(f"Erro: {e}")

    # ====================== CONFIGURAÇÃO DE TABELAS ======================
    elif menu == "⚙️ Configuração de Tabelas":
        if not tem_permissao("admin"):
            st.error("Acesso reservado ao administrador.")
            st.stop()
        
        st.header("⚙️ Configuração de Tabelas (INSS / IRRF)")
        st.info("⚠️ Alterações nestas tabelas afetam todos os cálculos de folha de pagamento, férias e rescisão.")
        
        try:
            tabelas = carregar_tabelas()
            
            # --- INSS ---
            st.subheader("📊 Tabela de INSS")
            dados_inss = tabelas.get("inss", {})
            faixas_inss = pd.DataFrame(dados_inss.get("faixas", []))
            
            st.write("Faixas de Contribuição:")
            new_faixas_inss = st.data_editor(faixas_inss, num_rows="fixed", use_container_width=True, key="editor_inss")
            
            teto_inss = st.number_input("Teto da Base de Cálculo INSS (R$)", 
                                       value=float(dados_inss.get("teto_base", 8157.41)), 
                                       step=100.0, format="%.2f")
            
            st.divider()
            
            # --- IRRF ---
            st.subheader("📊 Tabela de IRRF")
            dados_irrf = tabelas.get("irrf", {})
            faixas_irrf = pd.DataFrame(dados_irrf.get("faixas", []))
            
            st.write("Faixas de IRRF:")
            new_faixas_irrf = st.data_editor(faixas_irrf, num_rows="fixed", use_container_width=True, key="editor_irrf")
            
            ded_dep = st.number_input("Dedução por Dependente (R$)", 
                                     value=float(dados_irrf.get("deducao_dependente", 189.59)), 
                                     step=1.0, format="%.2f")
            
            if st.button("💾 Salvar Todas as Alterações", type="primary"):
                novas_tabelas = {
                    "inss": {
                        "faixas": new_faixas_inss.to_dict('records'),
                        "teto_base": teto_inss
                    },
                    "irrf": {
                        "deducao_dependente": ded_dep,
                        "faixas": new_faixas_irrf.to_dict('records')
                    }
                }
                if salvar_tabelas(novas_tabelas):
                    st.success("✅ Tabelas atualizadas com sucesso!")
                    st.cache_data.clear() # Limpar cache para forçar recarregamento
                    log_acao("CONFIG_TABELAS", "Tabelas de INSS/IRRF atualizadas")
                    st.rerun()
                else:
                    st.error("❌ Erro ao salvar as tabelas.")
                    
        except Exception as e:
            logger.error(f"Erro Configuração Tabelas: {e}")
            st.error(f"Erro: {e}")

    # ====================== BACKUP E RESTAURAÇÃO ======================
    elif menu == "💾 Backup e Restauração":
        if not tem_permissao("admin"):
            st.error("Acesso reservado ao administrador.")
            st.stop()
        
        st.header("💾 Backup e Restauração")
        
        try:
            tab_backup, tab_restaurar = st.tabs(["📦 Criar Backup", "♻️ Restaurar"])
            
            with tab_backup:
                st.subheader("Criar Backup Manual")
                st.info("O backup copia todos os dados do sistema (funcionários, usuários, folhas, documentos, eSocial) em um arquivo ZIP compactado.")
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    motivo_bkp = st.selectbox("Motivo do Backup", [
                        "manual", "pre_atualizacao", "seguranca", "rotina_mensal"
                    ])
                with col_b2:
                    st.metric("Backups Existentes", len(listar_backups()))
                
                if st.button("📦 Criar Backup Agora", type="primary", key="btn_criar_backup"):
                    with st.spinner("Criando backup..."):
                        resultado = criar_backup(motivo=motivo_bkp)
                    if resultado:
                        tamanho = os.path.getsize(resultado)
                        st.success(f"✅ Backup criado com sucesso!")
                        st.write(f"**Arquivo:** `{os.path.basename(resultado)}`")
                        st.write(f"**Tamanho:** {tamanho / 1024:.1f} KB")
                        log_acao("BACKUP_CRIADO", f"Motivo: {motivo_bkp}")
                        with open(resultado, "rb") as bf:
                            st.download_button("⬇️ Baixar Backup", bf,
                                             file_name=os.path.basename(resultado),
                                             mime="application/zip", key="dl_backup_novo")
                    else:
                        st.error("❌ Erro ao criar backup.")
                
                st.divider()
                st.subheader("📋 Backups Disponíveis")
                backups = listar_backups()
                if not backups:
                    st.info("Nenhum backup encontrado.")
                else:
                    for i, bkp in enumerate(backups):
                        col1, col2, col3 = st.columns([4, 2, 1])
                        col1.write(f"📁 `{bkp['nome']}`")
                        col2.write(f"{bkp['tamanho_legivel']} | {bkp['data']}")
                        if os.path.exists(bkp['caminho']):
                            with open(bkp['caminho'], "rb") as bf:
                                col3.download_button("⬇️", bf,
                                                   file_name=bkp['nome'],
                                                   mime="application/zip",
                                                   key=f"dl_bkp_{i}")
            
            with tab_restaurar:
                st.subheader("♻️ Restaurar Backup")
                st.warning("⚠️ **ATENÇÃO:** A restauração substituirá TODOS os dados atuais. Um backup do estado atual será criado automaticamente antes da restauração.")
                
                backups = listar_backups()
                if not backups:
                    st.info("Nenhum backup disponível para restauração.")
                else:
                    bkp_sel = st.selectbox("Selecione o backup para restaurar",
                                          [f"{b['nome']} ({b['tamanho_legivel']} — {b['data']})" for b in backups])
                    idx = next(i for i, b in enumerate(backups) 
                             if bkp_sel.startswith(b['nome']))
                    
                    st.info(f"**Backup selecionado:** {backups[idx]['nome']}")
                    
                    confirmar = st.checkbox("✅ Confirmo que desejo restaurar este backup e substituir todos os dados atuais.")
                    
                    if st.button("♻️ Restaurar", type="primary", disabled=not confirmar, key="btn_restaurar"):
                        with st.spinner("Restaurando..."):
                            sucesso = restaurar_backup(backups[idx]['caminho'])
                        if sucesso:
                            log_acao("BACKUP_RESTAURADO", f"Arquivo: {backups[idx]['nome']}")
                            st.success("✅ Backup restaurado com sucesso! Recarregue a página.")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao restaurar backup.")
        
        except Exception as e:
            logger.error(f"Erro Backup: {e}")
            st.error(f"Erro: {e}")
