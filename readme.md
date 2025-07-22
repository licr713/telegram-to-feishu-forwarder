# Telegram to Feishu Forwarder

## 1. 项目简介

这是一个独立的、轻量级的 Python 脚本，旨在实现将指定的公开 Telegram 频道消息，实时转发到指定的飞书（Lark）群聊中。

本项目不依赖任何第三方平台（如 n8n），通过直接调用 Telegram API 和飞书机器人 Webhook 实现端到端的实时消息转发。其设计目标是作为一个系统服务，在 Linux 服务器上 7x24 小时稳定运行。

---

## 2. 核心功能

1.  **交互式配置**: 首次运行时，脚本会通过命令行交互式地引导用户输入必要的配置信息，并将其保存以供后续使用。
2.  **实时消息监听**: 使用 `telethon` 库以用户身份登录 Telegram，并实时监听指定公开频道的 `NewMessage` 事件。
3.  **会话持久化**: 首次成功登录后，会自动在本地创建 `.session` 文件，避免后续重复进行短信或密码验证。
4.  **内容提取**: 从捕获的 Telegram 消息中，仅提取其核心的纯文本内容 (`raw_text`)。
5.  **飞书消息格式化**: 将提取的文本内容，构建成符合飞书自定义机器人 API 要求的 `text` 类型 JSON 消息体。
6.  **直接转发**: 使用 `requests` 库，通过 HTTP POST 请求，将格式化后的消息直接发送到用户指定的飞书机器人 Webhook URL。
7.  **后台服务化**: 设计上兼容 Linux 的 `systemd` 服务管理，能够实现后台运行、开机自启和进程守护（意外崩溃后自动重启）。

---

## 3. 技术栈

-   **Python 3**
-   **Telethon**: 用于与 Telegram User API 交互。
-   **Requests**: 用于发送 HTTP POST 请求。

---

## 4. 实现细节要求

### 4.1 脚本执行流程

-   **首次运行**:
    1.  检查本地是否存在一个配置文件（如 `config.ini`）。
    2.  如果不存在，则通过 `input()` 函数，依次提示用户输入以下信息：
        -   `API_ID` (Telegram App API ID)
        -   `API_HASH` (Telegram App API Hash)
        -   `TARGET_CHANNEL` (目标 Telegram 频道的用户名，**不带@**)
        -   `FEISHU_WEBHOOK_URL` (飞书机器人的 Webhook 链接)
    3.  将用户输入的信息，保存到 `config.ini` 文件中。
    4.  提示用户：“配置已保存。现在将进行首次登录...”
    5.  使用 `telethon` 配合保存的配置进行交互式登录，生成 `.session` 文件。
    6.  进入持续监听状态。

-   **后续运行**:
    1.  检测到 `config.ini` 和 `.session` 文件已存在。
    2.  直接读取 `config.ini` 加载配置。
    3.  使用 `.session` 文件静默登录，跳过验证。
    4.  直接进入持续监听状态。

### 4.2 错误处理与日志

-   使用 Python 内置的 `logging` 模块，将日志信息输出到标准输出。
-   日志应包含时间戳、日志级别和消息内容。
-   需要对 `requests.post` 调用进行 `try...except` 封装，捕获网络异常。
-   需要检查飞书 Webhook 的响应状态码，若非 `200`，则记录一条 `ERROR` 级别的日志，包含状态码和响应体内容。

### 4.3 配置文件 (`config.ini`) 示例

脚本应能读取和写入类似以下格式的配置文件：

```ini
[telegram]
api_id = 12345678
api_hash = abcdef1234567890abcdef1234567
target_channel = Financial_Express

[feishu]
webhook_url = https://open.feishu.cn/open-apis/bot/v2/hook/xxxx```

### 4.4 待生成的配套文件

请同时生成一个 `requirements.txt` 文件，内容如下：

```txt
telethon
requests
```

---

## 5. 部署指南（供参考）

该脚本最终将被部署为一个 `systemd` 服务。以下是一个 `systemd` 服务文件 (`telegram-forwarder.service`) 的示例模板，脚本的实现应与此部署方式兼容：

```ini
[Unit]
Description=Telegram to Feishu Forwarder Service
After=network.target

[Service]
User=your_username
WorkingDirectory=/path/to/your/script_directory
ExecStart=/usr/bin/python3 main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target```

请根据以上详细需求，生成主程序 `main.py` 和 `requirements.txt` 文件的完整代码。