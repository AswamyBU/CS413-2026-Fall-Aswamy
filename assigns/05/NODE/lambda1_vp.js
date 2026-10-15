"use strict";

// Visitor-based, closure-based, call-by-value LAMBDA interpreter.
// Node.js: const { D0Eint, d0exp_evaluate } = require("./lambda1_vp.js");
// Integer payloads use BigInt to preserve Python's arbitrary-precision integers.
// Constructors accept bigint or safe integer Numbers (e.g. new D0Eint(42)).
// Free-variable results are fresh JavaScript Sets; treat them as read-only.

function integer(value) {
    if (typeof value === "bigint") return value;
    if (typeof value === "number" && Number.isSafeInteger(value)) {
        return BigInt(value);
    }
    throw new TypeError("Expected a bigint or safe integer Number");
}

class D0E000 {
    static ctag = "D0E000";
    get ctag() { return this.constructor.ctag; }
    accept(visitor) {
        throw new TypeError(`unsupported expression ${this.constructor.name}`);
    }
}

class D0Eint extends D0E000 {
    static ctag = "D0Eint";
    constructor(arg1) {
        super();
        this.arg1 = integer(arg1);
    }
    accept(visitor) { return visitor.visit_int(this); }
}

class D0Ebtf extends D0E000 {
    static ctag = "D0Ebtf";
    constructor(arg1) {
        super();
        this.arg1 = arg1;
    }
    accept(visitor) { return visitor.visit_btf(this); }
}

class D0Eop1 extends D0E000 {
    static ctag = "D0Eop1";
    constructor(name, arg1) {
        super();
        this.name = name;
        this.arg1 = arg1;
    }
    accept(visitor) { return visitor.visit_op1(this); }
}

class D0Eop2 extends D0E000 {
    static ctag = "D0Eop2";
    constructor(name, arg1, arg2) {
        super();
        this.name = name;
        this.arg1 = arg1;
        this.arg2 = arg2;
    }
    accept(visitor) { return visitor.visit_op2(this); }
}

class D0Evar extends D0E000 {
    static ctag = "D0Evar";
    constructor(arg1) {
        super();
        this.arg1 = arg1;
    }
    accept(visitor) { return visitor.visit_var(this); }
}

class D0Elam extends D0E000 {
    static ctag = "D0Elam";
    constructor(arg1, arg2) {
        super();
        this.arg1 = arg1;
        this.arg2 = arg2;
    }
    accept(visitor) { return visitor.visit_lam(this); }
}

class D0Efix extends D0E000 {
    static ctag = "D0Efix";
    constructor(arg1, arg2, arg3) {
        super();
        this.arg1 = arg1;
        this.arg2 = arg2;
        this.arg3 = arg3;
    }
    accept(visitor) { return visitor.visit_fix(this); }
}

class D0Eapp extends D0E000 {
    static ctag = "D0Eapp";
    constructor(arg1, arg2) {
        super();
        this.arg1 = arg1;
        this.arg2 = arg2;
    }
    accept(visitor) { return visitor.visit_app(this); }
}

class D0Eif0 extends D0E000 {
    static ctag = "D0Eif0";
    constructor(arg1, arg2, arg3) {
        super();
        this.arg1 = arg1;
        this.arg2 = arg2;
        this.arg3 = arg3;
    }
    accept(visitor) { return visitor.visit_if0(this); }
}

class D0Elet extends D0E000 {
    static ctag = "D0Elet";
    constructor(arg1, arg2, arg3) {
        super();
        this.arg1 = arg1;
        this.arg2 = arg2;
        this.arg3 = arg3;
    }
    accept(visitor) { return visitor.visit_let(this); }
}

class D0Epair extends D0E000 {
    static ctag = "D0Epair";
    constructor(arg1, arg2) {
        super();
        this.arg1 = arg1;
        this.arg2 = arg2;
    }
    accept(visitor) { return visitor.visit_pair(this); }
}

class D0Epfst extends D0E000 {
    static ctag = "D0Epfst";
    constructor(arg1) {
        super();
        this.arg1 = arg1;
    }
    accept(visitor) { return visitor.visit_pfst(this); }
}

class D0Epsnd extends D0E000 {
    static ctag = "D0Epsnd";
    constructor(arg1) {
        super();
        this.arg1 = arg1;
    }
    accept(visitor) { return visitor.visit_psnd(this); }
}

class D0V000 {
    static ctag = "D0V000";
    get ctag() { return this.constructor.ctag; }
}

class ENV000 {
    static ctag = "ENV000";
    get ctag() { return this.constructor.ctag; }
    constructor() {
        if (new.target === ENV000) Object.freeze(this);
    }
}

class ENVnil extends ENV000 {
    constructor() {
        super();
        Object.freeze(this);
    }
}

class ENVcns extends ENV000 {
    static ctag = "ENVcns";
    constructor(arg1, arg2, arg3) {
        super();
        this.arg1 = arg1;
        this.arg2 = arg2;
        this.arg3 = arg3;
        Object.freeze(this);
    }
}

class D0Vint extends D0V000 {
    static ctag = "D0Vint";
    constructor(arg1) {
        super();
        this.arg1 = integer(arg1);
    }
}

class D0Vbtf extends D0V000 {
    static ctag = "D0Vbtf";
    constructor(arg1) {
        super();
        this.arg1 = arg1;
    }
}

class D0Vpair extends D0V000 {
    static ctag = "D0Vpair";
    constructor(arg1, arg2) {
        super();
        this.arg1 = arg1;
        this.arg2 = arg2;
    }
}

class D0Vlam extends D0V000 {
    static ctag = "D0Vlam";
    constructor(arg1, arg2) {
        super();
        this.arg1 = arg1;
        this.arg2 = arg2;
    }
}

class D0Vfix extends D0V000 {
    static ctag = "D0Vfix";
    constructor(arg1, arg2) {
        super();
        this.arg1 = arg1;
        this.arg2 = arg2;
    }
}

// Subclasses implement one method for each expression form.
class D0ExpVisitor {
    visit_int(dexp) { throw new Error("visit_int must be implemented"); }
    visit_btf(dexp) { throw new Error("visit_btf must be implemented"); }
    visit_op1(dexp) { throw new Error("visit_op1 must be implemented"); }
    visit_op2(dexp) { throw new Error("visit_op2 must be implemented"); }
    visit_var(dexp) { throw new Error("visit_var must be implemented"); }
    visit_lam(dexp) { throw new Error("visit_lam must be implemented"); }
    visit_fix(dexp) { throw new Error("visit_fix must be implemented"); }
    visit_app(dexp) { throw new Error("visit_app must be implemented"); }
    visit_if0(dexp) { throw new Error("visit_if0 must be implemented"); }
    visit_let(dexp) { throw new Error("visit_let must be implemented"); }
    visit_pair(dexp) { throw new Error("visit_pair must be implemented"); }
    visit_pfst(dexp) { throw new Error("visit_pfst must be implemented"); }
    visit_psnd(dexp) { throw new Error("visit_psnd must be implemented"); }
}

function union(...sets) {
    const result = new Set();
    for (const set of sets) for (const name of set) result.add(name);
    return result;
}

function without(set, ...names) {
    const result = new Set(set);
    for (const name of names) result.delete(name);
    return result;
}

class FreeVariableVisitor extends D0ExpVisitor {
    visit_int(dexp) { return new Set(); }
    visit_btf(dexp) { return new Set(); }
    visit_var(dexp) { return new Set([dexp.arg1]); }
    visit_lam(dexp) {
        return without(dexp.arg2.accept(this), dexp.arg1);
    }
    visit_fix(dexp) {
        return without(dexp.arg3.accept(this), dexp.arg1, dexp.arg2);
    }
    visit_let(dexp) {
        // The name is bound in the body, but not in the initializer.
        return union(dexp.arg2.accept(this),
                     without(dexp.arg3.accept(this), dexp.arg1));
    }
    visit_if0(dexp) {
        return union(dexp.arg1.accept(this), dexp.arg2.accept(this),
                     dexp.arg3.accept(this));
    }
    visit_op1(dexp) { return dexp.arg1.accept(this); }
    visit_pfst(dexp) { return dexp.arg1.accept(this); }
    visit_psnd(dexp) { return dexp.arg1.accept(this); }
    visit_op2(dexp) { return union(dexp.arg1.accept(this), dexp.arg2.accept(this)); }
    visit_app(dexp) { return union(dexp.arg1.accept(this), dexp.arg2.accept(this)); }
    visit_pair(dexp) { return union(dexp.arg1.accept(this), dexp.arg2.accept(this)); }
}

function d0exp_fvset(dexp) {
    return dexp.accept(new FreeVariableVisitor());
}

function d0env_search(denv, dvar) {
    while (denv instanceof ENVcns) {
        if (dvar === denv.arg1) return denv.arg2;
        denv = denv.arg3;
    }
    return new D0V000(); // Original unbound-variable error sentinel.
}

// BigInt division truncates toward zero; Python // rounds toward -infinity.
function floorDivide(left, right) {
    if (right === 0n) throw new RangeError("integer division by zero");
    const quotient = left / right;
    return left % right !== 0n && (left < 0n) !== (right < 0n)
        ? quotient - 1n : quotient;
}

class EvaluateVisitor extends D0ExpVisitor {
    constructor(denv = new ENVnil()) {
        super();
        this.denv = denv;
    }
    visit_int(dexp) { return new D0Vint(dexp.arg1); }
    visit_btf(dexp) { return new D0Vbtf(dexp.arg1); }
    visit_var(dexp) { return d0env_search(this.denv, dexp.arg1); }
    visit_lam(dexp) { return new D0Vlam(this.denv, dexp); }
    visit_fix(dexp) { return new D0Vfix(this.denv, dexp); }

    visit_app(dexp) {
        const dfun = dexp.arg1.accept(this);
        const darg = dexp.arg2.accept(this);
        // Apply using the closure's defining environment.
        if (dfun instanceof D0Vlam) {
            const dlam = dfun.arg2;
            const denv = new ENVcns(dlam.arg1, darg, dfun.arg1);
            return dlam.arg2.accept(new EvaluateVisitor(denv));
        } else if (dfun instanceof D0Vfix) {
            const dfix = dfun.arg2;
            const selfEnv = new ENVcns(dfix.arg1, dfun, dfun.arg1);
            const denv = new ENVcns(dfix.arg2, darg, selfEnv);
            return dfix.arg3.accept(new EvaluateVisitor(denv));
        }
        throw new TypeError("visit_app: not D0Vlam/D0Vfix");
    }
    visit_if0(dexp) {
        const cond = dexp.arg1.accept(this);
        if (!(cond instanceof D0Vbtf)) throw new TypeError("D0Vbtf(...) expected");
        return (cond.arg1 ? dexp.arg2 : dexp.arg3).accept(this);
    }
    visit_let(dexp) {
        const value = dexp.arg2.accept(this);
        const denv = new ENVcns(dexp.arg1, value, this.denv);
        return dexp.arg3.accept(new EvaluateVisitor(denv));
    }
    visit_pair(dexp) {
        const first = dexp.arg1.accept(this);
        const second = dexp.arg2.accept(this);
        return new D0Vpair(first, second);
    }
    visit_pfst(dexp) {
        const pair = dexp.arg1.accept(this);
        if (!(pair instanceof D0Vpair)) throw new TypeError("D0Vpair(...) expected");
        return pair.arg1;
    }
    visit_psnd(dexp) {
        const pair = dexp.arg1.accept(this);
        if (!(pair instanceof D0Vpair)) throw new TypeError("D0Vpair(...) expected");
        return pair.arg2;
    }
    visit_op1(dexp) {
        const value = dexp.arg1.accept(this);
        if (!["+1", "-1"].includes(dexp.name)) {
            throw new TypeError("visit_op1: not supported op1");
        }
        if (!(value instanceof D0Vint)) throw new TypeError("D0Vint(...) expected");
        return new D0Vint(value.arg1 + (dexp.name === "+1" ? 1n : -1n));
    }
    visit_op2(dexp) {
        const left = dexp.arg1.accept(this);
        const right = dexp.arg2.accept(this);
        if (!["+", "-", "*", "/", "<", ">", "<=", ">=", "==", "!="].includes(dexp.name)) {
            throw new TypeError("visit_op2: not supported op2");
        }
        if (!(left instanceof D0Vint) || !(right instanceof D0Vint)) {
            throw new TypeError("D0Vint(...) expected");
        }
        switch (dexp.name) {
            case "+": return new D0Vint(left.arg1 + right.arg1);
            case "-": return new D0Vint(left.arg1 - right.arg1);
            case "*": return new D0Vint(left.arg1 * right.arg1);
            case "/": return new D0Vint(floorDivide(left.arg1, right.arg1));
            case "<": return new D0Vbtf(left.arg1 < right.arg1);
            case ">": return new D0Vbtf(left.arg1 > right.arg1);
            case "<=": return new D0Vbtf(left.arg1 <= right.arg1);
            case ">=": return new D0Vbtf(left.arg1 >= right.arg1);
            case "==": return new D0Vbtf(left.arg1 === right.arg1);
            case "!=": return new D0Vbtf(left.arg1 !== right.arg1);
        }
    }
}

function d0exp_evaluate(dexp, denv = new ENVnil()) {
    return dexp.accept(new EvaluateVisitor(denv));
}

// CommonJS exports; the file can also be loaded as a browser classic script.
if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        D0E000, D0Eint, D0Ebtf, D0Eop1,
        D0Eop2, D0Evar, D0Elam, D0Efix,
        D0Eapp, D0Eif0, D0Elet, D0Epair,
        D0Epfst, D0Epsnd, D0V000, D0Vint,
        D0Vbtf, D0Vpair, D0Vlam, D0Vfix,
        ENV000, ENVnil, ENVcns, D0ExpVisitor,
        FreeVariableVisitor, EvaluateVisitor, d0exp_fvset, d0env_search,
        d0exp_evaluate,
    };
}
