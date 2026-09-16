#!/usr/bin/env python3
"""
Discord Bot Main Entry Point

확장 가능한 디스코드 봇
- /speak 명령어로 지정된 채널에 메시지 전송
- 모듈화된 구조로 쉬운 기능 확장 가능
"""

import asyncio
import sys
import logging
import aiohttp
import discord
from bot import create_bot, Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

GATEWAY_RETRY_DELAYS = (5, 10, 30, 60)


def is_retryable_gateway_error(error: Exception) -> bool:
    """Return whether a transient Gateway failure should restart the client."""
    if isinstance(error, (aiohttp.ClientError, discord.ConnectionClosed, discord.GatewayNotFound, discord.DiscordServerError, OSError)):
        return True

    # discord.py can raise this secondary error after a failed WebSocket
    # handshake, when no websocket sequence has been established yet.
    return (
        isinstance(error, AttributeError)
        and "'NoneType' object has no attribute 'sequence'" in str(error)
    )

async def main():
    """Main function to run the bot"""
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your .env file and make sure all required values are set")
        sys.exit(1)

    logger.info("Configuration validated successfully")
    retry_attempt = 0

    while True:
        bot = create_bot()
        logger.info("Bot instance created")
        logger.info("Starting bot...")

        try:
            async with bot:
                await bot.start(Config.DISCORD_TOKEN, reconnect=False)
        except Exception as e:
            if not is_retryable_gateway_error(e):
                logger.exception("Bot stopped because of an unexpected error")
                raise

            delay = GATEWAY_RETRY_DELAYS[
                min(retry_attempt, len(GATEWAY_RETRY_DELAYS) - 1)
            ]
            retry_attempt += 1
            logger.warning(
                "Discord Gateway connection failed (%s). Retrying in %s seconds "
                "(attempt %s).",
                e,
                delay,
                retry_attempt,
            )
            await asyncio.sleep(delay)
        else:
            logger.info("Bot stopped normally")
            return

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
