#!/bin/bash
# Tianshu - offline model validation script

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INIT]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[INIT]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[INIT]${NC} $1"
}

log_error() {
    echo -e "${RED}[INIT]${NC} $1"
}

require_path() {
    local path="$1"
    local description="$2"

    if [ ! -e "$path" ]; then
        log_error "Missing required model asset: $description"
        log_error "Expected path: $path"
        return 1
    fi

    log_success "Found: $description"
    return 0
}

optional_path() {
    local path="$1"
    local description="$2"

    if [ ! -e "$path" ]; then
        log_warning "Optional model asset missing: $description ($path)"
        return 0
    fi

    log_success "Found optional: $description"
}

main() {
    log_info "Validating offline model layout..."

    local failed=0

    require_path "/app/models/mineru.json" "MinerU config" || failed=1
    require_path "/app/models/PDF-Extract-Kit-1.0/models" "MinerU pipeline models" || failed=1
    require_path "/app/models/MinerU2.5-2509-1.2B" "MinerU VLM model" || failed=1
    require_path "/root/.paddlex/official_models/PaddleOCR-VL-1.5-0.9B" "PaddleOCR-VL 1.5 model" || failed=1
    require_path "/root/.paddlex/official_models/PP-DocLayoutV3" "PaddleOCR-VL layout model" || failed=1
    require_path "/app/models/SenseVoiceSmall" "SenseVoiceSmall audio model" || failed=1
    require_path "/app/models/speech_fsmn_vad_zh-cn-16k-common-pytorch" "FSMN VAD audio model" || failed=1

    optional_path "/root/.paddlex/official_models/PP-LCNet_x1_0_doc_ori" "Paddle document orientation classifier"
    optional_path "/root/.paddlex/official_models/UVDoc" "Paddle document unwarping model"
    optional_path "/root/.paddlex/fonts/simfang.ttf" "PaddleX visualization font"
    optional_path "/app/models/Paraformer" "Paraformer speaker diarization model"
    optional_path "/app/models/punc_ct-transformer_zh-cn-common-vocab272727-pytorch" "CT punctuation model"
    optional_path "/app/models/speech_campplus_sv_zh-cn_16k-common" "CAM++ speaker model"
    optional_path "/app/models/YOLO11/best.pt" "YOLO watermark model"
    optional_path "/app/models/big-lama.pt" "LaMa inpainting model"
    optional_path "/root/.config/Ultralytics/Arial.ttf" "Ultralytics Arial.ttf"
    optional_path "/root/.config/Ultralytics/settings.json" "Ultralytics settings"

    if [ "$failed" -ne 0 ]; then
        log_error "Offline model validation failed. Please rebuild or re-extract models-offline.tar.gz."
        exit 1
    fi

    log_success "Offline model validation passed"
}

main "$@"
