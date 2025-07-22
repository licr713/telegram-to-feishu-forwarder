# Telegram to Feishu Forwarder (Telegram 消息实时转发飞书机器人)

## 1. 项目简介

这是一个轻量级的 Python 脚本，用于将指定的公开 Telegram 频道消息，实时转发到指定的飞书（Lark）群聊中。

本项目旨在作为一个 7x24 小时运行的后台服务，不依赖任何第三方集成平台，实现了从 Telegram 到飞书的端到端消息同步。

## 2. 功能特性

- **交互式配置**: 首次运行脚本时，将引导您完成所有必要信息的配置。
- **实时转发**: 实时监听 Telegram 频道新消息并立即转发。
- **会话持久化**: 首次登录 Telegram 成功后，自动保存会话，无需重复验证。
- **纯文本提取**: 仅转发消息中的核心文本内容，保持信息清爽。
- **后台服务化**: 设计上与 Linux `systemd` 完美兼容，可实现开机自启和进程守护。
- **轻量独立**: 仅依赖 `telethon` 和 `requests` 两个库，部署简单。

## 3. 环境准备 (Prerequisites)

在开始之前，请确保您已准备好以下信息：

1.  **一台可以访问 Telegram 的服务器**: 推荐使用 Linux 系统以便于后台部署。
2.  **Python 3.6+ 环境**:
3.  **Telegram 账号**: 用于监听频道的账号。
4.  **Telegram API 凭证**:
    *   访问 [my.telegram.org](https://my.telegram.org)。
    *   使用您的 Telegram 账号登录。
    *   点击 "API development tools"，填写一个应用名称（任意填写），获取您的 `api_id` 和 `api_hash`。
5.  **目标 Telegram 公开频道**: 您希望转发其消息的公开频道的用户名（例如 `Financial_Express`，不带 `@`）。
6.  **飞书群聊机器人 Webhook**:
    *   在目标飞书群聊中，点击右上角“设置” -> “群机器人” -> “添加机器人”。
    *   选择“自定义机器人”。
    *   设置一个机器人名称和描述，点击“添加”。
    *   在安全设置中，可以根据需要选择一种安全校验方式（脚本默认不添加额外校验，仅需 Webhook URL）。
    *   复制生成的 `Webhook 地址`。

## 4. 安装与配置

### 第一步：下载代码并安装依赖

```bash
# 建议创建一个新的项目目录
mkdir telegram-forwarder
cd telegram-forwarder

# 此处假设您已将 main.py 和 requirements.txt 放入该目录
# 创建 Python 虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate

# 安装依赖库
pip install -r requirements.txt
```

### 第二步：首次运行并生成配置

直接运行主脚本，程序将引导您进行配置。

```bash
python3 main.py
```

脚本会依次提示您输入在 **“环境准备”** 步骤中获取的四项信息：

- `API_ID`
- `API_HASH`
- `TARGET_CHANNEL` (公开频道的用户名)
- `FEISHU_WEBHOOK_URL`

输入完成后，脚本会自动创建 `config.ini` 文件保存您的配置。

### 第三步：登录 Telegram

配置保存后，脚本会立即尝试登录 Telegram。您可能会在手机上收到 Telegram 的验证码，请按提示在命令行中输入验证码。

如果您的账号开启了二次验证（Two-Step Verification），还需要输入您的密码。

成功登录后，脚本目录中会生成一个 `.session` 文件。此文件保存了您的登录状态，**请务必妥善保管，不要泄露**。同时，脚本会开始正式工作，监听并转发消息。

## 5. 日常使用

后续再次运行脚本，它将自动读取 `config.ini` 和 `.session` 文件，静默登录并直接开始工作，无需任何手动操作。

```bash
# 确保虚拟环境已激活
source venv/bin/activate
# 直接运行即可
python3 main.py
```

所有运行日志（包括成功转发的记录和可能出现的错误）都会直接打印在控制台。

## 6. 部署为后台服务 (Systemd)

为了让脚本能在服务器后台长期稳定运行，推荐使用 `systemd` 进行管理。

### 第一步：创建服务文件

在 `/etc/systemd/system/` 目录下创建一个名为 `telegram-forwarder.service` 的文件：

```bash
sudo nano /etc/systemd/system/telegram-forwarder.service
```

将以下内容粘贴到文件中：

```ini
[Unit]
Description=Telegram to Feishu Forwarder Service
After=network.target

[Service]
# 【重要】请修改为您自己的用户名
User=your_username

# 【重要】请修改为您的脚本所在的绝对路径
WorkingDirectory=/path/to/your/script_directory

# 【重要】请确保 python3 的路径正确，且指向包含依赖库的环境
ExecStart=/path/to/your/script_directory/venv/bin/python3 main.py

Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**请务必修改 `User`、`WorkingDirectory` 和 `ExecStart` 中的路径为您服务器上的实际情况。** `ExecStart` 应该指向您在虚拟环境中的 Python 解释器。

### 第二步：管理服务

```bash
# 重新加载 systemd 配置，使新服务生效
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start telegram-forwarder

# 查看服务状态，确认是否成功运行
sudo systemctl status telegram-forwarder

# 设置服务开机自启
sudo systemctl enable telegram-forwarder

# 查看实时日志
sudo journalctl -u telegram-forwarder -f

# 停止服务
sudo systemctl stop telegram-forwarder
```

## 7. 故障排查

- **收不到飞书消息**:
    1.  检查 `journalctl -u telegram-forwarder` 日志中是否有错误信息。
    2.  确认飞书机器人的 Webhook URL 是否正确且未失效。
    3.  确认服务器网络可以访问飞书域名。
- **Telegram 无法登录**:
    1.  确认 `api_id` 和 `api_hash` 是否正确。
    2.  首次登录时，检查验证码或二次验证密码是否输入正确。
    3.  如果频繁失败，Telegram 可能会暂时限制登录，请稍后再试。
    4.  删除 `.session` 文件可以强制重新进行交互式登录。
