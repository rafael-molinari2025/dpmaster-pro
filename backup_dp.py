"""
DPMaster Pro — Sistema de Backup
Backup automático e manual do diretório data_dp/ com rotação.
"""

import os
import shutil
import zipfile
from datetime import datetime
import logging

logger = logging.getLogger("DPMasterPro.Backup")

# Configurações
DATA_DIR = "data_dp"
BACKUP_DIR = "data_dp_backups"
MAX_BACKUPS = 10  # Manter apenas os últimos N backups


def criar_backup(motivo: str = "manual") -> str:
    """
    Cria um backup completo do diretório data_dp/.
    
    Args:
        motivo: Razão do backup (manual, pre_rescisao, pre_exclusao, agendado)
    
    Returns:
        Caminho do arquivo de backup criado, ou string vazia em caso de erro.
    """
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_backup = f"backup_{motivo}_{timestamp}.zip"
        caminho_backup = os.path.join(BACKUP_DIR, nome_backup)

        if not os.path.exists(DATA_DIR):
            logger.warning("Diretório data_dp/ não encontrado para backup.")
            return ""

        with zipfile.ZipFile(caminho_backup, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(DATA_DIR):
                for file in files:
                    filepath = os.path.join(root, file)
                    arcname = os.path.relpath(filepath, os.path.dirname(DATA_DIR))
                    zf.write(filepath, arcname)

        # Registrar informações do backup
        tamanho = os.path.getsize(caminho_backup)
        logger.info(f"Backup criado: {nome_backup} ({tamanho} bytes) — Motivo: {motivo}")

        # Rotação: remover backups antigos
        rotacionar_backups()

        return caminho_backup

    except Exception as e:
        logger.error(f"Erro ao criar backup: {e}")
        return ""


def rotacionar_backups():
    """Remove backups antigos mantendo apenas os últimos MAX_BACKUPS."""
    try:
        if not os.path.exists(BACKUP_DIR):
            return

        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith('.zip')],
            key=lambda f: os.path.getmtime(os.path.join(BACKUP_DIR, f)),
            reverse=True
        )

        if len(backups) > MAX_BACKUPS:
            for backup_antigo in backups[MAX_BACKUPS:]:
                caminho = os.path.join(BACKUP_DIR, backup_antigo)
                os.remove(caminho)
                logger.info(f"Backup antigo removido: {backup_antigo}")

    except Exception as e:
        logger.error(f"Erro na rotação de backups: {e}")


def restaurar_backup(caminho_zip: str, destino: str = None) -> bool:
    """
    Restaura um backup a partir de um arquivo .zip.
    
    Args:
        caminho_zip: Caminho do arquivo de backup .zip
        destino: Diretório de destino (padrão: diretório atual)
    
    Returns:
        True se restaurado com sucesso.
    """
    try:
        if not os.path.exists(caminho_zip):
            logger.error(f"Arquivo de backup não encontrado: {caminho_zip}")
            return False

        destino = destino or "."

        # Criar backup do estado atual antes de restaurar
        criar_backup(motivo="pre_restauracao")

        with zipfile.ZipFile(caminho_zip, 'r') as zf:
            zf.extractall(destino)

        logger.info(f"Backup restaurado com sucesso: {caminho_zip}")
        return True

    except Exception as e:
        logger.error(f"Erro ao restaurar backup: {e}")
        return False


def listar_backups() -> list:
    """Lista todos os backups disponíveis com metadados."""
    try:
        if not os.path.exists(BACKUP_DIR):
            return []

        backups = []
        for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
            if f.endswith('.zip'):
                caminho = os.path.join(BACKUP_DIR, f)
                tamanho = os.path.getsize(caminho)
                data_mod = datetime.fromtimestamp(os.path.getmtime(caminho))
                backups.append({
                    "nome": f,
                    "caminho": caminho,
                    "tamanho_bytes": tamanho,
                    "tamanho_legivel": _fmt_tamanho(tamanho),
                    "data": data_mod.strftime("%d/%m/%Y %H:%M:%S"),
                    "data_iso": data_mod.isoformat(),
                })

        return backups

    except Exception as e:
        logger.error(f"Erro ao listar backups: {e}")
        return []


def _fmt_tamanho(bytes_val: int) -> str:
    """Formata tamanho em bytes para exibição legível."""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    else:
        return f"{bytes_val / (1024 * 1024):.1f} MB"


if __name__ == "__main__":
    # Execução direta para backup via linha de comando ou script agendado
    print("DPMaster Pro — Backup Manual")
    resultado = criar_backup(motivo="manual_cli")
    if resultado:
        print(f"Backup criado com sucesso: {resultado}")
    else:
        print("Erro ao criar backup!")
