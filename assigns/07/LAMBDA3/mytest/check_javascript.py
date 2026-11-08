"""Run each LAMBDA example through the JavaScript compiler and Node.js."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import lambda3 as L


def main() -> None:
    node = sys.argv[1] if len(sys.argv) > 1 else "node"
    if shutil.which(node) is None:
        raise SystemExit(f"Node.js executable not found: {node}")

    examples = sorted(Path(__file__).parent.glob("*.lam"))
    if not examples:
        raise SystemExit("No .lam examples found")

    with tempfile.TemporaryDirectory(prefix="lambda-js-") as temp_dir:
        for path in examples:
            expression, _ = L.d0exp_parse_and_typecheck(path.read_text())
            interpreted = L.d0exp_evaluate(expression)
            expected = L.d0val_format(interpreted)
            program = L.d0exp_compile_js(expression)
            # Observe lazy state before formatting the result. In particular,
            # eight_queens_stream.lam must compile to a stream value without
            # forcing its first cell and searching for a solution.
            program += (
                '\nconsole.log("LAMBDA_LAZY_EVALUATED:" + '
                '(_lambda_result && _lambda_result.tag === _lambda_lazy_tag '
                '? String(_lambda_result.evaluated) : "not-lazy"));\n'
            )
            program += '\nconsole.log("LAMBDA_RESULT:" + _lambda_format(_lambda_result));\n'
            js_path = Path(temp_dir) / f"{path.stem}.js"
            js_path.write_text(program)
            output = subprocess.check_output(
                [node, str(js_path)], text=True, cwd=Path(__file__).parent
            )
            results = [line.removeprefix("LAMBDA_RESULT:")
                       for line in output.splitlines()
                       if line.startswith("LAMBDA_RESULT:")]
            if not results:
                raise AssertionError(f"{path.name}: generated JavaScript produced no result")
            actual = results[-1]
            if actual != expected:
                raise AssertionError(
                    f"{path.name}: JavaScript result {actual} != interpreter result {expected}"
                )
            if isinstance(interpreted, L.D0Vlazy):
                lazy_states = [
                    line.removeprefix("LAMBDA_LAZY_EVALUATED:")
                    for line in output.splitlines()
                    if line.startswith("LAMBDA_LAZY_EVALUATED:")
                ]
                if lazy_states != ["false"]:
                    raise AssertionError(
                        f"{path.name}: expected an unforced lazy result, "
                        f"got {lazy_states or 'no lazy-state report'}"
                    )
            print(f"OK: {path.name} -> {actual}")


if __name__ == "__main__":
    main()
