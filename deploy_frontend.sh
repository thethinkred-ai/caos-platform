#!/bin/bash
lftp << 'EOF'
set ftp:ssl-allow no
set ftp:ssl-force false
open -u "windsurf","&,_oxW4Z\9o8Y<Ri" 87.232.64.20
mirror -R --delete /opt/caos/frontend/dist/ /www/caos.thinkred.ru/
quit
EOF
echo "lftp exit code: $?"
