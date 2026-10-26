# DESIGN: Compiling Extended LAMBDA into Pure Lambda-Calculus

## 1. Architecture

```text
 source AST (lambda1_vp.py, unchanged)
        │
        ▼
 compiler.py ── CompileVisitor (D0ExpVisitor) ──uses──▶ church.py (closed combinators)
        │                                                      │
        ▼                                                      ▼
 target.py ── Term = Var | Lam | App, show, fv, substitute, alpha_equiv
        │
        ▼
 evaluator.py ── one CBV machine for source ASTs *and* target terms
        │
        ▼
 observe.py ── NAT / BOOL / pair observers ──▶ pipeline.py ──▶ demo.py
```

| Module | Interface |
| --- | --- |
| `target.py` | `Var`, `Lam`, `App`; `show(t)`, `free_vars(t)`, `all_names(t)`, `substitute(t, x, r)`, `alpha_equiv(a, b)`, `is_pure(t)`, `fresh_name(base, avoid)` |
| `church.py` | Closed terms `TRUE FALSE I NUM(n) SUCC PRED IS_ZERO ADD SUB MUL NOT AND OR LT LEQ GT GEQ EQ NEQ PAIR FST SND Z`; `LIBRARY` |
| `source_syntax.py` | Imports the supplied AST; `pretty`, `source_substitute`, `source_value_to_python` |
| `compiler.py` | `compile_expr(source) -> Term`; raises `CompileError` |
| `evaluator.py` | `evaluate(expr, budget=None, *, trace=None) -> EvalResult(status, value, steps, budget)`; raises `EvalError` |
| `observe.py` | `observe(value, kind, budget) -> Observation(status, value, steps, detail)`; kinds `NAT`, `BOOL`, `pair_kind(k1, k2)` |
| `pipeline.py` | `run_program(source, kind, exec_budget, obs_budget) -> RunReport`; `source_result(source)` |

The compiler and the evaluator never import each other. They only meet in
`pipeline.py`, so compilation can't quietly run the program.

## 2. Translation rules

`C[e]` means "the translation of `e`". Writing several arguments at once is
shorthand for nested one-argument lambdas and applications. Capitalized names
are closed terms from the Church library (section 3), written out in full in
the output.

```text
C[n]                    = NUM(n) = lam s. lam z. s (... (s z))      n >= 0
C[true]                 = TRUE   = lam t. lam f. t
C[false]                = FALSE  = lam t. lam f. f
C[x]                    = x
C[lam x. e]             = lam x. C[e]
C[e1 e2]                = C[e1] C[e2]
C[let x = e1 in e2]     = (lam x. C[e2]) C[e1]
C[if c then t else f]   = (C[c] (lam u. C[t]) (lam v. C[f])) I
C[fix f(x). e]          = Z (lam f. lam x. C[e])
C[pair e1 e2]           = PAIR C[e1] C[e2]
C[fst e]                = FST C[e]
C[snd e]                = SND C[e]
C[not e]                = NOT C[e]
C[e1 and e2]            = (C[e1] (lam u. C[e2]) (lam v. FALSE)) I
C[e1 or e2]             = (C[e1] (lam u. TRUE) (lam v. C[e2])) I
C[e1 + e2]              = ADD C[e1] C[e2]
C[e1 - e2]              = SUB C[e1] C[e2]
C[e1 * e2]              = MUL C[e1] C[e2]
C[e1 < e2]              = LT  C[e1] C[e2]
C[e1 <= e2]             = LEQ C[e1] C[e2]
C[e1 > e2]              = GT  C[e1] C[e2]
C[e1 >= e2]             = GEQ C[e1] C[e2]
C[e1 == e2]             = EQ  C[e1] C[e2]
C[e1 != e2]             = NEQ C[e1] C[e2]
C[n], n < 0             = CompileError("unsupported negative integer literal n")
C[op ...], op unknown   = CompileError("unsupported unary/binary operator 'op'")
```

Here `u` and `v` are thunk parameters, picked fresh by the rule in section 4,
and `I` is the identity function `lam w. w`.

## 3. Church encodings

```text
TRUE    = lam t. lam f. t                FALSE = lam t. lam f. f
I       = lam w. w
NOT     = lam b. b FALSE TRUE
AND     = lam p. lam q. p q FALSE        OR    = lam p. lam q. p TRUE q
PAIR    = lam a. lam b. lam p. p a b
FST     = lam p. p TRUE                  SND   = lam p. p FALSE
SUCC    = lam n. lam s. lam z. s (n s z)
STEP'   = lam q. PAIR (SND q) (SUCC (SND q))
PRED    = lam n. FST (n STEP' (PAIR NUM(0) NUM(0)))
IS_ZERO = lam n. n (lam x. FALSE) TRUE
ADD     = lam m. lam n. lam s. lam z. m s (n s z)
SUB     = lam m. lam n. n PRED m
MUL     = lam m. lam n. lam s. m (n s)
LEQ     = lam m. lam n. IS_ZERO (SUB m n)
GEQ     = lam m. lam n. LEQ n m
LT      = lam m. lam n. NOT (LEQ n m)
GT      = lam m. lam n. NOT (LEQ m n)
EQ      = lam m. lam n. AND (LEQ m n) (LEQ n m)
NEQ     = lam m. lam n. NOT (EQ m n)
Z       = lam g. (lam x. g (lam v. x x v)) (lam x. g (lam v. x x v))
```

**Predecessor.** A Church numeral can apply a function n times, but it can't
"un-apply" one, so `PRED` counts up instead of down. It carries a pair of
(previous, current), starting at `(0, 0)`, and each step turns `(a, b)` into
`(b, b + 1)`: first `(0, 1)`, then `(1, 2)`, and after k steps `(k - 1, k)`.
The first number is always one behind, so after n steps it is n − 1. When n
is 0, no steps run and we get the 0 from `(0, 0)`, so `pred 0 = 0` needs no
special case. This is Kleene's trick (Pierce, *TAPL* §5.2; Wikipedia,
"Church encoding"), and under call-by-value it runs in linear time.

Subtraction `m - n` applies `PRED` to m, n times, so it stops at 0 on its
own, and every comparison comes down to whether `m - n` is zero. The
library's strict `AND` and `OR` are only used on values inside `EQ`; source
`and` and `or` must short-circuit, so they use thunks (section 2).

## 4. Naming policy

The encodings use names like `s`, `z`, `t`, and `f`, and so do ordinary
programs, so name capture was the bug I worried about most. Three rules
prevent it.

First, every library combinator is closed, and the compiler only applies
combinators to compiled code, never wrapping compiled code in their binders.
So their internal names can't capture anything, and programs can use those
names freely.

Second, source binders (`lam x`, `let x`, `fix f(x)`) are copied exactly as
written, so shadowing and `fix f(f)` behave just as in the source.

Third, the only binders the compiler adds around compiled code are thunk
parameters, and they are always fresh. A thunk around term `T` uses
`fresh_name(base, all_names(T))`: `u` for a then-branch or right operand, `v`
for an else-branch, or else the first of `base_1`, `base_2`, ... that doesn't
appear in `T`. A name that appears nowhere in `T` can't capture anything, and
because it depends only on `T`, the same program always compiles the same
way. For example, `if c then u else v v_1` compiles to
`(((c (lam u_1. u)) (lam v_2. (v v_1))) (lam w. w))`.

When substitution has to rename a binder, it reuses my Assignment 5 policy:
pick the first unused name among `y_1`, `y_2`, .... Together these rules
mean compiling never changes a program's free variables, `FV(C[e]) = FV(e)`,
which a randomized test checks on 400 open ASTs.

## 5. Evaluation strategy

The assignment asks for one evaluator for both languages, and I wanted that
to be literally true. The machine is a `D0ExpVisitor`, and I gave `Var`, `Lam`, and
`App` the same field layout (`arg1`, `arg2`) and the same `accept` method as
the source's `D0Evar`, `D0Elam`, and `D0Eapp`, so both languages go through
the same three methods (a test checks this). The other ten methods, like
`visit_int` and `visit_if0`, handle source-only constructs. A compiled term
never reaches them, so target execution never uses source operations or
knows about Church encodings.

Evaluation is weak, left-to-right call-by-value, done by substitution: the
machine evaluates the function, then the argument, then performs
`(lam x. b) v --> b[x := v]`, and never evaluates inside a lambda. It keeps
an explicit stack of pending work instead of recursing, so long runs can't
hit Python's recursion limit.

Each beta step checks the budget before it runs. If the count already
equals the budget, the result is `exhausted`. So a value finishes in zero
steps even with a budget of zero, and a value reached on the last allowed
step still counts as finished.

On the source side, values are ASTs too, substituted with my Assignment 5
code. Applying `fix f(x). e` to `v` gives `e[f := fix f(x). e][x := v]`; if
`f` and `x` are the same name, the `f` step is skipped so the parameter wins.
Type errors, unbound variables, unsupported operators, and running an open
target term all raise `EvalError`. Compiling open terms works fine.

**Observation.** Decoding has its own budget and step count. For a number
`n`, I run `n STEP BASE`, with `STEP = lam tail. lam c. lam z. c tail` and
`BASE = lam c. lam z. z`. Call-by-value turns each `s` into a `STEP` node,
building a finite chain whose links Python counts (up to renaming); any
other shape is `malformed`. A boolean is applied to two markers,
`lam p. lam q. lam r. p` and `lam p. lam q. lam r. q`, to see which comes
back. For a pair, I evaluate `FST p` and `SND p` and decode each part by its
own kind. Python only inspects the final shape and never does arithmetic.

## 6. Correctness argument

**Claim.** Take a closed, well-typed source program `e`, and suppose it
evaluates to a natural number, a boolean, or a finite pair of those. Then
running `C[e]` and observing the result with the matching kind gives the
same answer, as long as the budgets are large enough.

**Representations.** A number `n` is any closed lambda that observes as `n`.
A boolean picks its first or second argument, a pair is `lam p. p V1 V2`
with represented parts, and a function maps represented arguments to
represented results. Compiled values and thunks are all lambdas, so they
are all target values.

**Application.** `C[e1 e2]` is just `C[e1] C[e2]`, which the machine
evaluates function first, then argument, then substitutes, exactly like the
source. Since the only added binders are fresh thunks and substitution
avoids capture, plugging a compiled value into `C[b]` behaves like compiling
`b[x := v]`. **Let** is the same argument, because it compiles to
`(lam x. C[e2]) C[e1]`, and `x` isn't bound in the initializer.

**Conditional.** `C[c]` evaluates to a boolean `B`. Both thunks are lambdas,
so passing them to `B` runs nothing. `TRUE` returns `lam u. C[t]`, and
applying that to `I` gives exactly `C[t]` because `u` doesn't occur in it, so
only that branch runs. Without thunks, `TRUE C[t] C[f]` would evaluate both
branches as arguments, and `if true then 1 else LOOP` would never finish.
That is why branches must be delayed. `and` and `or` work the same way.

**Recursion.** Let `G = lam f. lam x. C[e]`. Then `Z G` steps to
`G (lam v. X X v)`, which is `lam x. C[e][f := F]` with `F = lam v. X X v`.
That is a lambda value, matching the source rule that `fix` is a value. When
`F` is applied to `a`, it unfolds once more, to `(lam x. C[e][f := F]) a`,
matching the source rule `e[f := fix f(x). e][x := a]`. The ordinary `Y`
combinator passes `x x` as an argument, which call-by-value evaluates before
`g` ever runs, so it loops forever (a test shows this). `Z` hides the
self-application behind `lam v`, so it only unfolds when called. When
`f == x`, `lam f. lam f. C[e]` lets the inner binder win, as specified.

**Arithmetic** follows from the standard Church-numeral identities in
section 3, since operands are always evaluated to numbers first.

**Why tests are not a proof.** The suite checks many programs, including 120
random ones compared against the source evaluator, but that is still a
finite set run within a budget. Running out of budget suggests a loop
without proving one. A real proof would use induction on evaluation plus a
substitution lemma for `C`; this section only sketches it.

## 7. Design tradeoffs

- **Substitution instead of environments.** The spec defines a beta step as
  substitution, so my machine does exactly that, which keeps step counts
  meaningful. To stay fast, nodes remember their free variables and
  `substitute` reuses any part of a term where `x` doesn't appear. Factorial 4
  takes 471 steps, Fibonacci 5 takes 2,021, and the demo runs in under a
  second.
- **One machine for two languages.** Copying the source field names
  (`Lam.arg1`) reads oddly, so I added aliases like `param` and `body`. In
  return, the variable, lambda, and application code is truly shared.
- **Simple but slow comparisons.** `EQ` is two `LEQ`s built on subtraction,
  costing about m × n steps. It's easy to check and fast enough here.
- **Lazy multiplication.** `MUL` returns `lam s. m (n s)` right away, so its
  work shows up during observation (218 steps for factorial).
- **Long printed terms.** The printed term spells out every combinator in
  full, so long terms are saved to `MySolution/generated/`.
- **Kinds instead of guessing.** `NUM(0)` and `FALSE` are the same term, so
  decoding always asks which kind to expect.
