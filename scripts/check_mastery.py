from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.core.config import get_settings
from app.services.mastery_tracker import MasteryTracker


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect student mastery records in Supabase.")
    parser.add_argument("--student-id", type=UUID, help="Filter to a single student UUID.")
    parser.add_argument("--skill-id", help="Filter to a specific skill ID.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum rows to return when listing records.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.skill_id and args.student_id is None:
        raise SystemExit("--skill-id requires --student-id so the lookup stays specific.")

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("Set MWP_SUPABASE_URL and MWP_SUPABASE_SERVICE_KEY before checking mastery.")

    tracker = MasteryTracker(settings.supabase_url, settings.supabase_service_key)

    if args.student_id and args.skill_id:
        record = tracker.get_mastery_record(args.student_id, args.skill_id)
        if record is None:
            print("No mastery record found.")
            return
        print(json.dumps(record, indent=2, sort_keys=True))
        return

    records = tracker.list_mastery_records(
        student_id=args.student_id,
        limit=args.limit,
    )
    if not records:
        print("No mastery records found.")
        return
    print(json.dumps(records, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
