"""고정 예제 하나를 실행하는 명령행 진입점. 대량 실험·선택기·UI 아님."""

import argparse
import json
from dataclasses import asdict

from .algorithms import ALGORITHMS
from .graph import build_warehouse
from .runner import run_request


def main() -> int:
    parser = argparse.ArgumentParser(description="단일 작업 피킹 경로 계산")
    parser.add_argument("--algorithm", choices=ALGORITHMS, default="nn")
    parser.add_argument("--coefficient", type=float, default=1.0)
    parser.add_argument("--budget-seconds", type=float, default=2.0)
    args = parser.parse_args()
    result = run_request(build_warehouse(), (0, 0),
                         [(0, 8), (8, 14), (20, 30), (32, 6), (36, 36)],
                         args.algorithm, budget_seconds=args.budget_seconds,
                         coefficient=args.coefficient)
    print(json.dumps(asdict(result), ensure_ascii=True, indent=2))
    return 0 if result.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
