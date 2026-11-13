a = 1
b = 2
c = 3
d = 4


def test_eval():
    e = 1
    f = 2
    expression = "a+b"
    print(eval(expression, {'a': a, 'b': b, '__builtins__': {}}, {'e': e}))


if __name__ == '__main__':
    test_eval()