#!/bin/bash
# deploy.sh — Deploy rutinario al VPS (correr como usuario deploy)
# Uso: bash /var/www/iarchitecter/deploy/scripts/deploy.sh
set -euo pipefail

APP_DIR="/var/www/iarchitecter"
BACKEND_DIR="$APP_DIR/backend"
VENV_DIR="$APP_DIR/venv"
LOG_FILE="/var/log/iarchitecter/deploy_$(date +%Y%m%d_%H%M%S).log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

log "=== Deploy iniciado ==="

log "Actualizando código desde GitHub..."
cd "$BACKEND_DIR"
git pull origin main 2>&1 | tee -a "$LOG_FILE"

log "Instalando dependencias Python..."
"$VENV_DIR/bin/pip" install --quiet -r requirements.txt 2>&1 | tee -a "$LOG_FILE"

log "Verificando que la app importa correctamente..."
"$VENV_DIR/bin/python" -c "from app.main import app; print('  Import OK')" 2>&1 | tee -a "$LOG_FILE"

log "Reiniciando servicio FastAPI..."
sudo systemctl restart iarchitecter-api
sleep 3
sudo systemctl status iarchitecter-api --no-pager | tee -a "$LOG_FILE"

log "Health check..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/v1/health || echo "000")
if [ "$HTTP_STATUS" = "200" ]; then
    log "✓ Health check OK (HTTP $HTTP_STATUS)"
else
    log "✗ Health check FALLÓ (HTTP $HTTP_STATUS)"
    log "  Ver logs: journalctl -u iarchitecter-api -n 50"
    exit 1
fi

log "=== Deploy completado exitosamente ==="
