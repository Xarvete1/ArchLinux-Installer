#!/bin/bash

if ! command -v python3 &> /dev/null; then
    echo "Ошибка: Python3 не установлен. Установите его перед запуском."
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo "Ошибка: pip3 не установлен. Установите его перед запуском (например, 'sudo apt install python3-pip')."
    exit 1
fi

echo "Проверка зависимостей для ArchLinux Installer..."

if ! python3 -c "import prompt_toolkit" &> /dev/null; then
    echo "Зависимость prompt_toolkit не найдена. Устанавливаю..."
    if pip3 install prompt_toolkit; then
        echo "prompt_toolkit успешно установлен."
    else
        echo "Ошибка установки prompt_toolkit. Проверьте интернет-соединение или права."
        exit 1
    fi
else
    echo "Все зависимости уже установлены."
fi

if [ ! -f "main.py" ]; then
    echo "Ошибка: файл main.py не найден в текущей директории."
    exit 1
fi

echo "Запуск ArchLinux Installer..."
if python3 main.py; then
    echo "Скрипт успешно завершён."
else
    echo "Ошибка при выполнении main.py."
    exit 1
fi