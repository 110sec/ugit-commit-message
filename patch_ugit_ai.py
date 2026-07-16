#!/usr/bin/env python3
"""
UGit AI Commit Message Patch Script
读取 external-ai-config.json，将 AI 配置注入 renderer.js 的 getExternalAIConfig 函数中
支持 OpenAI / Claude / DeepSeek 等兼容 API 的服务
"""

import json
import os
import re
import shutil
import sys
from datetime import datetime

# ========== 配置 ==========
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "external-ai-config.json")
RENDERER_PATH = "/Applications/UGit.app/Contents/Resources/app/renderer.js"
BACKUP_DIR = os.path.expanduser("~/Library/Application Support/UGit/backups")

# ========== 读取配置 ==========
def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"[错误] 配置文件不存在: {CONFIG_FILE}")
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    for k in ["endpoint", "apiKey"]:
        if not config.get(k):
            print(f"[错误] 配置缺少必填字段: {k}")
            sys.exit(1)
    return config

# ========== 生成函数体 ==========
def generate_function(config):
    return f'''function getExternalAIConfig() {{
    return {{
        enabled: {str(config.get("enabled", True)).lower()},
        provider: "{config.get("provider", "openai")}",
        endpoint: "{config["endpoint"].rstrip("/")}",
        apiKey: "{config["apiKey"]}",
        model: "{config.get("model", "gpt-4")}",
    }};
}}'''

# ========== 备份 ==========
def backup(path):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dest = os.path.join(BACKUP_DIR,
        f"renderer.js.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(path, dest)
    print(f"[备份] {dest}")
    return dest

# ========== 替换函数体（简单可靠的方式）==========
def replace_function(js_content, func_body):
    """用简单字符串匹配找到并替换 getExternalAIConfig 函数体"""
    
    # 1. 尝试直接替换整个旧函数
    # 旧函数格式: function getExternalAIConfig() {\n    return {...};\n}
    # 匹配 "function getExternalAIConfig() {" 开头，到 "}\n}" 结尾
    pattern = r'(function getExternalAIConfig\(\)\s*\{\n    return \{[\s\S]*?\n    \};\n\})'
    match = re.search(pattern, js_content)
    if match:
        new_content = js_content[:match.start()] + func_body + "\n" + js_content[match.end():]
        print("[补丁] 方式1: 整块替换 getExternalAIConfig")
        return new_content

    # 2. 尝试另一种常见格式（无缩进）
    pattern2 = r'(function getExternalAIConfig\(\)\{[\s\S]*?\n\})'
    match2 = re.search(pattern2, js_content)
    if match2:
        new_content = js_content[:match2.start()] + func_body + "\n" + js_content[match2.end():]
        print("[补丁] 方式2: 整块替换 getExternalAIConfig（无缩进格式）")
        return new_content

    # 3. 找函数起始行，替换到下一个独立的 }
    start_marker = 'function getExternalAIConfig()'
    idx = js_content.find(start_marker)
    if idx == -1:
        print("[错误] 未找到 getExternalAIConfig 函数")
        sys.exit(1)
    
    # 从函数开始往后找，定位到函数结束的 }
    # 策略：找 "};" 后紧跟 "\n}" 的模式
    body_start = js_content.find('{', idx)
    search_from = body_start
    brace_count = 0
    end_pos = -1
    
    for i in range(search_from, len(js_content)):
        c = js_content[i]
        if c == '{':
            brace_count += 1
        elif c == '}':
            brace_count -= 1
            if brace_count == 0:
                # 函数结束的 }
                # 检查后面是否是 \n\n 或 \n}function 等
                rest = js_content[i+1:]
                # 可能是 }; 格式或 };function 格式
                if rest.startswith('};\n'):
                    end_pos = i + 3  # 指向 \n
                    break
                elif rest.startswith('}\n'):
                    end_pos = i + 1  # 指向 \n
                    break
    
    if end_pos == -1:
        print("[错误] 无法定位 getExternalAIConfig 函数结束位置")
        sys.exit(1)
    
    new_content = js_content[:idx] + func_body + "\n" + js_content[end_pos+1:]
    print("[补丁] 方式3: 字符计数定位替换")
    return new_content

# ========== 确保 postExternalAICommitMessage 存在 ==========
def ensure_external_function(js_content):
    """确保 postExternalAICommitMessage 函数存在"""
    if "async function postExternalAICommitMessage" in js_content:
        print("[检查] postExternalAICommitMessage 已存在")
        return js_content
    
    ext_func = '''
async function postExternalAICommitMessage(diffContent, language, config) {
    try {
        const { endpoint, apiKey, model, provider } = config;
        if (!endpoint || !apiKey) {
            log.error("External AI: missing endpoint or apiKey");
            return null;
        }
        const isOpenAI = provider === "openai" || endpoint.includes("openai");
        let body, headers, url;
        if (isOpenAI) {
            url = `${endpoint}/chat/completions`;
            headers = {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${apiKey}`,
            };
            body = {
                model: model || "gpt-4",
                messages: [
                    { role: "system", content: "You are a helpful assistant that generates git commit messages. Generate a concise, descriptive commit message in the language requested. Follow conventional commit format: type(scope): description" },
                    { role: "user", content: `Generate a git commit message for this diff:\\n\\n${diffContent}\\n\\nLanguage: ${language === "en" ? "English" : "Chinese"}\\n\\nOnly return the commit message, no explanation.` }
                ],
                stream: false,
            };
        } else {
            url = `${endpoint}/v1/messages`;
            headers = {
                "Content-Type": "application/json",
                "x-api-key": apiKey,
                "anthropic-version": "2023-06-01",
            };
            body = {
                model: model || "claude-3-sonnet-20240229",
                max_tokens: 200,
                messages: [
                    { role: "user", content: `Generate a git commit message for this diff:\\n\\n${diffContent}\\n\\nLanguage: ${language === "en" ? "English" : "Chinese"}\\n\\nOnly return the commit message, no explanation.` }
                ],
            };
        }
        const response = await fetch(url, { method: "POST", headers, body: JSON.stringify(body) });
        if (!response.ok) {
            log.error(`External AI: API request failed ${response.status}`);
            return null;
        }
        const data = await response.json();
        let msg = isOpenAI
            ? (data.choices?.[0]?.message?.content || "")
            : (data.content?.[0]?.text || "");
        msg = msg.trim().replace(/^["']|["']$/g, "");
        return { msg, id: `ext-${Date.now()}` };
    } catch (e) {
        log.error(`External AI: ${e}`);
        return null;
    }
}

'''
    # 插在 getExternalAIConfig 之前
    idx = js_content.find('function getExternalAIConfig()')
    if idx == -1:
        print("[错误] 未找到 getExternalAIConfig 函数（无法确定插入位置）")
        sys.exit(1)
    
    new_content = js_content[:idx] + ext_func + "\n" + js_content[idx:]
    print("[补丁] postExternalAICommitMessage 已插入到 getExternalAIConfig 之前")
    return new_content

# ========== 主流程 ==========
def main():
    print("=" * 60)
    print(" UGit AI Commit Message Patch")
    print("=" * 60)

    config = load_config()
    print(f"\n[配置] endpoint : {config['endpoint']}")
    print(f"[配置] model   : {config.get('model', 'gpt-4')}")
    print(f"[配置] provider: {config.get('provider', 'openai')}")
    print(f"[配置] enabled : {config.get('enabled', True)}")

    func_body = generate_function(config)

    # 备份 & 读取
    backup(RENDERER_PATH)
    with open(RENDERER_PATH, "r", encoding="utf-8") as f:
        js_content = f.read()
    original_len = len(js_content)

    # 依次打补丁
    js_content = ensure_external_function(js_content)
    js_content = replace_function(js_content, func_body)

    # 验证
    if "getExternalAIConfig()" not in js_content:
        print("[错误] 补丁后 getExternalAIConfig() 未找到")
        sys.exit(1)
    
    # 验证新配置是否写入
    check_str = f'endpoint: "{config["endpoint"].rstrip("/")}"'
    if check_str not in js_content:
        print(f"[警告] 验证失败: 找不到 '{check_str}'")
    
    # 写入
    with open(RENDERER_PATH, "w", encoding="utf-8") as f:
        f.write(js_content)
    
    delta = len(js_content) - original_len
    print(f"\n[完成] renderer.js 已更新 ({delta:+d} 字节)")
    print(f"[提示] 请重启 UGit.app 使补丁生效")

if __name__ == "__main__":
    main()
