#!/usr/bin/env python3
"""
UGit AI Commit Message Extension Patch
扩展 TGit AI 支持 GitHub/GitLab 等外部仓库

由于 SIP 保护，无法直接修改 /Applications 中的文件。
本脚本会:
1. 复制 UGit.app 到 ~/Applications/
2. 修改复制的版本
3. 创建启动脚本
"""

import re
import os
import json
import shutil
from datetime import datetime

SOURCE_APP = "/Applications/UGit.app"
LOCAL_APP = os.path.expanduser("~/Applications/UGit.app")
RENDERER_PATH = f"{LOCAL_APP}/Contents/Resources/app/renderer.js"
BACKUP_DIR = os.path.expanduser("~/Library/Application Support/UGit/backups")
os.makedirs(BACKUP_DIR, exist_ok=True)
BACKUP_SUFFIX = f".backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"

def backup_file(filepath):
    """创建备份到 Application Support 目录"""
    filename = os.path.basename(filepath)
    backup_path = os.path.join(BACKUP_DIR, f"{filename}{BACKUP_SUFFIX}")
    shutil.copy2(filepath, backup_path)
    print(f"✓ 备份已创建: {backup_path}")
    return backup_path

def create_launcher():
    """创建启动脚本"""
    launcher_path = os.path.expanduser("~/Applications/ugit-local.sh")
    script = '''#!/bin/bash
# 启动本地修改版 UGit
open ~/Applications/UGit.app
'''
    with open(launcher_path, 'w') as f:
        f.write(script)
    os.chmod(launcher_path, 0o755)
    print(f"✓ 启动脚本已创建: {launcher_path}")

def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✓ 文件已写入: {filepath}")

def patch_postAICommitMessage(content):
    """
    修改 postAICommitMessage 函数
    1. 移除腾讯内部 API 限制
    2. 添加外部 AI API 支持
    """
    # 原始函数 (line 183314-183353)
    old_function = r'''// AI获取commit message
async function postAICommitMessage\(repository, diffContent, language\) \{
    try \{
        const \{ api, url: repoURL \} = \(0,src_utils/\* getAPIByRepository \*/\.e6o\)\(repository\);
        if \(!\(api\?\.isGitWoa\(\) \|\| api\?\.isGitCent\(\)\)\) \{
            return null;
        \}
        let url = 'api/copilot/v3/ide/commit_messages/stream';
        const shouldForceTapd = \(0,local_storage_cache/\* getAICommitMessageSuggestTAPD \*/\.UV\)\(\) \|\| 'true';
        const data = await api\.requestEventStream\('POST', url, \{
            extra: \{
                diffContent,
                referer: 'ugit',
                projectFullPath: repoURL,
                language: language \|\| 'zh_CN',
                \.\.\.\(shouldForceTapd === 'true'
                    \? \{ forceTapd: true \}
                    : \{ ignoreTapd: true \}\),
            \},
        \}\);
        if \(!data\) \{
            return null;
        \}
        let content = [];
        let id = '';
        for \(const item of data\) \{
            if \(!id && item\.id\) \{
                id = item\.id;
            \}
            content = content\.concat\(item\.choices\?\.\.map\(\(i\) => i\.delta\?\.content \?\? ''\) \?\? \[\]\);
        \}
        return \{
            msg: content\.join\(''\),
            id,
        \};
    \}
    catch \(e\) \{
        log\.error\(`postAICommitMessage:  \$e`\);
        return null;
    \}
\}'''

    # 新的增强函数
    new_function = '''// AI获取commit message (增强版 - 支持所有仓库)
async function postAICommitMessage(repository, diffContent, language) {
    try {
        const { api, url: repoURL } = (0,src_utils/* getAPIByRepository */.e6o)(repository);
        // 检查是否使用外部 AI API (非腾讯内部)
        const useExternalAI = (0,local_storage_cache/* getExternalAIConfig */.getExternalAIConfig)();
        if (useExternalAI && useExternalAI.enabled) {
            return await postExternalAICommitMessage(diffContent, language, useExternalAI);
        }
        // 原有腾讯内部逻辑
        if (!(api?.isGitWoa() || api?.isGitCent())) {
            return null;
        }
        let url = 'api/copilot/v3/ide/commit_messages/stream';
        const shouldForceTapd = (0,local_storage_cache/* getAICommitMessageSuggestTAPD */.UV)() || 'true';
        const data = await api.requestEventStream('POST', url, {
            extra: {
                diffContent,
                referer: 'ugit',
                projectFullPath: repoURL,
                language: language || 'zh_CN',
                ...(shouldForceTapd === 'true'
                    ? { forceTapd: true }
                    : { ignoreTapd: true }),
            },
        });
        if (!data) {
            return null;
        }
        let content = [];
        let id = '';
        for (const item of data) {
            if (!id && item.id) {
                id = item.id;
            }
            content = content.concat(item.choices?.map((i) => i.delta?.content ?? '') ?? []);
        }
        return {
            msg: content.join(''),
            id,
        };
    }
    catch (e) {
        log.error(`postAICommitMessage:  ${e}`);
        return null;
    }
}
// 外部 AI API 支持 (OpenAI/Claude 兼容)
async function postExternalAICommitMessage(diffContent, language, config) {
    try {
        const { endpoint, apiKey, model, provider } = config;
        if (!endpoint || !apiKey) {
            log.error('External AI: missing endpoint or apiKey');
            return null;
        }
        const isOpenAI = provider === 'openai' || endpoint.includes('openai');
        let body, headers, url;
        if (isOpenAI) {
            url = `${endpoint}/chat/completions`;
            headers = {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`,
            };
            body = {
                model: model || 'gpt-4',
                messages: [
                    { role: 'system', content: 'You are a helpful assistant that generates git commit messages. Generate a concise, descriptive commit message in the language requested. Follow conventional commit format: type(scope): description' },
                    { role: 'user', content: `Generate a git commit message for this diff:\n\n${diffContent}\n\nLanguage: ${language === 'en' ? 'English' : 'Chinese'}\n\nOnly return the commit message, no explanation.` }
                ],
                stream: false,
            };
        } else {
            // Claude API
            url = `${endpoint}/v1/messages`;
            headers = {
                'Content-Type': 'application/json',
                'x-api-key': apiKey,
                'anthropic-version': '2023-06-01',
            };
            body = {
                model: model || 'claude-3-sonnet-20240229',
                max_tokens: 200,
                messages: [
                    { role: 'user', content: `Generate a git commit message for this diff:\n\n${diffContent}\n\nLanguage: ${language === 'en' ? 'English' : 'Chinese'}\n\nOnly return the commit message, no explanation.` }
                ],
            };
        }
        const response = await fetch(url, {
            method: 'POST',
            headers,
            body: JSON.stringify(body),
        });
        if (!response.ok) {
            log.error(`External AI: API request failed ${response.status}`);
            return null;
        }
        const data = await response.json();
        let msg = '';
        if (isOpenAI) {
            msg = data.choices?.[0]?.message?.content || '';
        } else {
            msg = data.content?.[0]?.text || '';
        }
        // 清理消息
        msg = msg.trim().replace(/^["']|["']$/g, '');
        return { msg, id: `ext-${Date.now()}` };
    }
    catch (e) {
        log.error(`External AI: ${e}`);
        return null;
    }
}'''

    # 查找并替换
    pattern = re.compile(r'// AI获取commit message\nasync function postAICommitMessage\(repository, diffContent, language\) \{.*?\n\}', re.DOTALL)
    match = pattern.search(content)
    if match:
        content = content[:match.start()] + new_function + content[match.end():]
        print("✓ postAICommitMessage 函数已修改")
    else:
        print("✗ 未找到 postAICommitMessage 函数")
    return content

def patch_UI_condition(content):
    """
    修改 UI 条件，让 AI 按钮对所有仓库显示
    line 223265: if (this.isGitWoa || this.isGitTencent)
    改为: if (true)
    """
    # 原始条件
    old_condition = "if (this.isGitWoa || this.isGitTencent) {"
    new_condition = "if (true) { // AI button for all repos"

    if old_condition in content:
        content = content.replace(old_condition, new_condition)
        print("✓ UI 条件已修改 - AI 按钮将对所有仓库显示")
    else:
        print("✗ 未找到 UI 条件语句")
    return content

def patch_renderOptionsRight(content):
    """
    修改 renderOptionsRight 确保 AI 组件正确渲染
    """
    old_render = '''renderOptionsRight = () => {
        if (this.isGitWoa || this.isGitTencent) {
            return (react.createElement("div", { className: "commit-message-options-right" },
                react.createElement(TgitAi, { loading: this.props.tgitAILoading !== null, disabled: this.props.waitingFiles.length === 0, onClick: this.onAIClick, onCancel: this.onAICancel })));
        }
        return null;
    };'''

    new_render = '''renderOptionsRight = () => {
        // AI button shown for all repositories (including GitHub/GitLab)
        return (react.createElement("div", { className: "commit-message-options-right" },
            react.createElement(TgitAi, { loading: this.props.tgitAILoading !== null, disabled: this.props.waitingFiles.length === 0, onClick: this.onAIClick, onCancel: this.onAICancel })));
    };'''

    if old_render in content:
        content = content.replace(old_render, new_render)
        print("✓ renderOptionsRight 已修改")
    else:
        print("✗ 未找到 renderOptionsRight")
    return content

def patch_local_storage(content):
    """
    添加外部 AI 配置的存储函数，并自动从配置文件加载
    """
    # 在 getAICommitMessageSuggestTAPD 函数附近添加新函数
    old_storage = '''function getAICommitMessageSuggestTAPD() {
    try {
        return localStorage.getItem('aiCommitMessageSuggestTAPD') || 'true';
    }
    catch (e) {
        return 'true';
    }
}
function setAICommitMessageSuggestTAPD(value) {
    try {
        localStorage.setItem('aiCommitMessageSuggestTAPD', value);
    }
    catch (e) {
        log.error(`setAICommitMessageSuggestTAPD: ${e}`);
    }
}'''

    new_storage = '''function getAICommitMessageSuggestTAPD() {
    try {
        return localStorage.getItem('aiCommitMessageSuggestTAPD') || 'true';
    }
    catch (e) {
        return 'true';
    }
}
function setAICommitMessageSuggestTAPD(value) {
    try {
        localStorage.setItem('aiCommitMessageSuggestTAPD', value);
    }
    catch (e) {
        log.error(`setAICommitMessageSuggestTAPD: ${e}`);
    }
}
// 外部 AI 配置 - 自动从配置文件加载
(function initExternalAIFromConfig() {
    try {
        const config = localStorage.getItem('externalAIConfig');
        if (!config) {
            // 尝试从配置文件加载
            const configPath = '/Users/bln/bln-dev/ugit-comment/external-ai-config.json';
            // 通过 fetch 读取本地配置文件
            fetch('file://' + configPath)
                .then(r => r.json())
                .then(cfg => {
                    if (cfg.enabled && cfg.apiKey && cfg.apiKey !== 'YOUR-API-KEY-HERE') {
                        localStorage.setItem('externalAIConfig', JSON.stringify(cfg));
                        console.log('✓ External AI config loaded from file');
                    }
                })
                .catch(() => {});
        }
    } catch (e) {}
})();
function getExternalAIConfig() {
    try {
        const config = localStorage.getItem('externalAIConfig');
        return config ? JSON.parse(config) : null;
    }
    catch (e) {
        return null;
    }
}
function setExternalAIConfig(config) {
    try {
        localStorage.setItem('externalAIConfig', JSON.stringify(config));
    }
    catch (e) {
        log.error(`setExternalAIConfig: ${e}`);
    }
}'''

    if 'getExternalAIConfig' not in content:
        content = content.replace(old_storage, new_storage)
        print("✓ 外部 AI 配置存储函数已添加（含自动加载）")
    else:
        print("○ 外部 AI 配置存储函数已存在")
    return content

def patch_export(content):
    """
    导出新函数
    """
    old_export = '''/* harmony export */   UV: () => (/* binding */ getAICommitMessageSuggestTAPD),'''
    new_export = '''/* harmony export */   UV: () => (/* binding */ getAICommitMessageSuggestTAPD),
    /* harmony export */   getExternalAIConfig: () => getExternalAIConfig,
    /* harmony export */   setExternalAIConfig: () => setExternalAIConfig,'''

    if 'getExternalAIConfig: () => getExternalAIConfig' not in content:
        content = content.replace(old_export, new_export)
        print("✓ 新函数已导出")
    else:
        print("○ 新函数已导出")
    return content

def copy_app():
    """复制 UGit 到本地目录"""
    if os.path.exists(LOCAL_APP):
        print(f"✓ 发现已复制的 UGit: {LOCAL_APP}")
        return True
    print(f"正在复制 UGit 到 {LOCAL_APP}...")
    try:
        shutil.copytree(SOURCE_APP, LOCAL_APP)
        print("✓ 复制完成")
        return True
    except Exception as e:
        print(f"✗ 复制失败: {e}")
        return False

def main():
    if not os.path.exists(SOURCE_APP):
        print(f"✗ 源文件不存在: {SOURCE_APP}")
        print("请确保 UGit 已安装在 /Applications")
        return

    print(f"源文件: {SOURCE_APP}")
    print(f"目标文件: {LOCAL_APP}")
    print("-" * 50)

    # 复制应用
    if not copy_app():
        return

    # 创建备份
    backup_file(RENDERER_PATH)

    # 读取文件
    content = read_file(RENDERER_PATH)

    # 应用补丁
    content = patch_postAICommitMessage(content)
    content = patch_UI_condition(content)
    content = patch_renderOptionsRight(content)
    content = patch_local_storage(content)
    content = patch_export(content)

    # 写入文件
    write_file(RENDERER_PATH, content)

    # 创建启动脚本
    create_launcher()

    print("-" * 50)
    print("补丁应用完成!")
    print(f"\n启动修改后的 UGit:")
    print(f"  open ~/Applications/UGit.app")
    print("\n使用方法:")
    print("1. 启动 ~/Applications/UGit.app")
    print("2. 打开浏览器开发者工具 (Cmd+Option+I)")
    print("3. 在 Console 中配置外部 AI:")
    print("   localStorage.setItem('externalAIConfig', JSON.stringify({")
    print("     enabled: true,")
    print("     provider: 'openai',  // 或 'claude'")
    print("     endpoint: 'https://api.openai.com/v1',")
    print("     apiKey: 'your-api-key',")
    print("     model: 'gpt-4'")
    print("   }));")
    print("4. 刷新页面，在提交框旁边会显示 AI 按钮")

if __name__ == "__main__":
    main()
