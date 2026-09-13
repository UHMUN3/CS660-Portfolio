"""
Simple Arithmetic Interpreter

Grammar (BNF) for arithmetic expressions with +, -, *, and parentheses:

    <Expr>   ::= <Expr> + <Term> | <Expr> - <Term> | <Term>
    <Term>   ::= <Term> * <Factor> | <Factor>
    <Factor> ::= ( <Expr> ) | <Number>
    <Number> ::= <Digit> <Number> | <Digit>
    <Digit>  ::= 0 | 1 | 2 | ... | 9

The parser below is recursive descent (top-down), so the left-recursive
rules are implemented in their iterative EBNF form, folding operands
into a left-leaning AST to preserve left associativity:

    Expr ::= Term { (+ | -) Term }
    Term ::= Factor { * Factor }
"""

class ASTNode:
    pass

class NumberNode(ASTNode):
    def __init__(self, value):
        self.value = value

class BinaryOpNode(ASTNode):
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class Parser:
    def __init__(self, expression):
        self.expr = expression.replace(' ', '')
        self.pos = 0
        self.current_char = self.expr[0] if self.expr else None

    def advance(self):
        self.pos += 1
        self.current_char = self.expr[self.pos] if self.pos < len(self.expr) else None

    def parse_number(self):
        # <Number> ::= <Digit> <Number> | <Digit>
        digits = ''
        while self.current_char is not None and self.current_char.isdigit():
            digits += self.current_char
            self.advance()
        return NumberNode(int(digits))

    def parse_factor(self):
        # <Factor> ::= ( <Expr> ) | <Number>
        if self.current_char == '(':
            self.advance()                  # consume '('
            node = self.parse_expression()
            self.advance()                  # consume ')'
            return node
        return self.parse_number()

    def parse_term(self):
        # <Term> ::= <Term> * <Factor>, folded left: Factor { * Factor }
        node = self.parse_factor()
        while self.current_char == '*':
            self.advance()
            node = BinaryOpNode(node, '*', self.parse_factor())
        return node

    def parse_expression(self):
        # <Expr> ::= <Expr> (+|-) <Term>, folded left: Term { (+|-) Term }
        node = self.parse_term()
        while self.current_char in ('+', '-'):
            op = self.current_char
            self.advance()
            node = BinaryOpNode(node, op, self.parse_term())
        return node

def evaluate(node):
    # Semantic rules: a Number denotes its integer value; a binary node
    # denotes its operator applied to the values of its subtrees.
    if isinstance(node, NumberNode):
        return node.value
    left = evaluate(node.left)
    right = evaluate(node.right)
    if node.op == '+':
        return left + right
    if node.op == '-':
        return left - right
    if node.op == '*':
        return left * right

def ast_to_string(node):
    # Fully parenthesized form of the AST, to make its structure visible.
    if isinstance(node, NumberNode):
        return str(node.value)
    return f"({ast_to_string(node.left)} {node.op} {ast_to_string(node.right)})"

def interpret(expression):
    parser = Parser(expression)
    ast = parser.parse_expression()
    return evaluate(ast)

# Test cases
if __name__ == "__main__":
    test_expressions = [
        "42",
        "2 + 3",
        "10 - 4",
        "3 * 7",
        "2 + 3 * 4",
        "(2 + 3) * 4",
        "1 + 2 + 3",
        "10 - 5 - 2",
        "((1 + 2) * 3) - 4"
    ]

    print("Aaron Foster")
    print("Arithmetic Interpreter Test")
    for expr in test_expressions:
        try:
            result = interpret(expr)
            ast = Parser(expr).parse_expression()
            print(f"{expr} = {result}    AST: {ast_to_string(ast)}")
        except Exception as e:
            print(f"Error interpreting '{expr}': {e}")
