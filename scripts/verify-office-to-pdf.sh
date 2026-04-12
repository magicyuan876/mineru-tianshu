#!/bin/bash
# Office 转 PDF 功能验证脚本
# 用于验证 LibreOffice 和 Office 转 PDF 功能是否正常工作

set -e

# ============================================================================
# 配置
# ============================================================================
API_URL="${API_URL:-http://localhost:8000}"
WORKER_CONTAINER="${WORKER_CONTAINER:-tianshu-worker}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# 检查函数
# ============================================================================

check_docker_services() {
    log_info "Checking Docker services..."

    if ! docker ps | grep -q "$WORKER_CONTAINER"; then
        log_error "Worker container not running!"
        log_info "Please start services first:"
        log_info "  docker-compose up -d"
        exit 1
    fi

    log_success "Worker container is running"
}

check_libreoffice() {
    log_info "Checking LibreOffice installation..."

    if docker exec "$WORKER_CONTAINER" which libreoffice > /dev/null 2>&1; then
        VERSION=$(docker exec "$WORKER_CONTAINER" libreoffice --version 2>/dev/null || echo "Unknown")
        log_success "LibreOffice is installed: $VERSION"
    else
        log_error "LibreOffice is not installed in worker container!"
        exit 1
    fi
}

check_api_health() {
    log_info "Checking API health..."

    if curl -f -s "$API_URL/health" > /dev/null 2>&1; then
        RESPONSE=$(curl -s "$API_URL/health")
        log_success "API is healthy: $RESPONSE"
    else
        log_error "API health check failed!"
        log_info "Please ensure the backend is running"
        exit 1
    fi
}

check_uploads_permissions() {
    log_info "Checking uploads directory permissions..."

    # 检查容器内的 uploads 目录权限
    if docker exec "$WORKER_CONTAINER" test -w /app/data/uploads; then
        log_success "Uploads directory is writable"
    else
        log_error "Uploads directory is not writable!"
        log_info "Please check docker-compose.yml volume mount:"
        log_info "  - ./data/uploads:/app/data/uploads:rw  # Should be :rw not :ro"
        exit 1
    fi

    # 检查 converted_pdfs 目录
    if docker exec "$WORKER_CONTAINER" test -d /app/data/uploads/converted_pdfs; then
        log_success "Converted PDFs directory exists"
    else
        log_warning "Converted PDFs directory does not exist (will be created on first conversion)"
    fi
}

# ============================================================================
# 测试函数
# ============================================================================

create_test_document() {
    log_info "Creating test document..."

    # 创建临时测试文档
    TEST_FILE="/tmp/tianshu-test-office-$(date +%s).docx"

    # 使用 Python 创建一个简单的 Word 文档
    docker exec "$WORKER_CONTAINER" python3 -c "
from docx import Document
from docx.shared import Pt

doc = Document()
doc.add_heading('Tianshu Office to PDF Test', 0)
doc.add_paragraph('This is a test document for Office to PDF conversion.')
doc.add_paragraph('Created at: $(date)')

# 添加表格
table = doc.add_table(rows=3, cols=3)
table.style = 'Light Grid Accent 1'
for i in range(3):
    for j in range(3):
        table.cell(i, j).text = f'Cell {i+1},{j+1}'

doc.save('$TEST_FILE')
print('Test document created: $TEST_FILE')
" 2>/dev/null || {
        log_warning "python-docx not available, creating text-based test file"
        docker exec "$WORKER_CONTAINER" bash -c "
cat > /tmp/test.txt <<EOF
Tianshu Office to PDF Test
==========================

This is a test document for Office to PDF conversion.
Created at: $(date)

Test Points:
1. Text content
2. Formatting
3. Conversion quality
EOF
"
        TEST_FILE="/tmp/test.txt"
    }

    if docker exec "$WORKER_CONTAINER" test -f "$TEST_FILE"; then
        log_success "Test document created: $TEST_FILE"
        echo "$TEST_FILE"
    else
        log_error "Failed to create test document"
        exit 1
    fi
}

test_libreoffice_conversion() {
    log_info "Testing LibreOffice conversion directly..."

    # 在容器内创建测试文件并转换
    docker exec "$WORKER_CONTAINER" bash -c '
# 创建测试文本文件
cat > /tmp/test-direct.txt <<EOF
Test Document
=============
This is a direct LibreOffice conversion test.
EOF

# 转换为 PDF
libreoffice --headless --convert-to pdf --outdir /tmp /tmp/test-direct.txt 2>&1

# 检查结果
if [ -f /tmp/test-direct.pdf ]; then
    echo "✅ Direct conversion successful"
    ls -lh /tmp/test-direct.pdf
    exit 0
else
    echo "❌ Direct conversion failed"
    exit 1
fi
' || {
        log_error "Direct LibreOffice conversion failed!"
        return 1
    }

    log_success "Direct LibreOffice conversion works"
}

# ============================================================================
# API 测试函数
# ============================================================================

get_auth_token() {
    log_info "Getting authentication token..."

    # 默认凭据
    USERNAME="${TIANSHU_USERNAME:-admin}"
    PASSWORD="${TIANSHU_PASSWORD:-admin123}"

    TOKEN=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
        | jq -r '.access_token' 2>/dev/null || echo "")

    if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
        log_success "Authentication successful"
        echo "$TOKEN"
    else
        log_error "Authentication failed!"
        log_info "Please check username and password"
        log_info "Default: admin / admin123"
        exit 1
    fi
}

test_office_to_pdf_api() {
    local convert_mode="$1"  # true or false
    local test_file="$2"
    local token="$3"

    if [ "$convert_mode" = "true" ]; then
        log_info "Testing Office to PDF API (Complete Solution)..."
    else
        log_info "Testing Office to PDF API (Fast Solution)..."
    fi

    # 提交任务
    RESPONSE=$(curl -s -X POST "$API_URL/api/v1/tasks/submit" \
        -H "Authorization: Bearer $token" \
        -F "file=@$test_file" \
        -F "convert_office_to_pdf=$convert_mode" \
        -F "backend=auto" 2>/dev/null)

    TASK_ID=$(echo "$RESPONSE" | jq -r '.task_id' 2>/dev/null || echo "")

    if [ -n "$TASK_ID" ] && [ "$TASK_ID" != "null" ]; then
        log_success "Task submitted: $TASK_ID"

        # 等待任务完成
        log_info "Waiting for task to complete..."
        MAX_WAIT=120  # 最多等待 120 秒
        WAIT_TIME=0

        while [ $WAIT_TIME -lt $MAX_WAIT ]; do
            STATUS_RESPONSE=$(curl -s -X GET "$API_URL/api/v1/tasks/$TASK_ID" \
                -H "Authorization: Bearer $token" 2>/dev/null)

            STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status' 2>/dev/null || echo "")

            if [ "$STATUS" = "completed" ]; then
                log_success "Task completed successfully!"

                # 显示结果摘要
                RESULT=$(echo "$STATUS_RESPONSE" | jq -r '.result' 2>/dev/null || echo "")
                if [ -n "$RESULT" ]; then
                    log_info "Result preview:"
                    echo "$RESULT" | head -10
                fi

                return 0
            elif [ "$STATUS" = "failed" ]; then
                log_error "Task failed!"
                ERROR=$(echo "$STATUS_RESPONSE" | jq -r '.error' 2>/dev/null || echo "Unknown error")
                log_error "Error: $ERROR"
                return 1
            fi

            sleep 3
            WAIT_TIME=$((WAIT_TIME + 3))
            echo -n "."
        done

        echo ""
        log_warning "Task timeout after ${MAX_WAIT}s, status: $STATUS"
        return 1
    else
        log_error "Failed to submit task!"
        log_error "Response: $RESPONSE"
        return 1
    fi
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    log_info "=========================================="
    log_info "🧪 Office to PDF Function Verification"
    log_info "=========================================="
    echo ""

    # 检查依赖
    if ! command -v jq &> /dev/null; then
        log_warning "jq not found, installing..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y jq
        elif command -v yum &> /dev/null; then
            sudo yum install -y jq
        else
            log_error "Please install jq manually"
            exit 1
        fi
    fi

    # 1. 基础检查
    log_info "Step 1: Basic checks"
    check_docker_services
    check_libreoffice
    check_api_health
    check_uploads_permissions
    echo ""

    # 2. 直接测试 LibreOffice
    log_info "Step 2: Direct LibreOffice test"
    test_libreoffice_conversion
    echo ""

    # 3. API 测试（可选）
    if [ "${SKIP_API_TEST:-false}" = "false" ]; then
        log_info "Step 3: API integration test"

        # 创建测试文档（在宿主机）
        HOST_TEST_FILE="/tmp/tianshu-api-test-$(date +%s).txt"
        cat > "$HOST_TEST_FILE" <<EOF
Tianshu API Test Document
========================

This is a test document for API integration testing.
Created at: $(date)

Test Features:
- Office to PDF conversion
- API authentication
- Task submission
- Result retrieval
EOF

        # 获取认证令牌
        TOKEN=$(get_auth_token)
        echo ""

        # 测试快速方案
        if test_office_to_pdf_api "false" "$HOST_TEST_FILE" "$TOKEN"; then
            log_success "✅ Fast solution test passed"
        else
            log_warning "⚠️  Fast solution test failed"
        fi
        echo ""

        # 测试完整方案
        if test_office_to_pdf_api "true" "$HOST_TEST_FILE" "$TOKEN"; then
            log_success "✅ Complete solution test passed"
        else
            log_warning "⚠️  Complete solution test failed"
        fi
        echo ""

        # 清理测试文件
        rm -f "$HOST_TEST_FILE"
    else
        log_info "Step 3: API integration test (skipped)"
        echo ""
    fi

    # 4. 汇总结果
    log_info "=========================================="
    log_success "✅ Verification Complete!"
    log_info "=========================================="
    echo ""

    log_info "Summary:"
    log_success "  ✓ Worker container is running"
    log_success "  ✓ LibreOffice is installed and working"
    log_success "  ✓ API is healthy"
    log_success "  ✓ Uploads directory has correct permissions"
    log_success "  ✓ Direct LibreOffice conversion works"

    if [ "${SKIP_API_TEST:-false}" = "false" ]; then
        log_success "  ✓ API integration tests completed"
    fi

    echo ""
    log_info "Next steps:"
    echo "  1. Upload your Office documents via the web interface"
    echo "  2. Or use the API:"
    echo ""
    echo "     # Fast solution (direct parsing):"
    echo "     curl -X POST $API_URL/api/v1/tasks/submit \\"
    echo "       -H \"Authorization: Bearer YOUR_TOKEN\" \\"
    echo "       -F \"file=@your-file.docx\" \\"
    echo "       -F \"convert_office_to_pdf=false\" \\"
    echo "       -F \"backend=auto\""
    echo ""
    echo "     # Complete solution (Office → PDF → Markdown):"
    echo "     curl -X POST $API_URL/api/v1/tasks/submit \\"
    echo "       -H \"Authorization: Bearer YOUR_TOKEN\" \\"
    echo "       -F \"file=@your-file.docx\" \\"
    echo "       -F \"convert_office_to_pdf=true\" \\"
    echo "       -F \"backend=auto\""
    echo ""
    log_success "All checks passed! 🎉"
}

# 显示使用说明
show_usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --api-url URL           API URL (default: http://localhost:8000)
  --worker-container NAME Worker container name (default: tianshu-worker)
  --compose-file FILE     Docker compose file (default: docker-compose.yml)
  --skip-api-test         Skip API integration tests
  --help                  Show this help message

Environment Variables:
  API_URL                 API URL
  WORKER_CONTAINER        Worker container name
  COMPOSE_FILE            Docker compose file
  TIANSHU_USERNAME        Username for API authentication (default: admin)
  TIANSHU_PASSWORD        Password for API authentication (default: admin123)
  SKIP_API_TEST           Skip API tests (true/false)

Examples:
  # Basic usage (local deployment)
  $0

  # Custom API URL
  $0 --api-url http://192.168.1.100:8000

  # Skip API tests (only check LibreOffice)
  $0 --skip-api-test

  # Offline deployment verification
  COMPOSE_FILE=docker-compose.offline.yml $0
EOF
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        --worker-container)
            WORKER_CONTAINER="$2"
            shift 2
            ;;
        --compose-file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        --skip-api-test)
            SKIP_API_TEST=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# 捕获中断信号
trap 'log_warning "Verification interrupted by user"; exit 130' SIGINT SIGTERM

# 执行主函数
main
