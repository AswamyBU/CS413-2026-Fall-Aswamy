"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const m = require("../lambda1_vp.js");
const cases = require("../../TEST/cases.json");

function expression([kind, ...args]) {
    args = kind === "int" ? [BigInt(args[0])]
        : args.map(a => Array.isArray(a) ? expression(a) : a);
    return new m[`D0E${kind}`](...args);
}

function value([kind, ...args]) {
    switch (kind) {
        case "unknown": return new m.D0V000();
        case "int": return new m.D0Vint(BigInt(args[0]));
        case "btf": return new m.D0Vbtf(args[0]);
        case "pair": return new m.D0Vpair(...args.map(value));
        default: throw new Error(`Unknown value kind: ${kind}`);
    }
}

for (const row of cases) {
    test(row.name, () => {
        const term = expression(row.expr);
        assert.deepEqual(m.d0exp_fvset(term), new Set(row.fv));
        if (row.error) {
            assert.throws(() => m.d0exp_evaluate(term),
                row.error === "division" ? RangeError : TypeError);
        } else if (row.value) {
            assert.deepEqual(m.d0exp_evaluate(term), value(row.value));
        }
    });
}

test("environment shadowing and immutability", () => {
    const tail = new m.ENVcns("x", new m.D0Vint(1), new m.ENVnil());
    const env = new m.ENVcns("x", new m.D0Vint(2), tail);
    assert.deepEqual(m.d0env_search(env, "x"), new m.D0Vint(2));
    assert.deepEqual(m.d0exp_evaluate(new m.D0Evar("x"), tail), new m.D0Vint(1));
    assert.deepEqual(m.d0env_search(env, "missing"), new m.D0V000());
    assert.throws(() => { env.arg1 = "y"; }, TypeError);
    assert(Object.isFrozen(tail.arg3));
});

test("visitors can be reused without scope leaks", () => {
    const visitor = new m.EvaluateVisitor(new m.ENVcns("x", new m.D0Vint(3), new m.ENVnil()));
    const term = new m.D0Elet("x", new m.D0Eint(8), new m.D0Evar("x"));
    assert.deepEqual(term.accept(visitor), new m.D0Vint(8));
    assert.deepEqual(new m.D0Evar("x").accept(visitor), new m.D0Vint(3));
    assert.deepEqual(new m.D0Evar("x").accept(new m.FreeVariableVisitor()), new Set(["x"]));
});

test("closures capture environment", () => {
    const env = new m.ENVcns("z", new m.D0Vint(4), new m.ENVnil());
    for (const [term, cls] of [
        [new m.D0Elam("x", new m.D0Evar("z")), m.D0Vlam],
        [new m.D0Efix("f", "x", new m.D0Evar("z")), m.D0Vfix],
    ]) {
        const closure = m.d0exp_evaluate(term, env);
        assert(closure instanceof cls);
        assert.equal(closure.arg1, env);
        assert.equal(closure.arg2, term);
    }
});

test("unsupported expression", () => {
    for (const operation of [m.d0exp_evaluate, m.d0exp_fvset]) {
        assert.throws(() => operation(new m.D0E000()), TypeError);
    }
});

test("integer constructors accept safe Numbers and BigInts only", () => {
    for (const cls of [m.D0Eint, m.D0Vint]) {
        assert.equal(new cls(42).arg1, 42n);
        assert.equal(new cls(12345678901234567890n).arg1, 12345678901234567890n);
        for (const bad of [Number.MAX_SAFE_INTEGER + 1, 1.5, NaN, Infinity, "42", true]) {
            assert.throws(() => new cls(bad), TypeError);
        }
    }
});

test("free-variable results do not share mutable state", () => {
    const term = new m.D0Evar("x");
    m.d0exp_fvset(term).add("extra");
    assert.deepEqual(m.d0exp_fvset(term), new Set(["x"]));
});
