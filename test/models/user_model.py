# 🆕 Автоматично створений файл


class User:
    """
    Клас для представлення користувача.
    """

    def __init__(self, name):
        """
        Ініціалізація об'єкта користувача.

        Args:
            name (str): Ім'я користувача.
        """
        self.name = name

    def greet(self):
        """
        Виводить привітання для користувача.
        """
        print(f"Привіт, {self.name}!")
