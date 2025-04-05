# 🆕 Автоматично створений файл


def check_password_length(password):
    """
    Перевіряє, чи має пароль щонайменше 8 символів.

    Args:
        password (str): Пароль користувача.

    Returns:
        bool: True, якщо пароль довший або дорівнює 8 символам, інакше False.
    """
    return len(password) >= 8
