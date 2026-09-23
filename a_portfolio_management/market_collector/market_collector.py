import argparse
import traceback

from collectors.imir import run_imir
from collectors.vn30 import run_vn30
from collectors.sjc import run_sjc
from collectors.gold import run_gold
from collectors.fred_collector import run_fred_series, FRED_SERIES


CRAWL_TASKS = {
    "imir": run_imir,
    "vn30": run_vn30,
    "sjc": run_sjc,
    "gold": run_gold,
}

ALL_CRAWL_TASK_NAMES = list(CRAWL_TASKS.keys())
ALL_TASK_NAMES = ALL_CRAWL_TASK_NAMES + list(FRED_SERIES.keys())


def build_parser():
    parser = argparse.ArgumentParser(description="Unified market collector")

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all crawl collectors only: imir, vn30, sjc, gold"
    )

    parser.add_argument(
        "--only",
        nargs="+",
        help=f"Run only selected task names. Available: {', '.join(ALL_TASK_NAMES)}"
    )

    parser.add_argument(
        "--fred-mode",
        choices=["full", "incremental"],
        default="incremental",
        help="FRED fetch mode: full history or incremental from last record date to today"
    )

    return parser


def resolve_tasks(args):
    if args.all and args.only:
        raise ValueError("Use either --all or --only, not both.")

    if args.fred_mode == "full" and args.all:
        raise ValueError(
            "--fred-mode full cannot be used with --all. "
            "Please specify exactly one FRED series with --only."
        )

    if args.all:
        selected = ALL_CRAWL_TASK_NAMES
    elif args.only:
        selected = args.only
    else:
        selected = ALL_CRAWL_TASK_NAMES

    unknown = [name for name in selected if name not in ALL_TASK_NAMES]
    if unknown:
        raise ValueError(f"Unknown task names: {unknown}")

    fred_selected = [name for name in selected if name in FRED_SERIES]

    if args.fred_mode == "full":
        if len(fred_selected) != 1:
            raise ValueError(
                "--fred-mode full requires --only with exactly one explicit FRED series."
            )

    return selected


def run_selected_tasks(task_names, fred_mode):
    success = []
    failed = []

    for name in task_names:
        print("=" * 80)
        print(f"Running task: {name}")

        try:
            if name in CRAWL_TASKS:
                CRAWL_TASKS[name]()
            elif name in FRED_SERIES:
                run_fred_series(name, mode=fred_mode)
            else:
                raise ValueError(f"Task not configured: {name}")

            success.append(name)
            print(f"Task completed successfully: {name}")

        except Exception as e:
            failed.append(name)
            print(f"Task failed: {name}")
            print(f"Error: {e}")
            traceback.print_exc()

    print("=" * 80)
    print("Run summary")
    print(f"Successful tasks: {success}")
    print(f"Failed tasks: {failed}")


def main():
    parser = build_parser()
    args = parser.parse_args()

    selected = resolve_tasks(args)
    run_selected_tasks(selected, fred_mode=args.fred_mode)


if __name__ == "__main__":
    main()
