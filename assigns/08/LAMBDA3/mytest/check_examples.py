"""Type-check and compare compiled results for each LAMBDA source example."""

from pathlib import Path

import lambda3 as L


def main() -> None:
    examples = sorted(Path(__file__).parent.glob("*.lam"))
    if not examples:
        raise SystemExit("No .lam examples found")

    for path in examples:
        source = path.read_text()
        expression, _ = L.d0exp_parse_and_typecheck(source)
        interpreted = L.d0exp_evaluate(expression)

        namespace: dict[str, object] = {}
        exec(L.d0exp_compile(expression), namespace)
        compiled = namespace["_lambda_result"]
        compiled_text = namespace["_lambda_format"](compiled)
        interpreted_text = L.d0val_format(interpreted)
        if compiled_text != interpreted_text:
            raise AssertionError(
                f"{path.name}: compiled result {compiled_text} != "
                f"interpreter result {interpreted_text}"
            )
        print(f"OK: {path.name} -> {compiled_text}")


if __name__ == "__main__":
    main()
