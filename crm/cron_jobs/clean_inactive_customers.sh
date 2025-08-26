#!/bin/bash
# Deletes customers with no orders in the last year and logs the result.

set -euo pipefail

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MANAGE_PY="$PROJECT_ROOT/manage.py"
LOG_FILE="/tmp/customer_cleanup_log.txt"

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/venv/bin" ]; then
  source "$PROJECT_ROOT/venv/bin/activate"
fi

# Run Django shell code
PY_OUTPUT="$(
  cd "$PROJECT_ROOT"
  python3 "$MANAGE_PY" shell <<'PYCODE'
from datetime import timedelta
from django.utils import timezone
from django.db.models import Exists, OuterRef
from crm.models import Customer, Order

cutoff = timezone.now() - timedelta(days=365)
stale_customers = Customer.objects.filter(
    ~Exists(
        Order.objects.filter(customer=OuterRef('pk'), created_at__gte=cutoff)
    )
)
deleted_count, _ = stale_customers.delete()
print(deleted_count)
PYCODE
)"

# Log with timestamp
TS="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[$TS] Deleted customers: $PY_OUTPUT" >> "$LOG_FILE"
