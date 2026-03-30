<div align="center">
  
  # 🛠️ Game4FreeRenew <br><sup>AI 增强版</sup>
  
  <!-- 徽章区域，建议添加 -->
  [![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg?style=flat-square&logo=python)](https://www.python.org/)
  [![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Enabled-success?style=flat-square&logo=github-actions)](https://github.com/features/actions)
  [![License](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](LICENSE)
  
</div>

> 🌙 **"写给那些不想半夜起来点续期的服主们。"**

## 📖 项目简介

用过 **Gaming4Free** 的小伙伴都知道，这家的机器配置确实香，但最**阴间**的就是那个"续期倒计时"——如果不去点一下，服务器就会自动关机 😱

这个项目就是为了**彻底解放双手**搞出来的。它利用 **GitHub Actions** 24 小时值守，配合 **Google Gemini AI** 自动识别那个人机验证图片（哪怕是最恶心的九宫格也能过）。续期成功后，它还会把现场截图发到你的 Telegram 上。

---

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 🧠 **AI 视觉破解** | 调用 gemini 的模型，像真人一样看图过验证，不再卡死在点消防栓和公交车上 |
| 🤖 **全自动值守** | 默认每小时检查一次，到了续期时间自动下手，真正的" set and forget " |
| 📱 **状态实时推送** | 成功/未到点/报错，全带图推送到你的 Telegram |
| ☁️ **云端运行** | 零成本运行，无需本地电脑，无需加速器 |

---

## 🚀 快速上手

### 1️⃣ 准备仓库

- 在 GitHub 新建一个仓库（**强烈建议设为 Private** 🔒）
- 上传以下文件：
- 上传以下文件：

```text
Game4FreeRenew/
├── renew.py
├── requirements.txt
└── .github/
    └── workflows/
        └── main.yml
```

### 2️⃣ 配置 Secrets（关键步骤）

进入 `Settings -> Secrets and variables -> Actions`，新建以下 Repository Secrets：

| 变量名 | 说明 | 示例 |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini 密钥 | `AIzaSyDeP54D...` |
| `GEMINI_MODEL` | 模型名称 | `gemini-2.5-flash` |
| `RENEW_URL` | 续期链接 | `https://game4free.net/myplay` |
| `MC_USERNAME` | MC ID | `dafengzi` |
| `TG_BOT_TOKEN` | Telegram Bot Token | `7560020170:AA...` |
| `TG_CHAT_ID` | Telegram ID | `...4463...` |

<details>
<summary>💡 如何获取这些值？（点击展开）</summary>

- **Gemini Key**: [Google AI Studio](https://aistudio.google.com/app/apikey) 免费申请
- **Telegram Bot**: 找 [@BotFather](https://t.me/botfather) 创建机器人
- **Chat ID**: 发给 [@userinfobot](https://t.me/userinfobot) 就能拿到你的 ID

</details>

### 3️⃣ 激活 Workflow

1. 点击仓库顶部 `Actions` 选项卡
2. 若看到警告，点击绿色的 **"I understand my workflows, go ahead and enable them"**
3. 在左侧选中 `Game4Free 每小时自动续期`，点击右侧 **"Run workflow"** 手动测试

---

## ⚠️ 注意事项

> [!WARNING]
> **关于封号风险**
> 
> 虽然我们用了 AI 模拟真人操作，但**自动化行为可能违反免费主机的 Terms of Service**。建议：
> - 不要在服务器里放**特别重要**的存档
> - 记得**定期备份**！
> - 别把鸡蛋都放在一个篮子里

> [!CAUTION]
> **关于 IP 权重问题**
> 
> GitHub 的服务器 IP 偶尔会被谷歌判定为"可疑"。如果某次运行失败：
> - 别太慌，脚本**每小时都会重试**
> - 总有运气好的时候能过去
> - 连续失败？可以手动触发一次试试

> [!TIP]
> **路径说明**
> 
> 脚本里的图片保存路径已经针对 GitHub Actions 优化过了（使用 `/tmp/` 或工作目录），**一般情况下不需要改动**。

---

## 🛠️ 技术栈

- **Playwright** + **Stealth** —— 自动化浏览器 & 反检测
- **Gemini 1.5/2.5 Flash** —— AI 视觉大脑
- **python-telegram-bot** —— 消息推送
- **GitHub Actions** —— 云端调度

---

<div align="center">

### 🌟 觉得好用？给个 Star 支持一下！

[![Star History](https://img.shields.io/github/stars/wff0325/Game4freeRenew?style=social)](https://github.com/wff0325/Game4freeRenew/stargazers)

**有任何 Bug 或建议，欢迎提 [Issue](../../issues/new)！**

</div>

---

## 📄 License

[MIT](LICENSE) © 2026 - 让天下没有难续的服务器
