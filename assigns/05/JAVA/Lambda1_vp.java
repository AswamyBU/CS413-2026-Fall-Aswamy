import java.math.BigInteger;
import java.util.HashSet;
import java.util.Set;

/**
 * Visitor-pattern translation of lambda1_vp.py (Java 17+).
 * Closure-based, lexically scoped, left-to-right call-by-value evaluation.
 * Expressions dispatch through accept to generic visitors.
 * Integer payloads use BigInteger; convenience constructors accept long.
 * TypeError maps to IllegalArgumentException; division by zero to ArithmeticException.
 * Compile with javac Lambda1_vp.java.
 * Example: Lambda1_vp.d0exp_evaluate(new Lambda1_vp.D0Eint(42)).
 */
public final class Lambda1_vp {
    private Lambda1_vp() {}

    public static class D0E000 {
        public static final String ctag = "D0E000";
        public <R> R accept(D0ExpVisitor<R> visitor) {
            throw new IllegalArgumentException("unsupported expression " + getClass().getSimpleName());
        }
        public D0E000() {
        }
    }

    public static class D0Eint extends D0E000 {
        @Override
        public <R> R accept(D0ExpVisitor<R> visitor) {
            return visitor.visit_int(this);
        }
        public static final String ctag = "D0Eint";
        public BigInteger arg1;
        public D0Eint(BigInteger arg1) {
            this.arg1 = arg1;
        }
        public D0Eint(long arg1) { this(BigInteger.valueOf(arg1)); }
    }

    public static class D0Ebtf extends D0E000 {
        @Override
        public <R> R accept(D0ExpVisitor<R> visitor) {
            return visitor.visit_btf(this);
        }
        public static final String ctag = "D0Ebtf";
        public boolean arg1;
        public D0Ebtf(boolean arg1) {
            this.arg1 = arg1;
        }
    }

    public static class D0Eop1 extends D0E000 {
        @Override
        public <R> R accept(D0ExpVisitor<R> visitor) {
            return visitor.visit_op1(this);
        }
        public static final String ctag = "D0Eop1";
        public String name;
        public D0E000 arg1;
        public D0Eop1(String name, D0E000 arg1) {
            this.name = name;
            this.arg1 = arg1;
        }
    }

    public static class D0Eop2 extends D0E000 {
        @Override
        public <R> R accept(D0ExpVisitor<R> visitor) {
            return visitor.visit_op2(this);
        }
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
        @Override
        public <R> R accept(D0ExpVisitor<R> visitor) {
            return visitor.visit_var(this);
        }
        public static final String ctag = "D0Evar";
        public String arg1;
        public D0Evar(String arg1) {
            this.arg1 = arg1;
        }
    }

    public static class D0Elam extends D0E000 {
        @Override
        public <R> R accept(D0ExpVisitor<R> visitor) {
            return visitor.visit_lam(this);
        }
        public static final String ctag = "D0Elam";
        public String arg1;
        public D0E000 arg2;
        public D0Elam(String arg1, D0E000 arg2) {
            this.arg1 = arg1;
            this.arg2 = arg2;
        }
    }

    public static class D0Efix extends D0E000 {
        @Override
        public <R> R accept(D0ExpVisitor<R> visitor) {
            return visitor.visit_fix(this);
        }
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
        @Override
        public <R> R accept(D0ExpVisitor<R> visitor) {
            return visitor.visit_app(this);
        }
        public static final String ctag = "D0Eapp";
        public D0E000 arg1;
        public D0E000 arg2;
        public D0Eapp(D0E000 arg1, D0E000 arg2) {
            this.arg1 = arg1;
            this.arg2 = arg2;
        }
    }

    public static class D0Eif0 extends D0E000 {
        @Override
        public <R> R accept(D0ExpVisitor<R> visitor) {
            return visitor.visit_if0(this);
        }
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
        @Override
        public <R> R accept(D0ExpVisitor<R> visitor) {
            return visitor.visit_let(this);
        }
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
        @Override
        public <R> R accept(D0ExpVisitor<R> visitor) {
            return visitor.visit_pair(this);
        }
        public static final String ctag = "D0Epair";
        public D0E000 arg1;
        public D0E000 arg2;
        public D0Epair(D0E000 arg1, D0E000 arg2) {
            this.arg1 = arg1;
            this.arg2 = arg2;
        }
    }

    public static class D0Epfst extends D0E000 {
        @Override
        public <R> R accept(D0ExpVisitor<R> visitor) {
            return visitor.visit_pfst(this);
        }
        public static final String ctag = "D0Epfst";
        public D0E000 arg1;
        public D0Epfst(D0E000 arg1) {
            this.arg1 = arg1;
        }
    }

    public static class D0Epsnd extends D0E000 {
        @Override
        public <R> R accept(D0ExpVisitor<R> visitor) {
            return visitor.visit_psnd(this);
        }
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

    /** One operation per expression form, parameterized by its result type. */
    public interface D0ExpVisitor<R> {
        R visit_int(D0Eint dexp);
        R visit_btf(D0Ebtf dexp);
        R visit_op1(D0Eop1 dexp);
        R visit_op2(D0Eop2 dexp);
        R visit_var(D0Evar dexp);
        R visit_lam(D0Elam dexp);
        R visit_fix(D0Efix dexp);
        R visit_app(D0Eapp dexp);
        R visit_if0(D0Eif0 dexp);
        R visit_let(D0Elet dexp);
        R visit_pair(D0Epair dexp);
        R visit_pfst(D0Epfst dexp);
        R visit_psnd(D0Epsnd dexp);
    }

    public static class FreeVariableVisitor implements D0ExpVisitor<Set<String>> {
        @Override
        public Set<String> visit_int(D0Eint e) {
            return Set.of();
        }
        @Override
        public Set<String> visit_btf(D0Ebtf e) {
            return Set.of();
        }
        @Override
        public Set<String> visit_op1(D0Eop1 e) {
            return e.arg1.accept(this);
        }
        @Override
        public Set<String> visit_op2(D0Eop2 e) {
            return union(e.arg1.accept(this), e.arg2.accept(this));
        }
        @Override
        public Set<String> visit_var(D0Evar e) {
            return Set.of(e.arg1);
        }
        @Override
        public Set<String> visit_lam(D0Elam e) {
            return without(e.arg2.accept(this), e.arg1);
        }
        @Override
        public Set<String> visit_fix(D0Efix e) {
            return without(e.arg3.accept(this), e.arg1, e.arg2);
        }
        @Override
        public Set<String> visit_app(D0Eapp e) {
            return union(e.arg1.accept(this), e.arg2.accept(this));
        }
        @Override
        public Set<String> visit_if0(D0Eif0 e) {
            return union(union(e.arg1.accept(this), e.arg2.accept(this)), e.arg3.accept(this));
        }
        @Override
        public Set<String> visit_let(D0Elet e) {
            return union(e.arg2.accept(this), without(e.arg3.accept(this), e.arg1));
        }
        @Override
        public Set<String> visit_pair(D0Epair e) {
            return union(e.arg1.accept(this), e.arg2.accept(this));
        }
        @Override
        public Set<String> visit_pfst(D0Epfst e) {
            return e.arg1.accept(this);
        }
        @Override
        public Set<String> visit_psnd(D0Epsnd e) {
            return e.arg1.accept(this);
        }
    }

    /** Return immutable free names without evaluating the expression. */
    public static Set<String> d0exp_fvset(D0E000 dexp) {
        return dexp.accept(new FreeVariableVisitor());
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
        return dexp.accept(new EvaluateVisitor());
    }

    public static D0V000 d0exp_evaluate(D0E000 dexp, ENV000 denv) {
        return dexp.accept(new EvaluateVisitor(denv));
    }

    /** Each new lexical scope receives a new visitor, preserving the caller's scope. */
    public static class EvaluateVisitor implements D0ExpVisitor<D0V000> {
        public final ENV000 denv;

        public EvaluateVisitor() { this(new ENVnil()); }
        public EvaluateVisitor(ENV000 denv) { this.denv = denv; }

        @Override
        public D0V000 visit_int(D0Eint e) { return new D0Vint(e.arg1); }

        @Override
        public D0V000 visit_btf(D0Ebtf e) { return new D0Vbtf(e.arg1); }

        @Override
        public D0V000 visit_var(D0Evar e) { return d0env_search(denv, e.arg1); }

        @Override
        public D0V000 visit_lam(D0Elam e) { return new D0Vlam(denv, e); }

        @Override
        public D0V000 visit_fix(D0Efix e) { return new D0Vfix(denv, e); }

        @Override
        public D0V000 visit_if0(D0Eif0 e) {
            D0V000 value = e.arg1.accept(this);
            if (!(value instanceof D0Vbtf cond)) throw new IllegalArgumentException("D0Vbtf expected");
            return (cond.arg1 ? e.arg2 : e.arg3).accept(this);
        }

        @Override
        public D0V000 visit_let(D0Elet e) {
            D0V000 value = e.arg2.accept(this);
            return e.arg3.accept(new EvaluateVisitor(new ENVcns(e.arg1, value, denv)));
        }

        @Override
        public D0V000 visit_app(D0Eapp e) {
            D0V000 dfun = e.arg1.accept(this);
            D0V000 darg = e.arg2.accept(this);
            if (dfun instanceof D0Vlam closure) {
                D0Elam lam = closure.arg2;
                return lam.arg2.accept(new EvaluateVisitor(new ENVcns(lam.arg1, darg, closure.arg1)));
            }
            if (dfun instanceof D0Vfix closure) {
                D0Efix fix = closure.arg2;
                ENV000 selfEnv = new ENVcns(fix.arg1, dfun, closure.arg1);
                ENV000 argEnv = new ENVcns(fix.arg2, darg, selfEnv);
                return fix.arg3.accept(new EvaluateVisitor(argEnv));
            }
            throw new IllegalArgumentException("f0_D0Eapp: not D0Vlam/D0Vfix");
        }

        @Override
        public D0V000 visit_op1(D0Eop1 e) {
            D0V000 value = e.arg1.accept(this);
            return switch (e.name) {
                case "+1" -> new D0Vint(integer(value).add(BigInteger.ONE));
                case "-1" -> new D0Vint(integer(value).subtract(BigInteger.ONE));
                default -> throw new IllegalArgumentException("f0_D0Eop1: not supported op1");
            };
        }

        @Override
        public D0V000 visit_op2(D0Eop2 e) {
            D0V000 left = e.arg1.accept(this);
            D0V000 right = e.arg2.accept(this);
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

        @Override
        public D0V000 visit_pair(D0Epair e) {
            D0V000 first = e.arg1.accept(this);
            D0V000 second = e.arg2.accept(this);
            return new D0Vpair(first, second);
        }

        @Override
        public D0V000 visit_pfst(D0Epfst e) {
            D0V000 value = e.arg1.accept(this);
            if (!(value instanceof D0Vpair pair)) throw new IllegalArgumentException("D0Vpair expected");
            return pair.arg1;
        }

        @Override
        public D0V000 visit_psnd(D0Epsnd e) {
            D0V000 value = e.arg1.accept(this);
            if (!(value instanceof D0Vpair pair)) throw new IllegalArgumentException("D0Vpair expected");
            return pair.arg2;
        }
    }

    private static BigInteger integer(D0V000 value) {
        if (value instanceof D0Vint number) return number.arg1;
        throw new IllegalArgumentException("D0Vint expected");
    }

    // BigInteger divides toward zero; Python // divides toward negative infinity.
    private static BigInteger floorDivide(BigInteger a, BigInteger b) {
        BigInteger[] qr = a.divideAndRemainder(b);
        return qr[1].signum() != 0 && a.signum() != b.signum()
            ? qr[0].subtract(BigInteger.ONE) : qr[0];
    }
}
