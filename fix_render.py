#!/usr/bin/env python3
import re, sys

path = '/Users/bln/Applications/UGit.app/Contents/Resources/app/renderer.js'
with open(path, 'r') as f: content = f.read()

if 'function getExternalAIConfig()' in content:
    print('Already fixed.')
    sys.exit(0)

new_fn = '''// 外部 AI 配置
function getExternalAIConfig() {
    try {
        const config = localStorage.getItem('externalAIConfig');
        return config ? JSON.parse(config) : null;
    }
    catch (e) { return null; }
}
function setExternalAIConfig(config) {
    try { localStorage.setItem('externalAIConfig', JSON.stringify(config)); }
    catch (e) { log.error(`setExternalAIConfig: ${e}`); }
}
'''
idx = content.find('function setAICommitMessageSuggestTAPD(value) {')
end = content.find('}', idx + 50)
insert = end + 1
while insert < len(content) and content[insert] == '\n': insert += 1
content = content[:insert] + new_fn + content[insert:]
open(path, 'w').write(content)
print('Fixed! Restart UGit.')
