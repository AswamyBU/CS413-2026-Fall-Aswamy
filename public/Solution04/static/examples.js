/* Bundled examples for the static browser application. */
globalThis.LambdaExamples = {
  "Arithmetic": "# A small beginning → 42\nD0Eop2(\"+\", D0Eint(20), D0Eint(22))\n",
  "Factorial": "# Factorial of 5 → 120\nD0Eapp(\n    D0Efix(\"fact\", \"n\",\n        D0Eif0(\n            D0Eop2(\"<=\", D0Evar(\"n\"), D0Eint(1)),\n            D0Eint(1),\n            D0Eop2(\"*\", D0Evar(\"n\"),\n                D0Eapp(D0Evar(\"fact\"),\n                    D0Eop2(\"-\", D0Evar(\"n\"), D0Eint(1)))))),\n    D0Eint(5))\n",
  "Fibonacci": "# Fibonacci of 10 → 55\nD0Eapp(\n    D0Efix(\"fib\", \"n\",\n        D0Eif0(\n            D0Eop2(\"<=\", D0Evar(\"n\"), D0Eint(1)),\n            D0Evar(\"n\"),\n            D0Eop2(\"+\",\n                D0Eapp(D0Evar(\"fib\"), D0Eop2(\"-\", D0Evar(\"n\"), D0Eint(1))),\n                D0Eapp(D0Evar(\"fib\"), D0Eop2(\"-\", D0Evar(\"n\"), D0Eint(2)))))),\n    D0Eint(10))\n",
  "Runtime-error": "# Closed, but not safe to evaluate: Lint passes; Interpret fails.\nD0Eop2(\"/\", D0Eint(1), D0Eint(0))\n",
  "Undeclared": "D0Evar(\"x\")\n"
};
