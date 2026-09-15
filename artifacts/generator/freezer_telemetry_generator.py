#!/usr/bin/env python3
"""
freezer_telemetry_generator.py -- Fabric IQ workshop synthetic telemetry pusher.

Simulates live temperature/door-sensor telemetry for the 15 freezers defined
in artifacts/SampleData/freezers.csv, and pushes one JSON event per freezer
per interval into a Fabric Eventstream custom-endpoint source, which routes
them on to ColdChainEventhouse.ColdChainKQLDB.FreezerTelemetryRaw.

Event shape (matches the KQL ingestion mapping in
artifacts/Eventhouse/ColdChainKQLDB.kql):
    {
        "FreezerId": "FRZ001",
        "StoreId": "ST01",
        "Timestamp": "2026-09-06T14:32:01.123456+00:00",
        "TemperatureC": -17.8,
        "DoorOpen": false
    }

Temperature model: a bounded random walk around a cold-chain setpoint of
-18C. Periodically (per freezer, at random), an "anomaly episode" is
injected: the temperature drifts upward toward -10C over a few minutes
(simulating a door left open or a compressor fault), then recovers. This is
the exact signal that Module 04's Activator/ontology rules are built to
detect live during the workshop -- do not "fix" the anomaly logic without
checking whether a later lab's expected threshold (-12C, see the KQL
script's sanity-check comments) still lines up.

-------------------------------------------------------------------------
A NOTE ON WHY THIS SCRIPT USES `azure-eventhub` INSTEAD OF PLAIN `requests`
-------------------------------------------------------------------------
Fabric Eventstream's "custom endpoint" source does not expose a plain HTTPS
POST endpoint -- the connection string it issues
(`Endpoint=sb://...;SharedAccessKeyName=...;SharedAccessKey=...;EntityPath=...`)
is an Azure Event Hubs-compatible SAS connection string, authenticated over
AMQP. A bare `requests.post(...)` call cannot speak that protocol, so it
would silently fail to deliver events -- exactly the kind of fragile,
unverified assumption this workshop's artifacts are supposed to avoid.
`azure-eventhub` is the official, actively-maintained Microsoft SDK built
for precisely this connection string shape, so it is used here instead.
It is the ONLY non-stdlib dependency this script needs:

    pip install azure-eventhub

(Fabric also supports a Kafka-protocol custom endpoint, if you'd rather use
a Kafka client library -- see the Eventstream HOW-TO-EXPORT.md for details.
This script sticks to the Event Hubs/AMQP protocol since it needs only one
extra package and matches the default connection string shown in the
Fabric portal's "Keys" tab.)

-------------------------------------------------------------------------
USAGE
-------------------------------------------------------------------------
    pip install azure-eventhub
    python freezer_telemetry_generator.py [--interval-seconds 5] [--freezers-csv PATH]

    # Send a fixed number of ticks instead of running forever (handy for a
    # quick connectivity smoke-test before the live demo):
    python freezer_telemetry_generator.py --max-ticks 3

Stop anytime with Ctrl+C -- the producer client is closed cleanly.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# TODO: paste your Eventstream custom endpoint connection info here -- see lab-02.
#
# 1. In the Fabric portal, open FreezerTelemetryEventstream in edit mode.
# 2. Select the custom-endpoint SOURCE node ("FreezerTelemetrySource").
# 3. On the Details pane, open the "Event Hub" tab > "Keys" (or "SAS Key
#    Authentication") page, and copy "Connection string-primary key".
# 4. Paste it below. It looks like:
#    "Endpoint=sb://eventstream-xxxxxxxx.servicebus.windows.net/;SharedAccessKeyName=key_xxxxxxxx;SharedAccessKey=xxxxxxxx;EntityPath=es_xxxxxxxx"
#
# The EntityPath segment already tells the SDK which event hub to use, so you
# do NOT need to set EVENTHUB_NAME separately unless your connection string
# omits EntityPath (uncommon) -- in that case, set it explicitly below.
EVENTSTREAM_CONNECTION_STRING = "PASTE-YOUR-EVENTSTREAM-CUSTOM-ENDPOINT-CONNECTION-STRING-HERE"
EVENTHUB_NAME: str | None = None  # only needed if EntityPath isn't in the connection string above

# Cold-chain setpoint and random-walk tuning. Feel free to tweak these for a
# more/less dramatic live demo, but keep FREEZER_SETPOINT_C and
# ANOMALY_TARGET_C consistent with the -12C threshold used in the KQL
# script's sanity-check query and in later Activator/ontology rule labs.
FREEZER_SETPOINT_C = -18.0
NORMAL_STEP_STDDEV_C = 0.15        # per-tick random-walk noise while healthy
ANOMALY_TARGET_C = -10.0           # how warm an anomaly episode drifts toward
ANOMALY_STEP_C = 0.35              # per-tick drift toward the anomaly target
RECOVERY_STEP_C = 0.5              # per-tick drift back toward setpoint after recovery starts
ANOMALY_START_PROBABILITY = 0.003  # per freezer, per tick, chance a new anomaly episode begins
ANOMALY_MIN_TICKS = 24             # minimum length of an anomaly episode, in ticks
ANOMALY_MAX_TICKS = 60             # maximum length of an anomaly episode, in ticks


@dataclass
class FreezerState:
    freezer_id: str
    store_id: str
    temperature_c: float = FREEZER_SETPOINT_C
    door_open: bool = False
    anomaly_ticks_remaining: int = 0
    anomaly_recovering: bool = False

    def tick(self) -> None:
        """Advance this freezer's simulated state by one interval."""
        if self.anomaly_ticks_remaining > 0:
            self.anomaly_ticks_remaining -= 1
            if not self.anomaly_recovering:
                # Drift up toward the anomaly target (door left open / compressor fault).
                self.temperature_c += ANOMALY_STEP_C + random.gauss(0, NORMAL_STEP_STDDEV_C)
                self.temperature_c = min(self.temperature_c, ANOMALY_TARGET_C)
                self.door_open = random.random() < 0.6  # door mostly open during the episode
                if self.temperature_c >= ANOMALY_TARGET_C or self.anomaly_ticks_remaining <= ANOMALY_MIN_TICKS // 2:
                    self.anomaly_recovering = True
            else:
                # Recovery: drift back down toward setpoint.
                self.temperature_c -= RECOVERY_STEP_C + random.gauss(0, NORMAL_STEP_STDDEV_C)
                self.temperature_c = max(self.temperature_c, FREEZER_SETPOINT_C)
                self.door_open = False
            if self.anomaly_ticks_remaining == 0:
                self.anomaly_recovering = False
        else:
            # Healthy random walk around the setpoint.
            self.temperature_c += random.gauss(0, NORMAL_STEP_STDDEV_C)
            # Gently pull back toward the setpoint so the walk doesn't drift away.
            self.temperature_c += (FREEZER_SETPOINT_C - self.temperature_c) * 0.05
            self.door_open = random.random() < 0.02  # brief, normal door openings

            if random.random() < ANOMALY_START_PROBABILITY:
                self.anomaly_ticks_remaining = random.randint(ANOMALY_MIN_TICKS, ANOMALY_MAX_TICKS)
                self.anomaly_recovering = False

    def to_event(self) -> dict:
        return {
            "FreezerId": self.freezer_id,
            "StoreId": self.store_id,
            "Timestamp": datetime.now(timezone.utc).isoformat(),
            "TemperatureC": round(self.temperature_c, 2),
            "DoorOpen": self.door_open,
        }


def load_freezers(csv_path: Path) -> list[FreezerState]:
    """Read FreezerId/StoreId pairs from freezers.csv (ignores the other
    reference columns -- Model/Capacity/InstallDate live in the Lakehouse,
    not in the live telemetry stream)."""
    if not csv_path.exists():
        sys.exit(
            f"Could not find freezers CSV at {csv_path}. "
            "Run this script from the repo root, or pass --freezers-csv explicitly."
        )
    freezers: list[FreezerState] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            freezers.append(FreezerState(freezer_id=row["FreezerId"], store_id=row["StoreId"]))
    if not freezers:
        sys.exit(f"No rows found in {csv_path}.")
    return freezers


def build_producer(connection_string: str, eventhub_name: str | None):
    """Create an azure-eventhub EventHubProducerClient. Imported lazily so
    that --help and argument-parsing errors don't require azure-eventhub to
    already be installed."""
    try:
        from azure.eventhub import EventHubProducerClient
    except ImportError:
        sys.exit(
            "The 'azure-eventhub' package is required to send events.\n"
            "Install it with:  pip install azure-eventhub"
        )

    if connection_string.startswith("PASTE-YOUR-"):
        sys.exit(
            "EVENTSTREAM_CONNECTION_STRING is still the placeholder value.\n"
            "Open freezer_telemetry_generator.py and paste your Eventstream "
            "custom endpoint connection string at the top of the file -- see lab-02."
        )

    kwargs = {"conn_str": connection_string}
    if eventhub_name:
        kwargs["eventhub_name"] = eventhub_name
    return EventHubProducerClient.from_connection_string(**kwargs)


def run(
    connection_string: str,
    eventhub_name: str | None,
    freezers_csv: Path,
    interval_seconds: float,
    max_ticks: int | None,
) -> None:
    freezers = load_freezers(freezers_csv)
    print(f"Loaded {len(freezers)} freezers from {freezers_csv}")

    producer = build_producer(connection_string, eventhub_name)
    print(
        f"Connected. Sending one batch of {len(freezers)} events every "
        f"{interval_seconds}s. Press Ctrl+C to stop."
    )

    ticks = 0
    try:
        while max_ticks is None or ticks < max_ticks:
            for freezer in freezers:
                freezer.tick()

            events = [freezer.to_event() for freezer in freezers]

            batch = producer.create_batch()
            for event in events:
                from azure.eventhub import EventData
                import json as _json

                try:
                    batch.add(EventData(_json.dumps(event)))
                except ValueError:
                    # Batch is full (shouldn't happen at our event sizes/counts,
                    # but flush and start a new batch defensively).
                    producer.send_batch(batch)
                    batch = producer.create_batch()
                    batch.add(EventData(_json.dumps(event)))
            producer.send_batch(batch)

            anomalies = [e["FreezerId"] for e in events if e["TemperatureC"] > -12.0]
            status = f"tick {ticks + 1}: sent {len(events)} events"
            if anomalies:
                status += f" | ANOMALY: {', '.join(anomalies)}"
            print(status)

            ticks += 1
            if max_ticks is None or ticks < max_ticks:
                time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nStopping (Ctrl+C received).")
    finally:
        producer.close()
        print("Producer closed. Goodbye.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Push synthetic freezer telemetry to a Fabric Eventstream custom endpoint.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=5,
        help="Seconds to wait between telemetry batches.",
    )
    parser.add_argument(
        "--freezers-csv",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "SampleData" / "freezers.csv",
        help="Path to freezers.csv (defaults to ../SampleData/freezers.csv relative to this script).",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=None,
        help="Send this many batches and then exit, instead of running forever (useful for a smoke test).",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    run(
        connection_string=EVENTSTREAM_CONNECTION_STRING,
        eventhub_name=EVENTHUB_NAME,
        freezers_csv=args.freezers_csv,
        interval_seconds=args.interval_seconds,
        max_ticks=args.max_ticks,
    )


if __name__ == "__main__":
    main()
