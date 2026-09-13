"""Dry-run or create a repaired OFFLINE COPY of raw-angle recorder statistics.

Never writes the source database. Requires independently verified raw/degree time
boundaries; refuses mixed/ambiguous buckets instead of guessing. This changes
aggregated statistics only, not original state history. See docs/statistics-repair.md.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sqlite3


TABLES = {"statistics": 3600, "statistics_short_term": 300}


def timestamp(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("A timezone-aware boundary is required")
    return dt.timestamp()


def inspect(connection, statistic_ids, raw_before, degrees_from):
    """Return a precise plan without changing metadata or measurements."""
    if not statistic_ids or len(set(statistic_ids)) != len(statistic_ids):
        raise ValueError("Choose explicit, distinct orientation statistic IDs")
    if raw_before > degrees_from:
        raise ValueError("Raw and degree intervals must not overlap")
    if connection.execute("SELECT 1 FROM sqlite_master WHERE name='gardena_angle_migration'").fetchone():
        raise ValueError("This copy was already migrated; refusing to scale twice")
    plan = []
    for statistic_id in statistic_ids:
        row = connection.execute(
            "SELECT id,unit_of_measurement,source FROM statistics_meta WHERE statistic_id=?",
            (statistic_id,),
        ).fetchone()
        if row is None or row[2] != "recorder" or row[1] not in (None, "°"):
            raise ValueError(f"Unrecognised source/unit for {statistic_id}")
        item = {"statistic_id": statistic_id, "metadata_id": row[0], "old_unit": row[1], "tables": {}}
        for table, seconds in TABLES.items():
            counts = connection.execute(
                f"SELECT count(*),sum(CASE WHEN start_ts+?<=? THEN 1 ELSE 0 END),"
                "sum(CASE WHEN start_ts>=? THEN 1 ELSE 0 END) "
                f"FROM {table} WHERE metadata_id=?",
                (seconds, raw_before, degrees_from, row[0]),
            ).fetchone()
            total, raw, degrees = counts[0], counts[1] or 0, counts[2] or 0
            item["tables"][table] = {"raw": raw, "degrees": degrees, "ambiguous": total-raw-degrees}
        plan.append(item)
    return plan


def repair_copy(source, destination, statistic_ids, raw_before, degrees_from):
    """Snapshot and repair a new copy; reject any mixed bucket before writing."""
    destination = Path(destination)
    if destination.exists() or destination.resolve() == Path(source).resolve():
        raise ValueError("Destination must be a new, separate offline database")
    # 'x' prevents racing an existing destination. sqlite backup supplies a
    # consistent snapshot even when the read-only source is in WAL mode.
    with destination.open("xb"):
        pass
    with sqlite3.connect(f"{Path(source).resolve().as_uri()}?mode=ro", uri=True) as src:
        with sqlite3.connect(destination) as dst:
            src.backup(dst)
            plan = inspect(dst, statistic_ids, raw_before, degrees_from)
            if any(t["ambiguous"] for item in plan for t in item["tables"].values()):
                raise ValueError("Mixed/ambiguous buckets found. Destination is an unchanged snapshot; no repair applied")
            with dst:
                for item in plan:
                    for table, seconds in TABLES.items():
                        # Multiplication preserves NULLs. State/sum are included
                        # defensively, though angle measurements normally use mean/min/max.
                        dst.execute(
                            f"UPDATE {table} SET mean=mean*0.1,min=min*0.1,max=max*0.1,"
                            "state=state*0.1,sum=sum*0.1 WHERE metadata_id=? AND start_ts+?<=?",
                            (item["metadata_id"], seconds, raw_before),
                        )
                    dst.execute("UPDATE statistics_meta SET unit_of_measurement='°' WHERE id=?", (item["metadata_id"],))
                dst.execute("CREATE TABLE gardena_angle_migration (report TEXT NOT NULL)")
                dst.execute("INSERT INTO gardena_angle_migration VALUES (?)", (json.dumps({
                    "raw_before": raw_before, "degrees_from": degrees_from, "plan": plan,
                }),))
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Repaired copy failed integrity check; do not install it")
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--statistic-id", action="append", required=True)
    parser.add_argument("--raw-before", type=timestamp, required=True)
    parser.add_argument("--degrees-from", type=timestamp, required=True)
    parser.add_argument("--output", type=Path, help="Create a new repaired offline copy; omitted means read-only dry run")
    args = parser.parse_args()
    if args.output:
        plan = repair_copy(args.database, args.output, args.statistic_id, args.raw_before, args.degrees_from)
    else:
        with sqlite3.connect(f"{args.database.resolve().as_uri()}?mode=ro", uri=True) as connection:
            plan = inspect(connection, args.statistic_id, args.raw_before, args.degrees_from)
    print(json.dumps({"source_changed": False, "output": str(args.output) if args.output else None, "plan": plan}, indent=2))


if __name__ == "__main__":
    main()
