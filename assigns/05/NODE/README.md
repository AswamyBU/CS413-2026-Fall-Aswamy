# JavaScript visitor interpreter

`lambda1_vp.js` implements the closure-based, call-by-value interpreter using
expression visitors. It exports the expression classes, value classes,
environments, visitors, and interpreter functions through CommonJS.

From this directory:

```js
const { D0Eint, d0exp_evaluate } = require("./lambda1_vp.js");
console.log(d0exp_evaluate(new D0Eint(42)).arg1); // 42n
```

Run tests from the assignment directory (Node.js 18+, no external dependencies):

```sh
make -C NODE/TEST test
```

Or run `make test` inside `NODE/TEST`. The tests use the shared
`../TEST/cases.json` fixture, located outside `NODE`, for the same behavioral
examples as the Python tests. Run the Python suite separately with
`make -C TEST test`.
