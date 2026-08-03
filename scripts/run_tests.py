from __future__ import annotations

from _runtime import fail, run_in_venv


def main() -> int:
    try:
        test_status = run_in_venv(["-m", "pytest", "-q"])
        if test_status != 0:
            return test_status
        return run_in_venv(["-m", "compileall", "-q", "data_generator/src", "scripts"])
    except RuntimeError as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
