"""Cria um novo usuário administrador (admin global) pela linha de comando.

Útil para criar administradores adicionais ou recuperar o acesso quando
nenhum admin consegue entrar no sistema. Usa o mesmo formato de hash
(SHA-256 + salt) e a mesma criptografia Fernet de app_dp.py.

Uso (rodar na pasta do projeto, com o app parado ou não):
    venv\\Scripts\\python criar_admin.py
    venv\\Scripts\\python criar_admin.py --usuario maria --nome "Maria Souza"

Em produção (Docker):
    docker compose exec dpmaster python criar_admin.py

A senha é sempre pedida de forma oculta (não aparece na tela nem no histórico).
"""
import argparse
import getpass
import hashlib
import json
import os
import secrets
import sys

DATA_DIR = "data_dp"
USUARIOS_FILE = os.path.join(DATA_DIR, "usuarios.json")
KEY_FILE = os.path.join(DATA_DIR, ".master.key")

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


def _fernet():
    if not CRYPTO_AVAILABLE:
        return None
    if not os.path.exists(KEY_FILE):
        sys.exit(f"Erro: chave {KEY_FILE} não encontrada. Rode este script na pasta do "
                 "projeto, depois de o sistema ter sido iniciado ao menos uma vez.")
    with open(KEY_FILE, "rb") as kf:
        return Fernet(kf.read())


def carregar_usuarios(fernet):
    if not os.path.exists(USUARIOS_FILE):
        sys.exit(f"Erro: {USUARIOS_FILE} não encontrado. Inicie o sistema uma vez antes.")
    with open(USUARIOS_FILE, "rb") as f:
        conteudo = f.read()
    try:
        return json.loads(conteudo.decode("utf-8"))  # formato antigo, texto puro
    except (UnicodeDecodeError, json.JSONDecodeError):
        if fernet is None:
            sys.exit("Erro: arquivo criptografado, mas a biblioteca cryptography não está instalada.")
        return json.loads(fernet.decrypt(conteudo).decode("utf-8"))


def salvar_usuarios(usuarios, fernet):
    dados = json.dumps(usuarios, indent=4, ensure_ascii=False).encode("utf-8")
    if fernet is not None:
        dados = fernet.encrypt(dados)
    tmp = USUARIOS_FILE + ".tmp"
    with open(tmp, "wb") as f:
        f.write(dados)
    os.replace(tmp, USUARIOS_FILE)


def main():
    ap = argparse.ArgumentParser(description="Cria um novo usuário admin no DPMaster Pro.")
    ap.add_argument("--usuario", help="login do novo admin")
    ap.add_argument("--nome", help="nome completo do novo admin")
    args = ap.parse_args()

    fernet = _fernet()
    usuarios = carregar_usuarios(fernet)

    username = (args.usuario or input("Usuário (login): ")).strip()
    nome = (args.nome or input("Nome completo: ")).strip()
    if not username or not nome:
        sys.exit("Erro: usuário e nome são obrigatórios.")
    if any(u.get("username", "").lower() == username.lower() for u in usuarios):
        sys.exit(f"Erro: o usuário '{username}' já existe.")

    senha = getpass.getpass("Senha (mín. 8 caracteres, com letras e números): ")
    if len(senha) < 8 or not any(c.isalpha() for c in senha) or not any(c.isdigit() for c in senha):
        sys.exit("Erro: a senha precisa ter pelo menos 8 caracteres, com letras e números.")
    if getpass.getpass("Confirme a senha: ") != senha:
        sys.exit("Erro: as senhas não conferem.")

    try:
        from backup_dp import criar_backup
        criar_backup("antes_novo_admin")
    except Exception as e:  # backup é desejável, mas não deve impedir a criação
        print(f"Aviso: não foi possível criar backup ({e}).")

    salt = secrets.token_hex(16)
    novo = {
        "id": max((u.get("id", 0) for u in usuarios), default=0) + 1,
        "nome": nome,
        "username": username,
        "senha": hashlib.sha256(f"{salt}{senha}".encode("utf-8")).hexdigest(),
        "salt": salt,
        "perfil": "admin",
        # sem "empresa_id": admin global, acessa todas as empresas
    }
    usuarios.append(novo)
    salvar_usuarios(usuarios, fernet)
    print(f"Usuário admin '{username}' criado com sucesso (id {novo['id']}, admin global).")


if __name__ == "__main__":
    main()
