#!/usr/bin/env bash
# Put the annotation API behind HTTPS at api.genegenie.tech via nginx + Let's Encrypt.
# nginx terminates TLS on 443 and reverse-proxies to the local service on :8000
# (so port 8000 itself can stay closed to the public).
#
# PREREQUISITES (your actions, before running this):
#   1. DNS A record: api.genegenie.tech -> 3.6.214.176
#   2. EC2 security group: open inbound TCP 80 and 443 to 0.0.0.0/0
set -euo pipefail

DOMAIN="${API_DOMAIN:-api.genegenie.tech}"
EMAIL="${CERTBOT_EMAIL:-admin@genegenie.tech}"

echo "==> installing nginx + certbot"
sudo apt-get update -y
sudo apt-get install -y nginx certbot python3-certbot-nginx

echo "==> writing nginx reverse-proxy config for $DOMAIN"
sudo tee /etc/nginx/sites-available/genegenie-api >/dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Allow large VCF uploads (the whole point of going direct, not via Vercel).
    client_max_body_size 2g;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
        proxy_request_buffering off;   # stream uploads through, don't buffer whole file
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/genegenie-api /etc/nginx/sites-enabled/genegenie-api
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

echo "==> obtaining Let's Encrypt certificate (needs DNS + port 80 reachable)"
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect

sudo systemctl reload nginx
echo "==> done. Test: curl https://$DOMAIN/health"
