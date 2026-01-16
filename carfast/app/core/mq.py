# app/core/mq.py
import json
import logging
import aio_pika
from aio_pika import connect_robust, Message, DeliveryMode, ExchangeType
from app.config import settings  # 确保新项目有 settings.RABBITMQ_URL

logger = logging.getLogger("uvicorn")


class RabbitMQClient:
    connection: aio_pika.Connection = None
    channel: aio_pika.Channel = None
    EXCHANGE_NAME = "pylab.direct"  # 新项目建议改为 "newproject.direct"

    @classmethod
    async def connect(cls):
        if cls.connection and not cls.connection.is_closed:
            return
        try:
            # connect_robust 支持断线自动重连
            cls.connection = await connect_robust(settings.RABBITMQ_URL)
            cls.channel = await cls.connection.channel()
            # 声明持久化交换机
            await cls.channel.declare_exchange(
                cls.EXCHANGE_NAME, ExchangeType.DIRECT, durable=True
            )
            logger.info("✅ [RabbitMQ] Connection established")
        except Exception as e:
            logger.error(f"❌ [RabbitMQ] Connection failed: {e}")

    @classmethod
    async def close(cls):
        """安全关闭 RabbitMQ 连接"""
        try:
            if cls.channel and not cls.channel.is_closed:
                await cls.channel.close()
                cls.channel = None
        except Exception as e:
            logger.warning(f"⚠️ [RabbitMQ] Channel close warning: {e}")
        
        try:
            if cls.connection and not cls.connection.is_closed:
                await cls.connection.close()
                cls.connection = None
        except Exception as e:
            logger.warning(f"⚠️ [RabbitMQ] Connection close warning: {e}")

    @classmethod
    async def publish(cls, routing_key: str, message: dict):
        if not cls.channel or cls.channel.is_closed:
            await cls.connect()

        exchange = await cls.channel.get_exchange(cls.EXCHANGE_NAME)
        await exchange.publish(
            Message(
                body=json.dumps(message).encode(),
                delivery_mode=DeliveryMode.PERSISTENT
            ),
            routing_key=routing_key
        )

    @classmethod
    async def consume(cls, queue_name: str, routing_key: str, callback_func):
        """简单封装的消费者"""
        if not cls.channel:
            await cls.connect()

        queue = await cls.channel.declare_queue(queue_name, durable=True)
        await queue.bind(cls.EXCHANGE_NAME, routing_key=routing_key)

        async def message_wrapper(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    await callback_func(data)
                except Exception as e:
                    logger.error(f"❌ Consumer Error: {e}")
                    raise e

        await queue.consume(message_wrapper)
        logger.info(f"👂 [RabbitMQ] Listening on {queue_name}")