"""手动百炼连接烟雾测试；凭据只从临时环境变量读取。"""

from __future__ import annotations

import asyncio
import os

from xiangqi_tutor.tutor.openai_compatible import OpenAICompatibleProvider


async def main() -> None:
    provider = OpenAICompatibleProvider(
        base_url=os.environ["XIANGQI_TEST_BASE"],
        api_key=os.environ["XIANGQI_TEST_KEY"],
        model=os.getenv("XIANGQI_TEST_MODEL", "qwen-plus"),
    )
    try:
        model, latency = await provider.test_connection()
        print("BAILIAN_OK", model, round(latency, 2))
    finally:
        await provider.aclose()


if __name__ == "__main__":
    asyncio.run(main())
