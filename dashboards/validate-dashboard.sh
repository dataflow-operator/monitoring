#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MON_DASH="$ROOT_DIR/monitoring/dashboards/grafana-dashboard.json"
HELM_DASH="$ROOT_DIR/helm-charts/charts/dataflow-operator/dashboards/grafana-dashboard.json"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

command -v jq >/dev/null 2>&1 || fail "jq is required"

echo "== Grafana dashboard validation =="

echo "- JSON parse (monitoring)"
jq -e . >/dev/null "$MON_DASH"

echo "- JSON parse (helm)"
jq -e . >/dev/null "$HELM_DASH"

echo "- Files are identical"
diff -q "$MON_DASH" "$HELM_DASH" >/dev/null || fail "dashboard JSON differs between monitoring/ and helm-charts/"

echo "- Unique panel ids"
jq -r '.panels[]? | select(.id != null) | .id' "$MON_DASH" \
  | sort -n \
  | uniq -d \
  | awk 'BEGIN{bad=0}{print "duplicate id:", $0; bad=1} END{exit bad}' \
  || fail "duplicate panel ids detected"

echo "- No invalid histogram avg() queries"
if rg -n 'avg\\(dataflow_.*_seconds\\{' "$MON_DASH" >/dev/null; then
  fail "found avg(dataflow_*_seconds{...}) which is invalid for histograms; use _sum/_count instead"
fi

echo "OK"

