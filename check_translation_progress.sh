#!/bin/bash
# 檢查翻譯進度

echo "=== 翻譯進度監控 ==="
echo ""

# 檢查進程狀態
if ps aux | grep -v grep | grep translate_herbs_to_english_resume.py > /dev/null; then
    echo "✓ 翻譯程序正在運行"
    ps aux | grep -v grep | grep translate_herbs_to_english_resume.py | awk '{print "  PID: " $2 ", CPU: " $3 "%, MEM: " $4 "%"}'
else
    echo "✗ 翻譯程序未運行"
fi

echo ""

# 顯示最新進度
echo "=== 最新翻譯記錄 (最後20行) ==="
if [ -f translation_output.log ]; then
    tail -20 translation_output.log
else
    echo "日誌檔案不存在"
fi

echo ""

# 檢查進度檔案
if [ -f translation_progress.json ]; then
    echo "=== 進度檔案內容 ==="
    cat translation_progress.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'已完成: {len(data[\"completed\"])} 筆'); print(f'最後索引: {data[\"last_index\"]}')"
else
    echo "進度檔案不存在（可能尚未開始或已完成）"
fi

echo ""

# 檢查輸出檔案
if ls 對照表_含英文_*.xlsx 1> /dev/null 2>&1; then
    echo "=== 輸出檔案 ==="
    ls -lh 對照表_含英文_*.xlsx
else
    echo "輸出檔案尚未生成"
fi
