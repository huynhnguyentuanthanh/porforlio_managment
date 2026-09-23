import argparse
import traceback

from collectors.imir import run_imir
from collectors.vn30 import run_vn30
from collectors.sjc import run_sjc
from collectors.yfinance_collector import run_yfinance_symbol, YFINANCE_TICKERS


CRAWL_TASKS = {
    "imir": run_imir,
    "vn30": run_vn30,
    "sjc": run_sjc,
}

ALL_CRAWL_TASK_NAMES = list(CRAWL_TASKS.keys())
ALL_TASK_NAMES = ALL_CRAWL_TASK_NAMES + list(YFINANCE_TICKERS.keys())


def build_parser():
    parser = argparse.ArgumentParser(description="Unified market collector")

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all crawl collectors only: imir, vn30, sjc"
    )

    parser.add_argument(
        "--only",
        nargs="+",
        help=f"Run only selected task names. Available: {', '.join(ALL_TASK_NAMES)}"
    )

    parser.add_argument(
        "--yfinance-mode",
        choices=["full", "incremental"],
        default="incremental",
        help="yfinance fetch mode: full history or incremental from last record date to today"
    )

    return parser


def resolve_tasks(args):
    if args.all and args.only:
        raise ValueError("Use either --all or --only, not both.")

    if args.yfinance_mode == "full" and args.all:
        raise ValueError(
            "--yfinance-mode full cannot be used with --all. "
            "Please specify exactly one yfinance ticker with --only."
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

    yfinance_selected = [name for name in selected if name in YFINANCE_TICKERS]

    if len(yfinance_selected) > 1:
        raise ValueError(
            "Run yfinance tickers one at a time to reduce HTTP 429 / rate-limit risk."
        )

    if args.yfinance_mode == "full":
        if len(yfinance_selected) != 1:
            raise ValueError(
                "--yfinance-mode full requires --only with exactly one explicit yfinance ticker."
            )

    return selected


def run_selected_tasks(task_names, yfinance_mode):
    success = []
    failed = []

    for name in task_names:
        print("=" * 80)
        print(f"Running task: {name}")

        try:
            if name in CRAWL_TASKS:
                CRAWL_TASKSname
            elif name in YFINANCE_TICKERS:
                run_yfinance_symbol(name, mode=yfinance_mode)
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
    run_selected_tasks(selected, yfinance_mode=args.yfinance_mode)


if __name__ == "__main__":
    main()
