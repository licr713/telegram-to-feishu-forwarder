
import configparser
import logging
import os
import sys
import asyncio
from telethon import TelegramClient, events
import aiohttp

# --- 日志配置 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# --- 全局变量 ---
CONFIG_FILE = 'config.ini'
SESSION_FILE = 'telegram_forwarder.session'
MESSAGE_QUEUE = asyncio.Queue()  # 新增：全局消息队列

# --- 配置文件处理 ---
def create_config_interactively():
    """通过交互式命令行创建并保存配置文件"""
    config = configparser.ConfigParser()
    logging.info("未检测到配置文件，开始进行交互式配置...")

    while True:
        api_id_str = input("请输入您的 Telegram API ID: ").strip()
        if api_id_str.isdigit():
            api_id = api_id_str
            break
        else:
            logging.error("输入无效，API ID 必须是纯数字。请重新输入。")

    api_hash = input("请输入您的 Telegram API HASH: ").strip()
    target_channel = input("请输入目标公开频道的用户名 (不带 '@', 例如 'TG_beta') : ").strip()
    feishu_webhook_url = input("请输入飞书机器人的 Webhook URL: ").strip()

    config['telegram'] = {
        'api_id': api_id,
        'api_hash': api_hash,
        'target_channel': target_channel
    }
    config['feishu'] = {
        'webhook_url': feishu_webhook_url
    }

    with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
        config.write(configfile)
    
    logging.info(f"配置文件 '{CONFIG_FILE}' 已成功创建。")
    return config

def load_config():
    """加载配置文件，如果不存在则引导用户创建"""
    if not os.path.exists(CONFIG_FILE):
        return create_config_interactively()
    
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    return config

# --- 飞书消息发送 (异步) ---
async def send_to_feishu(session, text_content, webhook_url):
    """
    将文本内容格式化并异步发送到飞书机器人
    :param session: aiohttp.ClientSession 对象
    :param text_content: 从 Telegram 提取的纯文本
    :param webhook_url: 飞书机器人的 Webhook URL
    """
    if not text_content:
        logging.warning("待发送的文本内容为空，已跳过。")
        return

    headers = {
        'Content-Type': 'application/json'
    }
    payload = {
        "msg_type": "text",
        "content": {
            "text": text_content
        }
    }

    try:
        async with session.post(webhook_url, json=payload, headers=headers, timeout=10) as response:
            response_json = await response.json()
            if response.status == 200 and response_json.get("code") == 0:
                logging.info("成功转发消息到飞书。")
            else:
                logging.error(
                    f"发送到飞书失败。状态码: {response.status}, "
                    f"响应体: {await response.text()}"
                )
    except asyncio.TimeoutError:
        logging.error("发送到飞书时发生网络超时。")
    except aiohttp.ClientError as e:
        logging.error(f"发送到飞书时发生网络异常: {e}")
    except Exception as e:
        logging.error(f"发送到飞书时发生未知错误: {e}")


# --- 主程序 ---
async def main():
    """主程序入口"""
    # 1. 加载或创建配置
    config = load_config()
    try:
        api_id = config.getint('telegram', 'api_id')
        api_hash = config.get('telegram', 'api_hash')
        target_channel_username = config.get('telegram', 'target_channel')
        feishu_webhook_url = config.get('feishu', 'webhook_url')
    except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
        logging.error(f"配置文件 '{CONFIG_FILE}' 格式不正确或缺少必要项: {e}")
        logging.error("请删除旧的配置文件，然后重新运行脚本以生成新的正确配置。")
        return

    client = TelegramClient(SESSION_FILE, api_id, api_hash)

    async with aiohttp.ClientSession() as http_session:
        # 新增：worker 协程，按4秒一条速率转发消息
        async def feishu_worker():
            while True:
                text = await MESSAGE_QUEUE.get()
                await send_to_feishu(http_session, text, feishu_webhook_url)
                await asyncio.sleep(4)  # 限流：每4秒1条

        # 启动worker
        asyncio.create_task(feishu_worker())

        @client.on(events.NewMessage(chats=target_channel_username))
        async def message_handler(event):
            logging.info(f"监听到来自频道 '{target_channel_username}' 的新消息。")
            message_text = event.message.raw_text
            # 所有消息先入队
            await MESSAGE_QUEUE.put(message_text)

        try:
            await client.start()
            logging.info("成功登录 Telegram。")
            logging.info(f"开始监听频道 '{target_channel_username}' 的新消息...")
            await client.run_until_disconnected()
        except Exception as e:
            logging.error(f"程序启动或运行期间发生错误: {e}")
        finally:
            if client.is_connected():
                await client.disconnect()
            logging.info("客户端已断开连接。")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (ValueError, TypeError) as e:
        # 处理首次登录时 Telethon 可能引发的同步上下文错误
        logging.info("检测到首次登录，请在命令行中完成交互式验证...")
