#!/bin/bash

# YouTube Data Collector - Batch Processing Script
# Usage: ./run.sh <urls.jsonl> [output_directory]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}YouTube Data Collector - Batch Mode${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: Missing required argument${NC}"
    echo "Usage: $0 <urls.jsonl> [output_directory]"
    exit 1
fi

URLS_FILE="$1"
OUTPUT_DIR="${2:-output}"

# Diagnose Python
echo -e "${YELLOW}Using Python from: $(which python)${NC}"

# Run batch collector using 'python' instead of 'python3'
cd "$SCRIPT_DIR"
python batch_collector.py "$URLS_FILE" "$OUTPUT_DIR" --max-comments 1000 --sort-by 0

EXIT_CODE=$?
exit $EXIT_CODE
