#!/bin/bash
# check_status.sh — Verificación rápida del estado del servidor
echo "=== Estado de servicios ==="
sudo systemctl status iarchitecter-api --no-pager -l

echo ""
echo "=== Últimos logs del API ==="
journalctl -u iarchitecter-api -n 20 --no-pager

echo ""
echo "=== Health check ==="
curl -s http://127.0.0.1:8000/api/v1/health | python3 -m json.tool 2>/dev/null || echo "API no responde"

echo ""
echo "=== Disco y memoria ==="
df -h /var/www/iarchitecter
free -h
