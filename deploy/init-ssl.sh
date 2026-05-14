#!/bin/bash
# ============================================================
# DPMaster Pro — Inicialização do SSL (Let's Encrypt)
# Execute APÓS configurar o DNS e copiar os arquivos.
# Uso: sudo bash deploy/init-ssl.sh
# ============================================================

set -euo pipefail

DOMAIN="dpmasterpro.com.br"
EMAIL="admin@dpmasterpro.com.br"   # Altere para seu email real
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_DIR"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     DPMaster Pro — Configuração SSL (Let's Encrypt)     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Domínio: $DOMAIN"
echo "📧 Email:   $EMAIL"
echo ""

# ── 1. Verificar DNS ─────────────────────────────────────
echo "🔍 [1/4] Verificando DNS..."
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
DNS_IP=$(dig +short "$DOMAIN" 2>/dev/null || echo "")

if [ -z "$DNS_IP" ]; then
    echo "   ⚠️  DNS ainda não propagou para '$DOMAIN'."
    echo "   Verifique se o registro A está apontando para: $SERVER_IP"
    echo ""
    read -p "   Continuar mesmo assim? (s/n): " CONTINUAR
    if [ "$CONTINUAR" != "s" ]; then
        echo "   Abortado. Configure o DNS e tente novamente."
        exit 1
    fi
elif [ "$DNS_IP" != "$SERVER_IP" ]; then
    echo "   ⚠️  DNS aponta para $DNS_IP, mas este servidor é $SERVER_IP"
    read -p "   Continuar mesmo assim? (s/n): " CONTINUAR
    if [ "$CONTINUAR" != "s" ]; then
        exit 1
    fi
else
    echo "   ✅ DNS OK: $DOMAIN → $SERVER_IP"
fi

# ── 2. Criar configuração Nginx temporária (HTTP only) ───
echo ""
echo "📝 [2/4] Configuração temporária do Nginx (sem SSL)..."

# Salvar o nginx.conf original
cp nginx/nginx.conf nginx/nginx.conf.ssl.bak

# Criar config temporária que só serve HTTP (para o challenge do certbot)
cat > nginx/nginx.conf << 'NGINX_TEMP'
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 256;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    server {
        listen 80;
        server_name dpmasterpro.com.br www.dpmasterpro.com.br;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 200 'DPMaster Pro — Aguardando configuracao SSL...';
            add_header Content-Type text/plain;
        }
    }
}
NGINX_TEMP

echo "   ✅ Config temporária criada"

# ── 3. Subir Nginx temporário ────────────────────────────
echo ""
echo "🚀 [3/4] Iniciando Nginx para validação..."

# Parar containers existentes
docker compose down 2>/dev/null || true

# Subir apenas o Nginx (sem depender do dpmaster)
docker compose up -d nginx 2>/dev/null || \
    docker run -d --name dpmaster-nginx-temp \
        -p 80:80 \
        -v "$PROJECT_DIR/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" \
        -v dpmaster_certbot_www:/var/www/certbot \
        nginx:alpine

sleep 3

# ── 4. Obter Certificado SSL ─────────────────────────────
echo ""
echo "🔐 [4/4] Solicitando certificado SSL..."

docker run --rm \
    -v dpmaster_certbot_www:/var/www/certbot \
    -v dpmaster_certbot_conf:/etc/letsencrypt \
    certbot/certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "$DOMAIN" \
        -d "www.$DOMAIN"

# ── 5. Restaurar Nginx completo e subir tudo ─────────────
echo ""
echo "🔄 Restaurando configuração SSL completa..."
cp nginx/nginx.conf.ssl.bak nginx/nginx.conf
rm -f nginx/nginx.conf.ssl.bak

# Parar Nginx temporário
docker compose down 2>/dev/null || true
docker stop dpmaster-nginx-temp 2>/dev/null || true
docker rm dpmaster-nginx-temp 2>/dev/null || true

# Deploy completo
echo "🚀 Iniciando stack completo com SSL..."
bash deploy/deploy.sh

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              🔒 SSL CONFIGURADO!                         ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "║  ✅ https://dpmasterpro.com.br                           ║"
echo "║                                                          ║"
echo "║  O certificado será renovado automaticamente.            ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
