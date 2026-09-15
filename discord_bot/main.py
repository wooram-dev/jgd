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

async def main():
    """Main function to run the bot"""
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated successfully")
        
        # Create bot instance
        bot = create_bot()
        logger.info("Bot instance created")
        
        # Start the bot
        logger.info("Starting bot...")
        async with bot:
            await bot.start(Config.DISCORD_TOKEN)
            
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your .env file and make sure all required values are set")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)