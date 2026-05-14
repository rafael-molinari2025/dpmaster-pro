#!/bin/bash
# ============================================================
# DPMaster Pro — Setup Inicial do Servidor VPS
# Execute este script UMA VEZ ao configurar o servidor.
# Uso: sudo bash setup-server.sh
# ============================================================

set -euo pipefail

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     DPMaster Pro — Configuração do Servidor VPS         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Execute como root: sudo bash setup-server.sh"
    exit 1
fi

# ── 1. Atualizar Sistema ──────────────────────────────────
echo "📦 [1/6] Atualizando sistema..."
apt-get update -qq && apt-get upgrade -y -qq

# ── 2. Instalar Dependências Básicas ─────────────────────
echo "🔧 [2/6] Instalando dependências..."
apt-get install -y -qq \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    ufw \
    fail2ban \
    unzip \
    htop

# ── 3. Instalar Docker ───────────────────────────────────
echo "🐳 [3/6] Instalando Docker..."
if ! command -v docker &> /dev/null; then
    # Adicionar chave GPG oficial do Docker
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    # Adicionar repositório Docker
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Habilitar Docker no boot
    systemctl enable docker
    systemctl start docker
    echo "   ✅ Docker instalado: $(docker --version)"
else
    echo "   ✅ Docker já instalado: $(docker --version)"
fi

# ── 4. Configurar Firewall (UFW) ─────────────────────────
echo "🔒 [4/6] Configurando firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable
echo "   ✅ Firewall ativo (SSH + HTTP + HTTPS)"

# ── 5. Configurar Fail2Ban ───────────────────────────────
echo "🛡️  [5/6] Configurando Fail2Ban..."
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 7200
EOF

systemctl enable fail2ban
systemctl restart fail2ban
echo "   ✅ Fail2Ban configurado"

# ── 6. Criar Diretório do Projeto ────────────────────────
echo "📁 [6/6] Preparando diretório do projeto..."
PROJECT_DIR="/opt/dpmaster"
mkdir -p "$PROJECT_DIR"
echo "   ✅ Diretório criado: $PROJECT_DIR"

# ── Resumo ────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              ✅ SERVIDOR CONFIGURADO!                    ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "║  Próximos passos:                                        ║"
echo "║                                                          ║"
echo "║  1. Copie os arquivos do projeto para:                   ║"
echo "║     /opt/dpmaster/                                       ║"
echo "║                                                          ║"
echo "║  2. Configure o DNS no Registro.br:                      ║"
echo "║     Tipo A → IP deste servidor                           ║"
echo "║                                                          ║"
echo "║  3. Execute o script de SSL:                             ║"
echo "║     cd /opt/dpmaster && bash deploy/init-ssl.sh          ║"
echo "║                                                          ║"
echo "║  4. Inicie o sistema:                                    ║"
echo "║     cd /opt/dpmaster && bash deploy/deploy.sh            ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "IP deste servidor: $(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')"
