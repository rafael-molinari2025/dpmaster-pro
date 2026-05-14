#!/bin/bash
# ============================================================
# DPMaster Pro — Script de Deploy / Atualização
# Uso: bash deploy/deploy.sh
# ============================================================

set -euo pipefail

echo "╔══════════════════════════════════════════════════════════╗"
echo "║        DPMaster Pro — Deploy em Produção                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "📁 Diretório: $PROJECT_DIR"
echo "🕐 Início: $(date '+%d/%m/%Y %H:%M:%S')"
echo ""

# ── 1. Verificar Docker ──────────────────────────────────
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado. Execute setup-server.sh primeiro."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose não encontrado."
    exit 1
fi

echo "✅ Docker: $(docker --version | cut -d' ' -f3)"
echo ""

# ── 2. Backup Pré-Deploy ─────────────────────────────────
echo "💾 [1/4] Criando backup pré-deploy..."
BACKUP_DIR="$PROJECT_DIR/deploy_backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup dos volumes Docker (se existirem dados)
if docker volume inspect dpmaster_data &> /dev/null 2>&1; then
    docker run --rm \
        -v dpmaster_data:/data \
        -v "$BACKUP_DIR":/backup \
        alpine tar czf "/backup/pre_deploy_${TIMESTAMP}.tar.gz" -C /data . 2>/dev/null || true
    echo "   ✅ Backup dos dados salvo em: deploy_backups/pre_deploy_${TIMESTAMP}.tar.gz"
else
    echo "   ℹ️  Primeiro deploy — sem dados para backup."
fi

# Manter apenas os últimos 5 backups de deploy
ls -t "$BACKUP_DIR"/pre_deploy_*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true

# ── 3. Build da Imagem ───────────────────────────────────
echo ""
echo "🔨 [2/4] Construindo imagem Docker..."
docker compose build --no-cache dpmaster
echo "   ✅ Build concluído!"

# ── 4. Deploy ────────────────────────────────────────────
echo ""
echo "🚀 [3/4] Iniciando containers..."

# Parar containers existentes (se houver)
docker compose down --remove-orphans 2>/dev/null || true

# Subir todos os serviços
docker compose up -d

echo "   ✅ Containers iniciados!"

# ── 5. Verificação de Saúde ──────────────────────────────
echo ""
echo "🩺 [4/4] Verificando saúde do sistema..."

# Aguardar o app ficar pronto
MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if docker compose exec -T dpmaster curl -sf http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        echo "   ✅ Aplicação respondendo!"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo "   ⏳ Aguardando... (${WAITED}s)"
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "   ⚠️  App não respondeu em ${MAX_WAIT}s. Verificando logs..."
    docker compose logs --tail=30 dpmaster
    echo ""
    echo "   Use 'docker compose logs -f dpmaster' para ver logs em tempo real."
fi

# ── Resumo Final ─────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              ✅ DEPLOY CONCLUÍDO!                        ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "║  🌐 URL: https://dpmasterpro.com.br                     ║"
echo "║                                                          ║"
echo "║  Comandos úteis:                                         ║"
echo "║  • Ver logs:     docker compose logs -f dpmaster         ║"
echo "║  • Reiniciar:    docker compose restart dpmaster         ║"
echo "║  • Parar tudo:   docker compose down                     ║"
echo "║  • Status:       docker compose ps                       ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "🕐 Finalizado: $(date '+%d/%m/%Y %H:%M:%S')"
