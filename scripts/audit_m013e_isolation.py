from __future__ import annotations

from m013e_eval_support import source_isolation_audit


def main() -> None:
    result = source_isolation_audit()
    if not result["passed"] or result["runtime_nonce_calls_in_runner"] != 1:
        raise SystemExit(f"M013e isolation audit failed: {result}")
    print(result)


if __name__ == "__main__":
    main()
