#!/bin/bash
# 大话算法 — 批量生成轨迹JSON
# 用法: bash scripts/run_batch_traces.sh
# 从 样例网站目录执行

set -e
cd "$(dirname "$0")"

SRC_DIR="$(cd ../.. && pwd)/随书源代码"
TRACE_DIR="../data/traces"
BACKUP_DIR="../data/traces_backup_$(date +%Y%m%d_%H%M%S)"
BACKUP_KEEP="${BACKUP_KEEP:-0}"

echo "=========================================="
echo "  大话算法 — 批量轨迹生成"
echo "=========================================="
echo ""

# 默认不保留可重新生成的轨迹备份，避免 data/ 目录持续膨胀。
# 确实需要备份时可显式设置 BACKUP_KEEP，例如:
#   BACKUP_KEEP=1 bash scripts/run_batch_traces.sh
if [ "$BACKUP_KEEP" -gt 0 ] && [ -d "$TRACE_DIR" ] && [ "$(ls -A "$TRACE_DIR" 2>/dev/null)" ]; then
    echo "📦 备份旧traces到 $BACKUP_DIR"
    cp -r "$TRACE_DIR" "$BACKUP_DIR"
fi

# 只保留显式要求的最近几份轨迹备份。
BACKUP_COUNT=$(find ../data -maxdepth 1 -type d -name 'traces_backup_*' | wc -l | tr -d ' ')
if [ "$BACKUP_COUNT" -gt "$BACKUP_KEEP" ]; then
    echo "🧹 清理旧轨迹备份，仅保留最近 $BACKUP_KEEP 份"
    find ../data -maxdepth 1 -type d -name 'traces_backup_*' | sort | head -n "$((BACKUP_COUNT - BACKUP_KEEP))" | while read -r old_backup; do
        rm -rf "$old_backup"
    done
fi

# 清空traces目录
rm -rf "$TRACE_DIR"
mkdir -p "$TRACE_DIR"

echo "🔧 开始插桩+编译+运行..."
echo ""

# 运行批量插桩
python3 auto_instrument.py --batch "$SRC_DIR" "$TRACE_DIR" 2>&1

echo ""
echo "📊 结果统计:"
TOTAL=$(ls "$TRACE_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')
echo "  成功生成: $TOTAL 个轨迹文件"

# 重新生成章节页面
echo ""
echo "📄 重新生成章节页面..."
python3 generate.py 2>&1

echo ""
echo "✅ 完成!"
