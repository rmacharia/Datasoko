#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

printf "\n== health ==\n"
curl -s "$BASE_URL/health"; echo

printf "\n== version ==\n"
curl -s "$BASE_URL/version"; echo

printf "\n== ingest weekly ==\n"
curl -s -X POST "$BASE_URL/ingest/weekly" \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "biz_sample_001",
    "week_start": "2026-02-23",
    "week_end": "2026-03-01",
    "excel_file_path": "/home/rgmacharia/samples/sample_sales_data.xlsx",
    "mpesa_file_path": "/home/rgmacharia/samples/sample_mpesa_data.csv",
    "business_currency": "KES",
    "ensure_table": true
  }'; echo

printf "\n== weekly metrics ==\n"
curl -s -X POST "$BASE_URL/metrics/weekly" \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "biz_sample_001",
    "week_start": "2026-02-23",
    "week_end": "2026-03-01",
    "slow_mover_days": 14,
    "top_n_products": 5
  }'; echo

printf "\n== whatsapp weekly ==\n"
curl -s "$BASE_URL/whatsapp/weekly?business_id=biz_sample_001&week_start=2026-02-23&week_end=2026-03-01&business_name=Sample%20Duka&sme_type=retail&currency=KES&slow_mover_days=14&top_n_products=5"; echo
