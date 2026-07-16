#!/bin/bash
lftp << 'EOF'
set ftp:ssl-allow no
set ftp:ssl-force false
open -u "windsurf","&,_oxW4Z\9o8Y<Ri" 87.232.64.20
cat /www/caos.thinkred.ru/index.html
quit
EOF
