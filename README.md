# ⭐ Star 星星走起 动动发财手点点 ⭐

## ClawCloud 官网(GitHub注册送5美元地址)：[run.claw.cloud](https://console.run.claw.cloud/signin?link=M9P7GXP3M3W5)

> 自动登录 ClawCloud，保持账户活跃，支持设备验证 + 两步验证

![设备验证](./3.png)

---

## ⚠️ 注意事项

- 支持 **Mobile验证** 和 **2FA验证**
- 首次运行：需要设备验证，收到 TG 通知后 **30 秒内** 批准
- REPO_TOKEN：需要有 `repo` 权限才能自动更新 Cookie
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

## 方式一：GitHub Action运行
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

## 方式二：部署在自己VPS上面运行
### 1. 把项目中VPS目录下的三个文件拷贝到你服务器上面，建议路径 **/opt/claw-auto**

### 2. 修改run.sh文件内容，把相关参数值改为你自己的

### 3. 安装运行需要的环境
```
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

```
### 4. 创建Python虚拟机环境
```
python3 -m venv venv
source venv/bin/activate

```
### 5. 安装Python依赖包
该脚本引用了 requests, playwright, 和 pynacl（用于 SecretUpdater 部分）。

```
pip install --upgrade pip
pip install playwright requests pynacl
```
### 6. 安装playwright 和相关依赖
```
playwright install chromium --with-deps
```
### 7. 单次执行，测试脚本
- 确保你当前属于Python虚拟环境，判断方式，命令行用户名前面有个括号写着虚拟环境名，例如 **(venv) root@**
- 如果不在虚拟环境，执行命令 source venv/bin/activate ，进入
- 授权run.sh 脚本可执行权限 chmod +x run.sh
- 运行，./run.sh 。观察日志和TG通知

### 8. 定时执行，脚本scheduler.py 是定义每15-20天随机执行一次
```
nohup ./venv/bin/python scheduler.py > claw.log 2>&1 &
```

## 📊 流程图
```
┌─────────────────────────────────────────────────────────┐
│  1. 打开 ClawCloud 登录页                                │
│         ↓                                               │
│  2. 点击 "GitHub" 登录按钮                               │
│         ↓                                               │
│  3. GitHub 认证                                         │
│     ├── 输入用户名/密码                                  │
│     ├── 设备验证 (如需要) → 等待30秒/邮件批准             │
│     └── 两步验证 (如需要)                                │
│         ├── GitHub Mobile → 等待手机批准                 │
│         └── TOTP → 通过 Telegram /code 123456 输入       │
│         ↓                                               │
│  4. OAuth 授权 (如需要)                                  │
│         ↓                                               │
│  5. 等待重定向回 ClawCloud                               │
│         ↓                                               │
│  6. 保活操作 (访问控制台/应用页面)                        │
│         ↓                                               │
│  7. 提取新 Cookie 并保存/通知                            │
└─────────────────────────────────────────────────────────┘
```
---

## 📁 文件结构

```
.
├── .github/
│   └── workflows/
│       └── auto_login.yml    # GitHub Actions 配置
├── VPS/
│   └── auto_login.py         # VPS上面自动登录脚本
├   ├── scheduler.py          # 定时任务脚本
├   └── run.sh                # 运行脚本
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
[感谢：axibayuit-a11y佬](https://github.com/axibayuit-a11y)  优化：支持了2fa验证

欢迎提交 Issue 和 Pull Request！

⭐ 如果对你有帮助，请点个 Star 支持一下！
