#!/bin/bash
set -e
source ~/slink_env/bin/activate

echo "=== 1. Init ==="
python3 -c "from slink.crypto import save_hosts; save_hosts({}, password='wsl123')"

echo "=== 2. Add hosts ==="
slink add bastion -h 192.168.1.1 -u admin --master-password wsl123
slink add web1 -h 10.0.0.5 -u root -a www -a prod --jump-host bastion --master-password wsl123
slink add db1 -h 10.0.0.6 -u root --master-password wsl123

echo "=== 3. names / list / show ==="
slink names
slink list --master-password wsl123
echo "--- show web1 ---"
slink show web1 --master-password wsl123

echo "=== 4. Alias resolution ==="
python3 -c "from slink.store import get_host; info=get_host('www', password='wsl123'); print('Resolved via alias:', info['hostname'])"

echo "=== 5. JSON export ==="
slink export -o /tmp/slink_test.json --master-password wsl123
cat /tmp/slink_test.json

echo "=== 6. Change password ==="
python3 -c "from slink.store import rotate_password; rotate_password('wsl123', 'newpass')"
slink list --master-password newpass

echo "=== 7. Multi-user isolation ==="
SLINK_USER=alice slink init
SLINK_USER=alice slink add alice-web -h 10.0.0.10 -u alice --master-password alice123
SLINK_USER=bob slink init
SLINK_USER=bob slink add bob-web -h 10.0.0.20 -u bob --master-password bob123

echo "--- Alice ---"
SLINK_USER=alice slink list --master-password alice123
echo "--- Bob ---"
SLINK_USER=bob slink list --master-password bob123
echo "--- Default (should be empty or own) ---"
slink list --master-password newpass

echo "=== 8. Import JSON ==="
slink rm web1 --yes --master-password newpass
slink import-json /tmp/slink_test.json --master-password newpass
slink list --master-password newpass

echo "=== 9. Jump host chain test ==="
python3 -c "
from slink.store import get_host
info = get_host('web1', password='newpass')
from slink.cli import _resolve_jump_chain
_resolve_jump_chain(info, 'newpass')
print('Resolved jump_host:', info.get('jump_host'))
"

echo ""
echo "=== ALL TESTS PASSED ==="
