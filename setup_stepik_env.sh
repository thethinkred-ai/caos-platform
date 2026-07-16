#!/bin/bash
cat >> /opt/caos/.env << 'ENVEOF'
STEPIK_CLIENT_ID=JxFfjbsrZfC8V3JE73b9ml1ohTDJ9mmFrlHr6EZg
STEPIK_CLIENT_SECRET=68HjzdSZVfIOjbfVZe15BuVGZCQLQkZqqj9KxtmYfgFyCfq2xRSlykwRzjqxDipWKo7svcVu0vAWghEac2TxPUcJG4IG1wUFt1EG2L2bZGFpaA75fbyNrt1XQGcOQqBR
STEPIK_REDIRECT_URI=https://api-caos.thinkred.ru/api/v1/auth/stepik/callback
FRONTEND_URL=https://caos.thinkred.ru
ENVEOF
echo "--- .env updated ---"
cat /opt/caos/.env
echo "--- restarting caos-api ---"
systemctl restart caos-api.service
sleep 2
systemctl is-active caos-api.service
echo "--- testing stepik endpoint ---"
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/v1/auth/stepik
