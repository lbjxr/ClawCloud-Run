# ClawCloud 自动登录保活

## ⭐ Star 星星走起 动动发财手点点 ⭐

> 自动登录 ClawCloud，保持账户活跃，支持设备验证 + 两步验证

![设备验证](./3.png)

---

## ⚠️ 注意事项

- 支持 **Mobile验证** 和 **2FA验证**
- 首次运行：需要设备验证，收到 TG 通知后 **30 秒内** 批准
- REPO_TOKEN：需要有 `repo` 权限才能自动更新 Secret
- Cookie 有效期：每次运行都会更新，保持最新

### Mobile 验证
![Mobile验证](./1.png)

### 2FA 验证
![2FA验证](./4.png)

### 验证设置
![设置Mobile优先验证](./2.png)

---

## 🔐 Secrets 配置

| Secret 名称 | 必需 | 说明 |
|-------------|------|------|
| `GH_USERNAME` | ✅ | GitHub 用户名 |
| `GH_PASSWORD` | ✅ | GitHub 密码 |
| `GH_SESSION` | ❌ | 自动生成，无需手动添加 |
| `TG_BOT_TOKEN` | ❌ | Telegram Bot Token |
| `TG_CHAT_ID` | ❌ | Telegram Chat ID |
| `REPO_TOKEN` | ❌ | GitHub PAT（用于自动更新 Secret） |

---

## 🚀 快速开始

### 1. Fork 仓库

点击右上角 **Fork** 按钮

### 2. 配置 Secrets

进入 **Settings** → **Secrets and variables** → **Actions**，添加：

**必需：**
- `GH_USERNAME` - GitHub 用户名
- `GH_PASSWORD` - GitHub 密码

**推荐：**
- `TG_BOT_TOKEN` - Telegram Bot Token
- `TG_CHAT_ID` - Telegram Chat ID
- `REPO_TOKEN` - GitHub Personal Access Token

### 3. 启用 Actions

进入 **Actions** → 点击 **I understand my workflows**

### 4. 手动测试

选择 **ClawCloud 自动登录保活** → **Run workflow**

---

## 📊 流程图

```text
开始
  ↓
加载已保存的 Cookie（如果有）
  ↓
访问 ClawCloud
  ↓
已登录？ ─是→ 保活 → 提取新 Cookie → 保存 → 完成
  ↓否
点击 GitHub 登录
  ↓
Cookie 有效？ ─是→ 直接 OAuth 授权
  ↓否
输入用户名密码
  ↓
需要设备验证？ ─是→ 发送 TG 通知 → 等待 30 秒
  ↓
登录成功
  ↓
OAuth 授权
  ↓
重定向到 ClawCloud
  ↓
保活（访问控制台、应用页面）
  ↓
提取新的 Session Cookie
  ↓
自动更新 GH_SESSION Secret
  ↓
发送 Telegram 通知
  ↓
完成 ✅

```

---

## 📁 文件结构

```
.
├── .github/
│   └── workflows/
│       └── auto_login.yml    # GitHub Actions 配置
├── scripts/
│   └── auto_login.py         # 自动登录脚本
├── 1.png                      # Mobile 验证截图
├── 2.png                      # 设置截图
├── 3.png                      # 主截图
├── 4.png                      # 2FA 截图
└── README.md
```

---

## 🐛 常见问题

### Q: 设备验证超时怎么办？
A: 确保 Telegram 通知已配置，收到通知后立即在邮箱或 GitHub App 批准。

### Q: 2FA 验证码怎么输入？
A: 在 Telegram 发送 `/code 123456`（替换为你的 6 位验证码）。

### Q: Cookie 更新失败？
A: 检查 `REPO_TOKEN` 是否有 `repo` 权限。

### Q: 为什么需要 GitHub 密码？
A: 用于 Cookie 失效时重新登录，密码存储在 GitHub Secrets 中，安全可靠。

---

## 📄 License

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

⭐ 如果对你有帮助，请点个 Star 支持一下！
