#!/bin/bash

# Gemini Summary Generator Script
# Usage: ./run_gemini.sh <combined_data.jsonl> [output.jsonl]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}Error: GEMINI_API_KEY environment variable is not set.${NC}"
    echo "Please set it: export GEMINI_API_KEY='your_api_key'"
    exit 1
fi

if [ $# -lt 1 ]; then
    echo -e "${RED}Error: Missing required argument${NC}"
    echo "Usage: $0 <combined_data.jsonl> [output.jsonl]"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="${2:-gemini_results_for_training.jsonl}"

# Diagnose Python
echo -e "${YELLOW}Using Python from: $(which python)${NC}"

echo -e "${GREEN}Starting Gemini Summary Generation...${NC}"
python "$SCRIPT_DIR/summarize_with_gemini.py" "$INPUT_FILE" --output "$OUTPUT_FILE"

EXIT_CODE=$?
exit $EXIT_CODE
