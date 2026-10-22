"""Free variables for the lecture's tuple-based lambda expressions."""


def free_vars(expr):
    tag = expr[0]
    if tag == "var":
        return {expr[1]}
    if tag == "app":
        return free_vars(expr[1]) | free_vars(expr[2])
    if tag == "lam":
        return free_vars(expr[2]) - {expr[1]}
    raise ValueError(f"unknown expression tag: {tag}")
