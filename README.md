# UGit AI Commit Message 扩展指南

## 功能说明

为 UGit 添加 AI 生成 Git Commit Message 功能，支持 DeepSeek、OpenAI、Claude 等 API。

## 准备工作

### 1. 获取 API Key

**DeepSeek（推荐，便宜）**
- 注册 https://platform.deepseek.com
- 获取 API Key

**OpenAI**
- 注册 https://platform.openai.com
- 获取 API Key

**Claude**
- 注册 https://console.anthropic.com
- 获取 API Key

### 2. 备份原版 UGit

```bash
# 如果之前有修改过，先删除
rm -rf ~/Applications/UGit.app

# 复制原版 UGit
cp -pR /Applications/UGit.app ~/Applications/UGit.app
```

## 应用补丁

### 方式一：运行补丁脚本

```bash
cd /Users/bln/bln-dev/ugit-comment
python3 patch_ugit_ai.py
```

### 方式二：手动应用（推荐）

如果脚本有问题，手动执行以下步骤：

```bash
# 1. 复制 UGit
rm -rf ~/Applications/UGit.app
cp -pR /Applications/UGit.app ~/Applications/UGit.app

# 2. 应用补丁
python3 << 'PYEOF'
with open('/Users/bln/Applications/UGit.app/Contents/Resources/app/renderer.js', 'r') as f:
    content = f.read()

# Patch 1: 添加外部 AI 调用
old1 = r'''// AI获取commit message
async function postAICommitMessage(repository, diffContent, language) {
    try {
        const { api, url: repoURL } = (0,src_utils/* getAPIByRepository */.e6o)(repository);
        if (!(api?.isGitWoa() || api?.isGitCent())) {
            return null;
        }'''

new1 = r'''// AI获取commit message (增强版)
async function postAICommitMessage(repository, diffContent, language) {
    try {
        const { api, url: repoURL } = (0,src_utils/* getAPIByRepository */.e6o)(repository);
        const useExternalAI = (0,local_storage_cache/* getExternalAIConfig */.getExternalAIConfig)();
        if (useExternalAI && useExternalAI.enabled) {
            return await postExternalAICommitMessage(diffContent, language, useExternalAI);
        }
        if (!(api?.isGitWoa() || api?.isGitCent())) {
            return null;
        }'''

content = content.replace(old1, new1)

# Patch 2: 添加 postExternalAICommitMessage 函数
old2 = '''        log.error(`postAICommitMessage:  ${e}`);
        return null;
    }
}'''
new2 = '''        log.error(`postAICommitMessage:  ${e}`);
        return null;
    }
}
// 外部 AI API 支持
async function postExternalAICommitMessage(diffContent, language, config) {
    try {
        const { endpoint, apiKey, model, provider } = config;
        if (!endpoint || !apiKey) return null;
        const isOpenAI = provider === 'openai' || endpoint.includes('openai') || endpoint.includes('deepseek');
        let body, headers, url;
        if (isOpenAI) {
            url = `${endpoint}/chat/completions`;
            headers = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${apiKey}` };
            body = { model: model || 'gpt-4', messages: [
                { role: 'system', content: 'You are a helpful assistant that generates git commit messages. Follow conventional commit format: type(scope): description' },
                { role: 'user', content: `Generate a git commit message for this diff:\n\n${diffContent}\n\nLanguage: ${language === 'en' ? 'English' : 'Chinese'}\n\nOnly return the commit message.` }
            ], stream: false };
        } else {
            url = `${endpoint}/v1/messages`;
            headers = { 'Content-Type': 'application/json', 'x-api-key': apiKey, 'anthropic-version': '2023-06-01' };
            body = { model: model || 'claude-3-sonnet-20240229', max_tokens: 200, messages: [
                { role: 'user', content: `Generate a git commit message:\n\n${diffContent}\n\nLanguage: ${language === 'en' ? 'English' : 'Chinese'}` }
            ]};
        }
        const response = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body) });
        if (!response.ok) return null;
        const data = await response.json();
        const msg = isOpenAI ? data.choices?.[0]?.message?.content : data.content?.[0]?.text;
        return { msg: msg?.trim() || '', id: `ext-${Date.now()}` };
    } catch (e) { log.error(`External AI: ${e}`); return null; }
}'''
content = content.replace(old2, new2)

# Patch 3: UI 对所有仓库显示 AI 按钮
old3 = "if (this.isGitWoa || this.isGitTencent) {"
new3 = "if (true) { // AI for all repos"
content = content.replace(old3, new3)

# Patch 4: 添加配置和函数
old4 = '''function setAICommitMessageSuggestTAPD(value) {
    (0,_utils_local_storage_local_storage__WEBPACK_IMPORTED_MODULE_0__/* .setString */ .gQ)(`${LocalStorageCacheKey.ForceTapd}`, JSON.stringify(value));
}
/***/ }),'''
new4 = '''function setAICommitMessageSuggestTAPD(value) {
    (0,_utils_local_storage_local_storage__WEBPACK_IMPORTED_MODULE_0__/* .setString */ .gQ)(`${LocalStorageCacheKey.ForceTapd}`, JSON.stringify(value));
}
const DEEPSEEK_CONFIG = {"enabled":true,"provider":"openai","endpoint":"https://api.deepseek.com/v1","apiKey":"YOUR-API-KEY","model":"deepseek-chat"};
function getExternalAIConfig() {
    try {
        const stored = (0,_utils_local_storage_local_storage__WEBPACK_IMPORTED_MODULE_0__/* .getString */ .AA)('externalAIConfig');
        if (stored) { const p = JSON.parse(stored); if (p.enabled && p.apiKey) return p; }
    } catch (e) {}
    return DEEPSEEK_CONFIG;
}
function setExternalAIConfig(config) {
    try { (0,_utils_local_storage_local_storage__WEBPACK_IMPORTED_MODULE_0__/* .setString */ .gQ)('externalAIConfig', JSON.stringify(config)); } catch (e) {}
}
/***/ }),'''
content = content.replace(old4, new4)

# Patch 5: 导出函数
old5 = '''/* harmony export */   UV: () => (/* binding */ getAICommitMessageSuggestTAPD),'''
new5 = '''/* harmony export */   UV: () => (/* binding */ getAICommitMessageSuggestTAPD),
    /* harmony export */   getExternalAIConfig: () => getExternalAIConfig,'''
content = content.replace(old5, new5)

with open('/Users/bln/Applications/UGit.app/Contents/Resources/app/renderer.js', 'w') as f:
    f.write(content)
print('Done!')
PYEOF
```

## 配置 API Key

### 方法 1：直接在代码中修改

```bash
# 编辑配置文件
nano /Users/bln/bln-dev/ugit-comment/external-ai-config.json
```

内容：
```json
{
  "enabled": true,
  "provider": "openai",
  "endpoint": "https://api.deepseek.com/v1",
  "apiKey": "你的API密钥",
  "model": "deepseek-chat"
}
```

然后重新运行补丁脚本。

### 方法 2：在 UGit Console 中配置

1. 打开 ~/Applications/UGit.app
2. 打开开发者工具 (Cmd+Option+I)
3. 在 Console 输入 `allow pasting` 回车
4. 粘贴（替换 YOUR-API-KEY）：

```javascript
localStorage.setItem('externalAIConfig', JSON.stringify({
  enabled: true,
  provider: 'openai',
  endpoint: 'https://api.deepseek.com/v1',
  apiKey: 'YOUR-API-KEY',
  model: 'deepseek-chat'
}))
```

5. 刷新页面 (Cmd+R)

## 使用方法

1. 打开 ~/Applications/UGit.app
2. 选择任意 Git 仓库（GitHub、GitLab、本地都可以）
3. 在文件列表勾选要提交的文件
4. 点击提交框旁边的 **AI 按钮**
5. 等待 AI 生成 commit message
6. 检查生成的内容，点击提交

## 故障排除

### 问题：按钮不显示

1. 确保 `showCommitOptions` 已开启（UGit 设置中）
2. 检查 Console 是否有报错
3. 刷新页面重试

### 问题：点击按钮没反应

1. 打开 Console 检查网络请求
2. 确认 API Key 正确
3. 检查 API 额度是否充足

### 问题：生成的 message 是英文

DeepSeek 会根据内容自动判断语言，也可以手动修改 prompt 中的语言设置。

## 支持的 AI 提供商

| 提供商 | endpoint | model 示例 |
|--------|----------|-----------|
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat |
| OpenAI | https://api.openai.com/v1 | gpt-4, gpt-3.5-turbo |
| Claude | https://api.anthropic.com/v1 | claude-3-sonnet-20240229 |

## 文件结构

```
ugit-comment/
├── external-ai-config.json   # AI 配置
├── ai-commit.py              # 命令行版本
├── patch_ugit_ai.py          # 补丁脚本
└── README.md                 # 本文档
```

## 注意事项

1. API Key 存储在 localStorage 中，换电脑需要重新配置
2. 建议定期检查 API 使用量
3. 生成的 commit message 仅供参考，建议人工检查后再提交
