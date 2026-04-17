#!/bin/bash
# setup_vps.sh — Configuración inicial del VPS (correr UNA sola vez como root)
# Uso: sudo bash setup_vps.sh
set -euo pipefail

echo "[setup] Actualizando sistema..."
apt-get update && apt-get upgrade -y

echo "[setup] Instalando dependencias del sistema..."
apt-get install -y \
    python3.11 python3.11-venv python3.11-dev \
    nginx certbot python3-certbot-nginx \
    git curl wget build-essential \
    libpq-dev libffi-dev libssl-dev \
    nodejs npm

echo "[setup] Creando usuario deploy..."
id -u deploy &>/dev/null || useradd -m -s /bin/bash deploy

echo "[setup] Creando estructura de directorios..."
mkdir -p /var/www/iarchitecter/{backend,frontend}
mkdir -p /var/log/iarchitecter
chown -R deploy:deploy /var/www/iarchitecter /var/log/iarchitecter

echo "[setup] Configurando sudoers para deploy..."
cat > /etc/sudoers.d/deploy-iarchitecter << 'EOF'
deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart iarchitecter-api, \
                            /bin/systemctl restart iarchitecter-frontend, \
                            /bin/systemctl status iarchitecter-api, \
                            /bin/systemctl status iarchitecter-frontend, \
                            /usr/sbin/nginx -t, \
                            /bin/systemctl reload nginx
EOF

echo "[setup] Instalando servicio systemd..."
cp /var/www/iarchitecter/backend/deploy/systemd/iarchitecter-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable iarchitecter-api

echo "[setup] Configurando nginx..."
cp /var/www/iarchitecter/backend/deploy/nginx/iarchitecter.conf /etc/nginx/sites-available/iarchitecter
ln -sf /etc/nginx/sites-available/iarchitecter /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "[setup] ✓ Setup inicial completo."
echo "  Próximos pasos:"
echo "  1. Crear venv: python3.11 -m venv /var/www/iarchitecter/venv"
echo "  2. Instalar deps: /var/www/iarchitecter/venv/bin/pip install -r /var/www/iarchitecter/backend/requirements.txt"
echo "  3. Copiar .env: cp .env.example /var/www/iarchitecter/backend/.env && nano /var/www/iarchitecter/backend/.env"
echo "  4. SSL: sudo certbot --nginx -d tudominio.com"
echo "  5. Iniciar: sudo systemctl start iarchitecter-api"
