import java.math.BigInteger;
import java.util.HashSet;
import java.util.Set;

/**
 * Direct translation of lambda1.py (Java 17+).
 * Closure-based, lexically scoped, left-to-right call-by-value evaluation.
 * Expressions are dispatched with instanceof, as in the Python source.
 * Integer payloads use BigInteger; convenience constructors accept long.
 * TypeError maps to IllegalArgumentException; division by zero to ArithmeticException.
 * Example: Lambda1.d0exp_evaluate(new Lambda1.D0Eint(42)).
 */
public final class Lambda1 {
    private Lambda1() {}

    public static class D0E000 {
        public static final String ctag = "D0E000";
        public D0E000() {
        }
    }

    public static class D0Eint extends D0E000 {
        public static final String ctag = "D0Eint";
        public BigInteger arg1;
        public D0Eint(BigInteger arg1) {
            this.arg1 = arg1;
        }
        public D0Eint(long arg1) { this(BigInteger.valueOf(arg1)); }
    }

    public static class D0Ebtf extends D0E000 {
        public static final String ctag = "D0Ebtf";
        public boolean arg1;
        public D0Ebtf(boolean arg1) {
            this.arg1 = arg1;
        }
    }

    public static class D0Eop1 extends D0E000 {
        public static final String ctag = "D0Eop1";
        public String name;
        public D0E000 arg1;
        public D0Eop1(String name, D0E000 arg1) {
            this.name = name;
            this.arg1 = arg1;
        }
    }

    public static class D0Eop2 extends D0E000 {
        public static final String ctag = "D0Eop2";
        public String name;
        public D0E000 arg1;
        public D0E000 arg2;
        public D0Eop2(String name, D0E000 arg1, D0E000 arg2) {
            this.name = name;
            this.arg1 = arg1;
            this.arg2 = arg2;
        }
    }

    public static class D0Evar extends D0E000 {
        public static final String ctag = "D0Evar";
        public String arg1;
        public D0Evar(String arg1) {
            this.arg1 = arg1;
        }
    }

    public static class D0Elam extends D0E000 {
        public static final String ctag = "D0Elam";
        public String arg1;
        public D0E000 arg2;
        public D0Elam(String arg1, D0E000 arg2) {
            this.arg1 = arg1;
            this.arg2 = arg2;
        }
    }

    public static class D0Efix extends D0E000 {
        public static final String ctag = "D0Efix";
        public String arg1;
        public String arg2;
        public D0E000 arg3;
        public D0Efix(String arg1, String arg2, D0E000 arg3) {
            this.arg1 = arg1;
            this.arg2 = arg2;
            this.arg3 = arg3;
        }
    }

    public static class D0Eapp extends D0E000 {
        public static final String ctag = "D0Eapp";
        public D0E000 arg1;
        public D0E000 arg2;
        public D0Eapp(D0E000 arg1, D0E000 arg2) {
            this.arg1 = arg1;
            this.arg2 = arg2;
        }
    }

    public static class D0Eif0 extends D0E000 {
        public static final String ctag = "D0Eif0";
        public D0E000 arg1;
        public D0E000 arg2;
        public D0E000 arg3;
        public D0Eif0(D0E000 arg1, D0E000 arg2, D0E000 arg3) {
            this.arg1 = arg1;
            this.arg2 = arg2;
            this.arg3 = arg3;
        }
    }

    public static class D0Elet extends D0E000 {
        public static final String ctag = "D0Elet";
        public String arg1;
        public D0E000 arg2;
        public D0E000 arg3;
        public D0Elet(String arg1, D0E000 arg2, D0E000 arg3) {
            this.arg1 = arg1;
            this.arg2 = arg2;
            this.arg3 = arg3;
        }
    }

    public static class D0Epair extends D0E000 {
        public static final String ctag = "D0Epair";
        public D0E000 arg1;
        public D0E000 arg2;
        public D0Epair(D0E000 arg1, D0E000 arg2) {
            this.arg1 = arg1;
            this.arg2 = arg2;
        }
    }

    public static class D0Epfst extends D0E000 {
        public static final String ctag = "D0Epfst";
        public D0E000 arg1;
        public D0Epfst(D0E000 arg1) {
            this.arg1 = arg1;
        }
    }

    public static class D0Epsnd extends D0E000 {
        public static final String ctag = "D0Epsnd";
        public D0E000 arg1;
        public D0Epsnd(D0E000 arg1) {
            this.arg1 = arg1;
        }
    }

    public static class D0V000 {
        public static final String ctag = "D0V000";
        public D0V000() {
        }
    }

    public static class ENV000 {
        public static final String ctag = "ENV000";
        public ENV000() {
        }
    }

    public static class ENVnil extends ENV000 {
        public ENVnil() {
        }
    }

    public static class ENVcns extends ENV000 {
        public static final String ctag = "ENVcns";
        public final String arg1;
        public final D0V000 arg2;
        public final ENV000 arg3;
        public ENVcns(String arg1, D0V000 arg2, ENV000 arg3) {
            this.arg1 = arg1;
            this.arg2 = arg2;
            this.arg3 = arg3;
        }
    }

    public static class D0Vint extends D0V000 {
        public static final String ctag = "D0Vint";
        public BigInteger arg1;
        public D0Vint(BigInteger arg1) {
            this.arg1 = arg1;
        }
        public D0Vint(long arg1) { this(BigInteger.valueOf(arg1)); }
    }

    public static class D0Vbtf extends D0V000 {
        public static final String ctag = "D0Vbtf";
        public boolean arg1;
        public D0Vbtf(boolean arg1) {
            this.arg1 = arg1;
        }
    }

    public static class D0Vpair extends D0V000 {
        public static final String ctag = "D0Vpair";
        public D0V000 arg1;
        public D0V000 arg2;
        public D0Vpair(D0V000 arg1, D0V000 arg2) {
            this.arg1 = arg1;
            this.arg2 = arg2;
        }
    }

    public static class D0Vlam extends D0V000 {
        public static final String ctag = "D0Vlam";
        public ENV000 arg1;
        public D0Elam arg2;
        public D0Vlam(ENV000 arg1, D0Elam arg2) {
            this.arg1 = arg1;
            this.arg2 = arg2;
        }
    }

    public static class D0Vfix extends D0V000 {
        public static final String ctag = "D0Vfix";
        public ENV000 arg1;
        public D0Efix arg2;
        public D0Vfix(ENV000 arg1, D0Efix arg2) {
            this.arg1 = arg1;
            this.arg2 = arg2;
        }
    }

    /** Return an immutable set of free variable names, without evaluation. */
    public static Set<String> d0exp_fvset(D0E000 dexp) {
        if (dexp instanceof D0Eint || dexp instanceof D0Ebtf) return Set.of();
        if (dexp instanceof D0Evar e) return Set.of(e.arg1);
        if (dexp instanceof D0Elam e) return without(d0exp_fvset(e.arg2), e.arg1);
        if (dexp instanceof D0Efix e) return without(d0exp_fvset(e.arg3), e.arg1, e.arg2);
        if (dexp instanceof D0Elet e) {
            return union(d0exp_fvset(e.arg2), without(d0exp_fvset(e.arg3), e.arg1));
        }
        if (dexp instanceof D0Eop1 e) return d0exp_fvset(e.arg1);
        if (dexp instanceof D0Epfst e) return d0exp_fvset(e.arg1);
        if (dexp instanceof D0Epsnd e) return d0exp_fvset(e.arg1);
        if (dexp instanceof D0Eop2 e) return union(d0exp_fvset(e.arg1), d0exp_fvset(e.arg2));
        if (dexp instanceof D0Eapp e) return union(d0exp_fvset(e.arg1), d0exp_fvset(e.arg2));
        if (dexp instanceof D0Epair e) return union(d0exp_fvset(e.arg1), d0exp_fvset(e.arg2));
        if (dexp instanceof D0Eif0 e) {
            return union(union(d0exp_fvset(e.arg1), d0exp_fvset(e.arg2)), d0exp_fvset(e.arg3));
        }
        throw new IllegalArgumentException("d0exp_fvset: unsupported expression");
    }

    private static Set<String> union(Set<String> left, Set<String> right) {
        Set<String> result = new HashSet<>(left);
        result.addAll(right);
        return Set.copyOf(result);
    }

    private static Set<String> without(Set<String> names, String... bound) {
        Set<String> result = new HashSet<>(names);
        for (String name : bound) result.remove(name);
        return Set.copyOf(result);
    }

    public static D0V000 d0env_search(ENV000 denv, String dvar) {
        while (denv instanceof ENVcns env) {
            if (dvar.equals(env.arg1)) return env.arg2;
            denv = env.arg3;
        }
        return new D0V000(); // Preserve the original error sentinel.
    }

    public static D0V000 d0exp_evaluate(D0E000 dexp) {
        return d0exp_evaluate(dexp, new ENVnil());
    }

    /** Evaluate with bindings for any free variables in dexp. */
    public static D0V000 d0exp_evaluate(D0E000 dexp, ENV000 denv) {
        if (dexp instanceof D0Eint e) return new D0Vint(e.arg1);
        if (dexp instanceof D0Ebtf e) return new D0Vbtf(e.arg1);
        if (dexp instanceof D0Elam e) return new D0Vlam(denv, e);
        if (dexp instanceof D0Efix e) return new D0Vfix(denv, e);
        if (dexp instanceof D0Eif0 e) return f0_D0Eif0(e, denv);
        if (dexp instanceof D0Elet e) return f0_D0Elet(e, denv);
        if (dexp instanceof D0Eop1 e) return f0_D0Eop1(e, denv);
        if (dexp instanceof D0Eop2 e) return f0_D0Eop2(e, denv);
        if (dexp instanceof D0Evar e) return d0env_search(denv, e.arg1);
        if (dexp instanceof D0Eapp e) return f0_D0Eapp(e, denv);
        if (dexp instanceof D0Epair e) {
            D0V000 first = d0exp_evaluate(e.arg1, denv);
            D0V000 second = d0exp_evaluate(e.arg2, denv);
            return new D0Vpair(first, second);
        }
        if (dexp instanceof D0Epfst e) {
            D0V000 value = d0exp_evaluate(e.arg1, denv);
            if (!(value instanceof D0Vpair pair)) throw new IllegalArgumentException("D0Vpair expected");
            return pair.arg1;
        }
        if (dexp instanceof D0Epsnd e) {
            D0V000 value = d0exp_evaluate(e.arg1, denv);
            if (!(value instanceof D0Vpair pair)) throw new IllegalArgumentException("D0Vpair expected");
            return pair.arg2;
        }
        throw new IllegalArgumentException("d0exp_evaluate: unsupported expression");
    }

    private static D0V000 f0_D0Eif0(D0Eif0 e, ENV000 denv) {
        D0V000 value = d0exp_evaluate(e.arg1, denv);
        if (!(value instanceof D0Vbtf cond)) throw new IllegalArgumentException("D0Vbtf expected");
        return d0exp_evaluate(cond.arg1 ? e.arg2 : e.arg3, denv);
    }

    private static D0V000 f0_D0Elet(D0Elet e, ENV000 denv) {
        D0V000 value = d0exp_evaluate(e.arg2, denv);
        return d0exp_evaluate(e.arg3, new ENVcns(e.arg1, value, denv));
    }

    private static D0V000 f0_D0Eapp(D0Eapp e, ENV000 denv) {
        D0V000 dfun = d0exp_evaluate(e.arg1, denv);
        D0V000 darg = d0exp_evaluate(e.arg2, denv);
        if (dfun instanceof D0Vlam closure) {
            D0Elam lam = closure.arg2;
            return d0exp_evaluate(lam.arg2, new ENVcns(lam.arg1, darg, closure.arg1));
        }
        if (dfun instanceof D0Vfix closure) {
            D0Efix fix = closure.arg2;
            ENV000 selfEnv = new ENVcns(fix.arg1, dfun, closure.arg1);
            ENV000 argEnv = new ENVcns(fix.arg2, darg, selfEnv);
            return d0exp_evaluate(fix.arg3, argEnv);
        }
        throw new IllegalArgumentException("f0_D0Eapp: not D0Vlam/D0Vfix");
    }

    private static BigInteger integer(D0V000 value) {
        if (value instanceof D0Vint number) return number.arg1;
        throw new IllegalArgumentException("D0Vint expected");
    }

    private static D0V000 f0_D0Eop1(D0Eop1 e, ENV000 denv) {
        D0V000 value = d0exp_evaluate(e.arg1, denv);
        return switch (e.name) {
            case "+1" -> new D0Vint(integer(value).add(BigInteger.ONE));
            case "-1" -> new D0Vint(integer(value).subtract(BigInteger.ONE));
            default -> throw new IllegalArgumentException("f0_D0Eop1: not supported op1");
        };
    }

    private static D0V000 f0_D0Eop2(D0Eop2 e, ENV000 denv) {
        D0V000 left = d0exp_evaluate(e.arg1, denv);
        D0V000 right = d0exp_evaluate(e.arg2, denv);
        if (!Set.of("+", "-", "*", "/", "<", ">", "<=", ">=", "==", "!=").contains(e.name)) {
            throw new IllegalArgumentException("f0_D0Eop2: not supported op2");
        }
        BigInteger a = integer(left);
        BigInteger b = integer(right);
        return switch (e.name) {
            case "+" -> new D0Vint(a.add(b));
            case "-" -> new D0Vint(a.subtract(b));
            case "*" -> new D0Vint(a.multiply(b));
            case "/" -> new D0Vint(floorDivide(a, b));
            case "<" -> new D0Vbtf(a.compareTo(b) < 0);
            case ">" -> new D0Vbtf(a.compareTo(b) > 0);
            case "<=" -> new D0Vbtf(a.compareTo(b) <= 0);
            case ">=" -> new D0Vbtf(a.compareTo(b) >= 0);
            case "==" -> new D0Vbtf(a.equals(b));
            case "!=" -> new D0Vbtf(!a.equals(b));
            default -> throw new IllegalArgumentException("f0_D0Eop2: not supported op2");
        };
    }

    // BigInteger divides toward zero; Python // divides toward negative infinity.
    private static BigInteger floorDivide(BigInteger a, BigInteger b) {
        BigInteger[] qr = a.divideAndRemainder(b);
        return qr[1].signum() != 0 && a.signum() != b.signum()
            ? qr[0].subtract(BigInteger.ONE) : qr[0];
    }
}
