"""Run IAM ACK outbox once or in a supervised foreground polling process.

Example: python -m pyaccountingkit.company_configuration.infrastructure.iam.delivery_runner
  --once --batch 10

Deployment must restrict environment secrets and supervise process termination.
"""

import argparse
import json
import os
import signal
import time
from dataclasses import asdict

from .ack_delivery import IamAckDeliveryWorker
from .ack_operations import IamAckOperationsRunner
from .http_revocation_source import HttpsIamRevocationSource
from ..postgres.iam_ack_operations import PostgresIamAckMetrics
from ..postgres.iam_ack_outbox import PostgresIamAckOutbox


class JsonTelemetry:
    def report(self, sample) -> None:
        print(json.dumps(asdict(sample), sort_keys=True), flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Restricted IAM ACK delivery runner")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--batch", type=int, default=10)
    parser.add_argument("--poll-seconds", type=int, default=15)
    args = parser.parse_args(argv)
    if not 1 <= args.batch <= 20 or not 1 <= args.poll_seconds <= 300:
        parser.error("--batch must be 1..20; --poll-seconds must be 1..300")
    dsn = os.environ["CC_PG_IAM_DELIVERY_DSN"]
    origin = os.environ["CC_IAM_HTTPS_ORIGIN"]
    bearer = os.environ["CC_IAM_BEARER_TOKEN"]
    # Never log these inputs. This CLI requires a separately restricted SQL role.
    worker = IamAckDeliveryWorker(
        outbox=PostgresIamAckOutbox(dsn),
        source=HttpsIamRevocationSource(origin=origin, bearer_token=bearer),
    )
    runner = IamAckOperationsRunner(
        worker=worker, metrics=PostgresIamAckMetrics(dsn), telemetry=JsonTelemetry(),
    )
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while not stopping:
        runner.tick(limit=args.batch)
        if args.once:
            break
        # Termination is checked after each bounded foreground cycle.
        time.sleep(args.poll_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
