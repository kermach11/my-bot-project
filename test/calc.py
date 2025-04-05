# 🆕 Автоматично створений файл


def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        return "На нуль ділити не можна"
    return a / b

def main():
    print("Простий калькулятор:")
    x = 10
    y = 5
    print("Сума:", add(x, y))
    print("Різниця:", subtract(x, y))
    print("Добуток:", multiply(x, y))
    print("Ділення:", divide(x, y))

if __name__ == "__main__":
    main()
