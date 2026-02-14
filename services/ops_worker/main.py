import asyncio

from health_monitor import run_health_monitor
from metrics_collector import run_metrics_collector
from shared.logging import configure_logging

configure_logging("ops_worker")


async def main() -> None:
    await asyncio.gather(
        run_health_monitor(),
        run_metrics_collector(),
    )


if __name__ == "__main__":
    asyncio.run(main())
