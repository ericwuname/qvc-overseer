# QVC 用户使用手册 — 保姆级教程

> 适用版本：V6.1 | 难度：零基础 | 预计阅读：5 分钟

---

## 目录

1. [我为什么要用 QVC](#1-我为什么要用-qvc)
2. [安装（1 分钟）](#2-安装)
3. [第一次使用（2 分钟）](#3-第一次使用)
4. [看懂报告](#4-看懂报告)
5. [让 AI 自动修 bug](#5-让-ai-自动修-bug)
6. [日常使用场景](#6-日常使用场景)
7. [进阶功能](#7-进阶功能)
8. [常见问题](#8-常见问题)

---

## 1. 我为什么要用 QVC

**如果你用 AI（Codex/Cursor/GPT）写代码，你需要 QVC。**

原因很简单：AI 写完代码后会自己查一遍，但它查不出自己的问题。就像你写的文章自己校对，永远有错别字。

QVC 是一个"局外人"——它不写代码，只查代码。它能发现 AI 自审查**绝对看不到**的三类问题：

1. **记忆残留**：AI 在生成过程中留下的逻辑断裂
2. **上下文遗忘**：AI 写文件 A 时还记得接口，写文件 B 时忘了
3. **自利采摘**：AI 找了一两个问题就停手了，没查全

---

## 2. 安装

### 第一步：打开终端

Windows：按 `Win + R`，输入 `cmd`，回车。

### 第二步：安装 QVC

```bash
pip install qvc-overseer
```

如果提示 `pip 不是内部命令`，先安装 Python：[python.org](https://python.org) 下载，安装时勾选"Add Python to PATH"。

### 第三步：验证安装

```bash
qvc --help
```

看到一大串帮助信息 = 安装成功。

---

## 3. 第一次使用

### 第一步：进入你的项目

```bash
cd 你的项目路径
```

例如：`cd D:\my-project`

### 第二步：初始化 QVC（就这一次）

```bash
qvc setup
```

它会自动创建两个东西：
- `.qvc/` 文件夹（QVC 的工作目录）
- `AGENTS.md` 文件（告诉你的 AI 助手怎么配合 QVC）

### 第三步：扫描

```bash
qvc scan .
```

你会看到进度条在跑，然后：

```
Done! 1.0s, 3 bugs
  Tasks: 3 -> .qvc/tasks/pending.md (say 'fix qvc tasks' to your AI)
```

**完成！你已经用 QVC 完成了第一次代码审查。**

---

## 4. 看懂报告

扫描完成后，项目里多了一个 `qvc-report.md` 文件。打开它：

### 第一部分：外部监工摘要

```
## 👁 外部监工摘要

| QVC 外部审查发现 | 5 条缺陷 |
| 预估AI 自审未发现率 | 67% |
```

这告诉你：AI 说自己"没问题"，但 QVC 找到了 5 个，AI 大概漏了 67%。

### 第二部分：高置信度问题

```
## 🔥 高置信度问题 — 建议立即处理

### Bug #1: [95%] 文件包含 UTF-8 BOM 字符
- 文件：backend/app/api/requirement_mining.py:1
- 问题：文件头部包含 BOM 字符，会导致 JSON 解析失败
- 盲区：AI 编码层自动剥离 BOM，自审查时看不到
```

**前 3 条就是真 bug。** 这是 QVC 的品质保证。

### 第三部分：AI 修复指令

报告最底部有一块：

```
## AI Fix Instructions

> 复制以下内容，粘贴到你的 AI 编程助手，回车即可。

### Task 1 [95%]: UTF-8 BOM in 15 files
- File: backend/app/api/requirement_mining.py:1
- Fix: Save as UTF-8 without BOM
```

**复制这一段 → 粘贴到 Codex/Cursor/GPT → 回车 → AI 自动修。**

---

## 5. 让 AI 自动修 bug

### 方式一：从报告里复制（适合偶尔用）

1. 打开 `qvc-report.md`
2. 翻到底部 "AI Fix Instructions"
3. 复制整段
4. 粘贴到你的 AI 助手
5. 回车

### 方式二：一句话触发（推荐，适合日常）

前提：你运行过 `qvc setup`（3.2 步骤）。

直接对你的 AI 助手说：

```
fix qvc tasks
```

AI 会自动：
1. 读取 `.qvc/tasks/pending.md`
2. 逐条修复
3. 告诉你修了什么

**你只需要说 3 个单词。** 这就是 QVC V6 的核心体验。

### 方式三：命令行直接输出

```bash
qvc scan . --fix-prompt
```

扫描完终端直接显示修复指令，复制粘贴即可。

---

## 6. 日常使用场景

### 场景 A：写完一段代码后检查

```bash
qvc scan . --diff
```

只扫描你刚改过的文件，很快。

### 场景 B：提交代码前检查

```bash
qvc check
```

如果发现致命 bug，阻止提交。

### 场景 C：想让 QVC 自动看着你的项目

```bash
qvc watch .
```

QVC 会监控文件变化，发现新 bug 自动写入任务池。你随时说 "fix qvc tasks" 就行。

按 `Ctrl + C` 停止。

### 场景 D：只想看最严重的问题

```bash
qvc scan . --min-severity fatal
```

只显示会导致系统崩溃的致命问题。

---

## 7. 进阶功能

### 7.1 启用 LLM 深度审查

QVC 默认用静态分析（快，但精度 80%）。加上 LLM 后精度到 95%+：

```bash
# 用 Ollama（免费，本地跑）
qvc scan . --llm --llm-provider local

# 用 OpenAI API（付费，更准）
qvc scan . --llm --llm-provider openai --llm-api-key sk-xxx

# 用自定义 API（DeepSeek / Qwen 等）
qvc scan . --llm --llm-provider custom --llm-base-url https://your-api.com
```

### 7.2 对比 AI 自审报告

如果你有 AI Agent 的自审报告（它说"没问题"的那个）：

```bash
qvc scan . --self-review-report agent-review.md
```

QVC 会精确告诉你：AI 说自己检查了 X 条，实际漏了 Y 条。

### 7.3 同步社区基因池

社区里其他用户发现的 bug 模式，你可以一键同步：

```bash
qvc update
```

你的 QVC 会越来越聪明。

### 7.4 贡献你的发现

你项目里发现的 bug 模式可以贡献回社区：

```bash
qvc contribute preview    # 看看有什么可以贡献
qvc contribute submit --all   # 全部提交
```

### 7.5 VS Code 用户

安装 QVC VS Code 扩展后：
- 右键文件夹 → QVC: Full Scan
- 状态栏显示最新 bug 数量
- 问题面板直接看结果

---

## 8. 常见问题

### Q：QVC 会修改我的代码吗？

**不会。永远不会。** QVC 只报告问题，不碰你的代码。

### Q：需要 API Key 吗？

不需要。核心功能完全离线，免费。

### Q：需要 GitHub 账号吗？

不需要。你永远不需要登录任何账号。

### Q：扫描一次要多久？

小项目（<100 文件）：1 秒以内。
大项目（1000+ 文件）：5-15 秒。

### Q：报告在哪里？

项目根目录下的 `qvc-report.md`。用任何文本编辑器都能打开。

### Q：QVC 和其他工具有什么区别？

| | QVC | ESLint/Pylint | SonarQube |
|---|---|---|---|
| 审查视角 | 外部监工 | 规则检查 | 企业 SAST |
| 发现 AI 盲区 | ✅ | ❌ | ❌ |
| 修改代码 | 永不 | 有时 | 不 |
| 安装复杂度 | pip install | npm/pip + config | 服务器部署 |
| 价格 | 免费开源 | 免费 | 付费 |

### Q：支持什么语言？

Python、JavaScript、TypeScript、React、Go（实验性）。

### Q：扫出来很多 bug 怎么办？

正常。QVC 会按置信度排序。**前 3 条 ≥90% 置信度的，基本是真 bug。** 先修前 3 条。

### Q：有 bug 但我觉得不是 bug？

那是误报。QVC V6.1 的误报率很低，但还存在。你可以忽略它——QVC 的任务池会自动标记已修复的问题。

### Q：怎么卸载？

```bash
pip uninstall qvc
```

删除项目里的 `.qvc/` 文件夹和 `AGENTS.md` 里的 QVC 部分即可。

---

> **就这些。你用 QVC 只需要记住一个命令：`qvc scan .` 和一句话：`fix qvc tasks`。**
