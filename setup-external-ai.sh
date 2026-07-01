#!/bin/bash
# UGit External AI Config Installer
# 自动配置外部 AI 设置

CONFIG_FILE="/Users/bln/bln-dev/ugit-comment/external-ai-config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误: 配置文件不存在: $CONFIG_FILE"
    exit 1
fi

# 检查 API Key
API_KEY=$(cat "$CONFIG_FILE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('apiKey',''))")
if [ "$API_KEY" = "YOUR-API-KEY-HERE" ] || [ -z "$API_KEY" ]; then
    echo "错误: 请先编辑 $CONFIG_FILE 填入你的 API Key"
    exit 1
fi

echo "正在配置 UGit External AI..."
echo ""
echo "配置内容:"
cat "$CONFIG_FILE"
echo ""

# 使用 osascript 直接与 Electron 应用交互
# 由于无法直接操作 App 的 localStorage，我们创建辅助文件

cat > /tmp/ugit-external-ai-inject.js << 'EOF'
// This script will be injected via the app
const config = CONFIG_PLACEHOLDER;
localStorage.setItem('externalAIConfig', JSON.stringify(config));
console.log('✓ External AI configured:', config.provider, config.model);
EOF

# 替换配置
CONFIG_JSON=$(cat "$CONFIG_FILE")
sed "s|CONFIG_PLACEHOLDER|${CONFIG_JSON}|g" /tmp/ugit-external-ai-inject.js > /tmp/ugit-external-ai-ready.js

echo ""
echo "配置已准备好。"
echo ""
echo "启动 UGit 后:"
echo "1. 打开开发者工具 (Cmd+Option+I)"
echo "2. 在 Console 中输入: (注意先输入 allow pasting)"
echo ""
echo "localStorage.getItem('externalAIConfig')"
echo ""
echo "确认配置已加载后，刷新页面 (Cmd+R)"
