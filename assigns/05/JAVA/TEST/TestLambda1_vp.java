import java.math.BigInteger;
import java.util.Set;

/** Standalone behavioral tests; no JUnit or enabled Java assertions required. */
public final class TestLambda1_vp {
    private static int checks;

    private static void check(boolean ok, String name) {
        checks++;
        if (!ok) throw new AssertionError(name);
    }

    private static void expectError(Class<? extends Throwable> type, Runnable action, String name) {
        checks++;
        try {
            action.run();
        } catch (Throwable error) {
            if (type.isInstance(error)) return;
            throw new AssertionError(name + ": unexpected exception", error);
        }
        throw new AssertionError(name + ": expected " + type.getSimpleName());
    }

    private static String value(Lambda1_vp.D0V000 v) {
        if (v instanceof Lambda1_vp.D0Vint i) return "int:" + i.arg1;
        if (v instanceof Lambda1_vp.D0Vbtf b) return "btf:" + b.arg1;
        if (v instanceof Lambda1_vp.D0Vpair p) return "pair:(" + value(p.arg1) + "," + value(p.arg2) + ")";
        return v.getClass().getSimpleName();
    }

    private static void example(String name, Lambda1_vp.D0E000 term, Set<String> free,
                                String result, Class<? extends Throwable> error) {
        check(Lambda1_vp.d0exp_fvset(term).equals(free), name + ": free variables");
        if (error != null) {
            expectError(error, () -> Lambda1_vp.d0exp_evaluate(term), name);
        } else if (result != null) {
            check(value(Lambda1_vp.d0exp_evaluate(term)).equals(result), name + ": value");
        }
    }

    public static void main(String[] args) {
        // Explicit expected results mirror the shared ../../TEST/cases.json examples.
        example("integer",
                new Lambda1_vp.D0Eint(new BigInteger("42")),
                Set.of(), "int:42", null);
        example("boolean",
                new Lambda1_vp.D0Ebtf(false),
                Set.of(), "btf:false", null);
        example("unbound variable sentinel",
                new Lambda1_vp.D0Evar("missing"),
                Set.of("missing"), "D0V000", null);
        example("arithmetic +",
                new Lambda1_vp.D0Eop2("+", new Lambda1_vp.D0Eint(new BigInteger("7")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "int:10", null);
        example("arithmetic -",
                new Lambda1_vp.D0Eop2("-", new Lambda1_vp.D0Eint(new BigInteger("7")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "int:4", null);
        example("arithmetic *",
                new Lambda1_vp.D0Eop2("*", new Lambda1_vp.D0Eint(new BigInteger("7")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "int:21", null);
        example("arithmetic /",
                new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("7")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "int:2", null);
        example("floor division -7/3",
                new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("-7")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "int:-3", null);
        example("floor division 7/-3",
                new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("7")), new Lambda1_vp.D0Eint(new BigInteger("-3"))),
                Set.of(), "int:-3", null);
        example("floor division -7/-3",
                new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("-7")), new Lambda1_vp.D0Eint(new BigInteger("-3"))),
                Set.of(), "int:2", null);
        example("floor division -6/3",
                new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("-6")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "int:-2", null);
        example("floor division 0/-3",
                new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("0")), new Lambda1_vp.D0Eint(new BigInteger("-3"))),
                Set.of(), "int:0", null);
        example("arbitrary precision",
                new Lambda1_vp.D0Eop2("*", new Lambda1_vp.D0Eint(new BigInteger("100000000000000000000")), new Lambda1_vp.D0Eint(new BigInteger("100000000000000000000"))),
                Set.of(), "int:10000000000000000000000000000000000000000", null);
        example("comparison 2<3",
                new Lambda1_vp.D0Eop2("<", new Lambda1_vp.D0Eint(new BigInteger("2")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:true", null);
        example("comparison 3<3",
                new Lambda1_vp.D0Eop2("<", new Lambda1_vp.D0Eint(new BigInteger("3")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:false", null);
        example("comparison 4<3",
                new Lambda1_vp.D0Eop2("<", new Lambda1_vp.D0Eint(new BigInteger("4")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:false", null);
        example("comparison 2>3",
                new Lambda1_vp.D0Eop2(">", new Lambda1_vp.D0Eint(new BigInteger("2")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:false", null);
        example("comparison 3>3",
                new Lambda1_vp.D0Eop2(">", new Lambda1_vp.D0Eint(new BigInteger("3")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:false", null);
        example("comparison 4>3",
                new Lambda1_vp.D0Eop2(">", new Lambda1_vp.D0Eint(new BigInteger("4")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:true", null);
        example("comparison 2<=3",
                new Lambda1_vp.D0Eop2("<=", new Lambda1_vp.D0Eint(new BigInteger("2")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:true", null);
        example("comparison 3<=3",
                new Lambda1_vp.D0Eop2("<=", new Lambda1_vp.D0Eint(new BigInteger("3")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:true", null);
        example("comparison 4<=3",
                new Lambda1_vp.D0Eop2("<=", new Lambda1_vp.D0Eint(new BigInteger("4")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:false", null);
        example("comparison 2>=3",
                new Lambda1_vp.D0Eop2(">=", new Lambda1_vp.D0Eint(new BigInteger("2")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:false", null);
        example("comparison 3>=3",
                new Lambda1_vp.D0Eop2(">=", new Lambda1_vp.D0Eint(new BigInteger("3")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:true", null);
        example("comparison 4>=3",
                new Lambda1_vp.D0Eop2(">=", new Lambda1_vp.D0Eint(new BigInteger("4")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:true", null);
        example("comparison 2==3",
                new Lambda1_vp.D0Eop2("==", new Lambda1_vp.D0Eint(new BigInteger("2")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:false", null);
        example("comparison 3==3",
                new Lambda1_vp.D0Eop2("==", new Lambda1_vp.D0Eint(new BigInteger("3")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:true", null);
        example("comparison 4==3",
                new Lambda1_vp.D0Eop2("==", new Lambda1_vp.D0Eint(new BigInteger("4")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:false", null);
        example("comparison 2!=3",
                new Lambda1_vp.D0Eop2("!=", new Lambda1_vp.D0Eint(new BigInteger("2")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:true", null);
        example("comparison 3!=3",
                new Lambda1_vp.D0Eop2("!=", new Lambda1_vp.D0Eint(new BigInteger("3")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:false", null);
        example("comparison 4!=3",
                new Lambda1_vp.D0Eop2("!=", new Lambda1_vp.D0Eint(new BigInteger("4")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), "btf:true", null);
        example("unary +1",
                new Lambda1_vp.D0Eop1("+1", new Lambda1_vp.D0Eint(new BigInteger("5"))),
                Set.of(), "int:6", null);
        example("unary -1",
                new Lambda1_vp.D0Eop1("-1", new Lambda1_vp.D0Eint(new BigInteger("5"))),
                Set.of(), "int:4", null);
        example("conditional selects True",
                new Lambda1_vp.D0Eif0(new Lambda1_vp.D0Ebtf(true), new Lambda1_vp.D0Eint(new BigInteger("9")), new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eint(new BigInteger("0")))),
                Set.of(), "int:9", null);
        example("conditional selects False",
                new Lambda1_vp.D0Eif0(new Lambda1_vp.D0Ebtf(false), new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eint(new BigInteger("0"))), new Lambda1_vp.D0Eint(new BigInteger("9"))),
                Set.of(), "int:9", null);
        example("let initializer sees outer binding",
                new Lambda1_vp.D0Elet("x", new Lambda1_vp.D0Eint(new BigInteger("10")), new Lambda1_vp.D0Elet("x", new Lambda1_vp.D0Eop2("+", new Lambda1_vp.D0Evar("x"), new Lambda1_vp.D0Eint(new BigInteger("1"))), new Lambda1_vp.D0Evar("x"))),
                Set.of(), "int:11", null);
        example("lambda captures lexical scope",
                new Lambda1_vp.D0Elet("x", new Lambda1_vp.D0Eint(new BigInteger("10")), new Lambda1_vp.D0Elet("f", new Lambda1_vp.D0Elam("y", new Lambda1_vp.D0Eop2("+", new Lambda1_vp.D0Evar("x"), new Lambda1_vp.D0Evar("y"))), new Lambda1_vp.D0Elet("x", new Lambda1_vp.D0Eint(new BigInteger("99")), new Lambda1_vp.D0Eapp(new Lambda1_vp.D0Evar("f"), new Lambda1_vp.D0Eint(new BigInteger("2")))))),
                Set.of(), "int:12", null);
        example("higher order closure",
                new Lambda1_vp.D0Eapp(new Lambda1_vp.D0Eapp(new Lambda1_vp.D0Elam("x", new Lambda1_vp.D0Elam("y", new Lambda1_vp.D0Eop2("+", new Lambda1_vp.D0Evar("x"), new Lambda1_vp.D0Evar("y")))), new Lambda1_vp.D0Eint(new BigInteger("7"))), new Lambda1_vp.D0Eint(new BigInteger("8"))),
                Set.of(), "int:15", null);
        example("recursive factorial",
                new Lambda1_vp.D0Eapp(new Lambda1_vp.D0Efix("fact", "n", new Lambda1_vp.D0Eif0(new Lambda1_vp.D0Eop2("<=", new Lambda1_vp.D0Evar("n"), new Lambda1_vp.D0Eint(new BigInteger("1"))), new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eop2("*", new Lambda1_vp.D0Evar("n"), new Lambda1_vp.D0Eapp(new Lambda1_vp.D0Evar("fact"), new Lambda1_vp.D0Eop1("-1", new Lambda1_vp.D0Evar("n")))))), new Lambda1_vp.D0Eint(new BigInteger("6"))),
                Set.of(), "int:720", null);
        example("fix parameter shadows own name",
                new Lambda1_vp.D0Eapp(new Lambda1_vp.D0Efix("x", "x", new Lambda1_vp.D0Evar("x")), new Lambda1_vp.D0Eint(new BigInteger("7"))),
                Set.of(), "int:7", null);
        example("fix captures lexical scope",
                new Lambda1_vp.D0Elet("x", new Lambda1_vp.D0Eint(new BigInteger("10")), new Lambda1_vp.D0Elet("f", new Lambda1_vp.D0Efix("f", "n", new Lambda1_vp.D0Eif0(new Lambda1_vp.D0Eop2("==", new Lambda1_vp.D0Evar("n"), new Lambda1_vp.D0Eint(new BigInteger("0"))), new Lambda1_vp.D0Evar("x"), new Lambda1_vp.D0Eapp(new Lambda1_vp.D0Evar("f"), new Lambda1_vp.D0Eop1("-1", new Lambda1_vp.D0Evar("n"))))), new Lambda1_vp.D0Elet("x", new Lambda1_vp.D0Eint(new BigInteger("99")), new Lambda1_vp.D0Eapp(new Lambda1_vp.D0Evar("f"), new Lambda1_vp.D0Eint(new BigInteger("3")))))),
                Set.of(), "int:10", null);
        example("nested pair",
                new Lambda1_vp.D0Epair(new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Epair(new Lambda1_vp.D0Ebtf(true), new Lambda1_vp.D0Eint(new BigInteger("2")))),
                Set.of(), "pair:(int:1,pair:(btf:true,int:2))", null);
        example("pfst",
                new Lambda1_vp.D0Epfst(new Lambda1_vp.D0Epair(new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Ebtf(true))),
                Set.of(), "int:1", null);
        example("psnd",
                new Lambda1_vp.D0Epsnd(new Lambda1_vp.D0Epair(new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Ebtf(true))),
                Set.of(), "btf:true", null);
        example("argument is eager",
                new Lambda1_vp.D0Eapp(new Lambda1_vp.D0Elam("x", new Lambda1_vp.D0Eint(new BigInteger("1"))), new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eint(new BigInteger("0")))),
                Set.of(), null, ArithmeticException.class);
        example("let initializer is eager",
                new Lambda1_vp.D0Elet("x", new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eint(new BigInteger("0"))), new Lambda1_vp.D0Eint(new BigInteger("1"))),
                Set.of(), null, ArithmeticException.class);
        example("pair second is eager",
                new Lambda1_vp.D0Epfst(new Lambda1_vp.D0Epair(new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eint(new BigInteger("0"))))),
                Set.of(), null, ArithmeticException.class);
        example("division by zero",
                new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eint(new BigInteger("0"))),
                Set.of(), null, ArithmeticException.class);
        example("condition requires boolean",
                new Lambda1_vp.D0Eif0(new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eint(new BigInteger("2")), new Lambda1_vp.D0Eint(new BigInteger("3"))),
                Set.of(), null, IllegalArgumentException.class);
        example("application requires closure",
                new Lambda1_vp.D0Eapp(new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eint(new BigInteger("2"))),
                Set.of(), null, IllegalArgumentException.class);
        example("first requires pair",
                new Lambda1_vp.D0Epfst(new Lambda1_vp.D0Eint(new BigInteger("1"))),
                Set.of(), null, IllegalArgumentException.class);
        example("second requires pair",
                new Lambda1_vp.D0Epsnd(new Lambda1_vp.D0Eint(new BigInteger("1"))),
                Set.of(), null, IllegalArgumentException.class);
        example("unary requires integer",
                new Lambda1_vp.D0Eop1("+1", new Lambda1_vp.D0Ebtf(true)),
                Set.of(), null, IllegalArgumentException.class);
        example("unknown unary",
                new Lambda1_vp.D0Eop1("?", new Lambda1_vp.D0Eint(new BigInteger("1"))),
                Set.of(), null, IllegalArgumentException.class);
        example("unknown binary",
                new Lambda1_vp.D0Eop2("?", new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eint(new BigInteger("2"))),
                Set.of(), null, IllegalArgumentException.class);
        example("left requires integer",
                new Lambda1_vp.D0Eop2("+", new Lambda1_vp.D0Ebtf(true), new Lambda1_vp.D0Eint(new BigInteger("2"))),
                Set.of(), null, IllegalArgumentException.class);
        example("right requires integer",
                new Lambda1_vp.D0Eop2("+", new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Ebtf(true)),
                Set.of(), null, IllegalArgumentException.class);
        example("pair left before right",
                new Lambda1_vp.D0Epair(new Lambda1_vp.D0Epfst(new Lambda1_vp.D0Eint(new BigInteger("0"))), new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eint(new BigInteger("0")))),
                Set.of(), null, IllegalArgumentException.class);
        example("operator left before right",
                new Lambda1_vp.D0Eop2("+", new Lambda1_vp.D0Epfst(new Lambda1_vp.D0Eint(new BigInteger("0"))), new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eint(new BigInteger("0")))),
                Set.of(), null, IllegalArgumentException.class);
        example("function before argument",
                new Lambda1_vp.D0Eapp(new Lambda1_vp.D0Epfst(new Lambda1_vp.D0Eint(new BigInteger("0"))), new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eint(new BigInteger("0")))),
                Set.of(), null, IllegalArgumentException.class);
        example("argument before application type check",
                new Lambda1_vp.D0Eapp(new Lambda1_vp.D0Eint(new BigInteger("0")), new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eint(new BigInteger("0")))),
                Set.of(), null, ArithmeticException.class);
        example("lambda binding",
                new Lambda1_vp.D0Elam("x", new Lambda1_vp.D0Eop2("+", new Lambda1_vp.D0Evar("x"), new Lambda1_vp.D0Evar("y"))),
                Set.of("y"), null, null);
        example("fix bindings",
                new Lambda1_vp.D0Efix("f", "x", new Lambda1_vp.D0Epair(new Lambda1_vp.D0Eapp(new Lambda1_vp.D0Evar("f"), new Lambda1_vp.D0Evar("x")), new Lambda1_vp.D0Evar("z"))),
                Set.of("z"), null, null);
        example("let initializer remains free",
                new Lambda1_vp.D0Elet("x", new Lambda1_vp.D0Evar("x"), new Lambda1_vp.D0Epair(new Lambda1_vp.D0Evar("x"), new Lambda1_vp.D0Evar("y"))),
                Set.of("x", "y"), null, null);
        example("if visits all branches",
                new Lambda1_vp.D0Eif0(new Lambda1_vp.D0Evar("c"), new Lambda1_vp.D0Evar("x"), new Lambda1_vp.D0Evar("y")),
                Set.of("c", "x", "y"), null, null);
        example("unary free variables",
                new Lambda1_vp.D0Eop1("+1", new Lambda1_vp.D0Evar("x")),
                Set.of("x"), null, null);
        example("first free variables",
                new Lambda1_vp.D0Epfst(new Lambda1_vp.D0Evar("p")),
                Set.of("p"), null, null);
        example("second free variables",
                new Lambda1_vp.D0Epsnd(new Lambda1_vp.D0Evar("p")),
                Set.of("p"), null, null);
        example("duplicate names collapse",
                new Lambda1_vp.D0Epair(new Lambda1_vp.D0Evar("x"), new Lambda1_vp.D0Evar("x")),
                Set.of("x"), null, null);
        example("free analysis does not evaluate",
                new Lambda1_vp.D0Eop2("/", new Lambda1_vp.D0Eint(new BigInteger("1")), new Lambda1_vp.D0Eint(new BigInteger("0"))),
                Set.of(), null, null);

        Lambda1_vp.ENV000 tail = new Lambda1_vp.ENVcns("x", new Lambda1_vp.D0Vint(1), new Lambda1_vp.ENVnil());
        Lambda1_vp.ENV000 env = new Lambda1_vp.ENVcns("x", new Lambda1_vp.D0Vint(2), tail);
        check(value(Lambda1_vp.d0env_search(env, "x")).equals("int:2"), "nearest binding");
        check(value(Lambda1_vp.d0exp_evaluate(new Lambda1_vp.D0Evar("x"), tail)).equals("int:1"), "outer environment unchanged");
        check(Lambda1_vp.d0env_search(env, "missing").getClass() == Lambda1_vp.D0V000.class, "unbound sentinel");
        expectError(UnsupportedOperationException.class,
                () -> Lambda1_vp.d0exp_fvset(new Lambda1_vp.D0Evar("x")).add("y"), "immutable free set");
        expectError(IllegalArgumentException.class,
                () -> Lambda1_vp.d0exp_evaluate(new Lambda1_vp.D0E000()), "unsupported evaluation");
        expectError(IllegalArgumentException.class,
                () -> Lambda1_vp.d0exp_fvset(new Lambda1_vp.D0E000()), "unsupported analysis");
        Lambda1_vp.D0Elam lam = new Lambda1_vp.D0Elam("y", new Lambda1_vp.D0Evar("x"));
        Lambda1_vp.D0Vlam closure = (Lambda1_vp.D0Vlam) Lambda1_vp.d0exp_evaluate(lam, env);
        check(closure.arg1 == env && closure.arg2 == lam, "lambda captures environment and syntax");
        Lambda1_vp.D0Efix fix = new Lambda1_vp.D0Efix("f", "y", new Lambda1_vp.D0Evar("x"));
        Lambda1_vp.D0Vfix recursive = (Lambda1_vp.D0Vfix) Lambda1_vp.d0exp_evaluate(fix, env);
        check(recursive.arg1 == env && recursive.arg2 == fix, "fix captures environment and syntax");

        Lambda1_vp.EvaluateVisitor visitor = new Lambda1_vp.EvaluateVisitor(env);
        Lambda1_vp.D0E000 local = new Lambda1_vp.D0Elet("x", new Lambda1_vp.D0Eint(9), new Lambda1_vp.D0Evar("x"));
        check(value(local.accept(visitor)).equals("int:9"), "direct evaluation visitor");
        check(value(new Lambda1_vp.D0Evar("x").accept(visitor)).equals("int:2"), "visitor scope does not leak");
        check(new Lambda1_vp.D0Evar("x").accept(new Lambda1_vp.FreeVariableVisitor()).equals(Set.of("x")), "direct free variable visitor");
        Lambda1_vp.FreeVariableVisitor custom = new Lambda1_vp.FreeVariableVisitor() {
            @Override public Set<String> visit_int(Lambda1_vp.D0Eint e) { return Set.of("custom"); }
        };
        check(new Lambda1_vp.D0Eint(1).accept(custom).equals(Set.of("custom")), "accept dispatches to custom visitor");
        System.out.println("TestLambda1_vp: " + checks + " checks passed (70 shared examples plus API checks).");
    }
}
