import subprocess
import os
import sys

def get_available_disks():
    try:
        result = subprocess.run(["lsblk", "-d", "-n", "-o", "NAME"], capture_output=True, text=True)
        disks = [f"/dev/{line.strip()}" for line in result.stdout.splitlines()]
        return disks if disks else []
    except Exception as e:
        print(f"Ошибка получения дисков: {e}")
        sys.exit(1)

def install_system(username, password, disk, filesystem, use_swap, swap_size, timezone, locale, use_luks, luks_password, bootloader):
    print("Шаг 1: Подготовка диска...")
    root_part = f"{disk}1"
    swap_part = f"{disk}2"
    print(f"Создание разделов на {disk}... (предполагается ручная разметка)")

    if use_luks:
        print(f"Шаг 2: Настройка LUKS на {root_part}...")
        subprocess.run(["cryptsetup", "luksFormat", root_part], input=luks_password.encode(), check=True)
        subprocess.run(["cryptsetup", "open", root_part, "cryptroot"], input=luks_password.encode(), check=True)

    print("Шаг 3: Форматирование разделов...")
    root_dev = "/dev/mapper/cryptroot" if use_luks else root_part
    subprocess.run([f"mkfs.{filesystem}", root_dev], check=True)
    if use_swap:
        subprocess.run(["mkswap", swap_part], check=True)
        subprocess.run(["swapon", swap_part], check=True)

    print("Шаг 4: Монтирование и установка базовой системы...")
    subprocess.run(["mount", root_dev, "/mnt"], check=True)
    subprocess.run(["pacstrap", "/mnt", "base", "linux", "linux-firmware"], check=True)

    print("Шаг 5: Настройка системы...")
    subprocess.run(["genfstab", "-U", "/mnt"], check=True)
    subprocess.run(["arch-chroot", "/mnt"], check=True)  # Упрощено

    print("Шаг 6: Установка часового пояса и локали...")
    subprocess.run(["ln", "-sf", f"/usr/share/zoneinfo/{timezone}", "/etc/localtime"], check=True)
    with open("/etc/locale.gen", "a") as f:
        f.write(f"{locale} UTF-8\n")
    subprocess.run(["locale-gen"], check=True)

    print("Шаг 7: Настройка пользователя...")
    subprocess.run(["useradd", "-m", username], check=True)
    subprocess.run(["chpasswd"], input=f"{username}:{password}".encode(), check=True)

    print(f"Шаг 8: Установка загрузчика ({bootloader})...")
    if bootloader == "GRUB":
        subprocess.run(["grub-install", disk], check=True)
        subprocess.run(["grub-mkconfig", "-o", "/boot/grub/grub.cfg"], check=True)
    else:
        subprocess.run(["bootctl", "install"], check=True)

def main():
    print("Добро пожаловать в ArchLinux Installer!")

    # 1. Имя пользователя
    while True:
        username = input("Введите имя пользователя: ").strip()
        if username and " " not in username:
            break
        print("Имя не может быть пустым или содержать пробелы.")

    # 2. Пароль
    while True:
        password = input("Введите пароль: ")
        password_confirm = input("Повторите пароль: ")
        if password == password_confirm and password:
            break
        print("Пароли не совпадают или пустые.")

    # 3. Выбор диска
    disks = get_available_disks()
    if not disks:
        print("Диски не найдены. Установка прервана.")
        sys.exit(1)
    print("Доступные диски:", ", ".join(disks))
    while True:
        disk = input("Выберите диск для установки (например, /dev/sda): ").strip()
        if disk in disks:
            break
        print("Неверный выбор диска.")

    # 4. Тип файловой системы
    filesystems = ["ext4", "btrfs", "xfs", "f2fs"]
    print("Доступные файловые системы:", ", ".join(filesystems))
    while True:
        filesystem = input("Выберите тип файловой системы: ").lower()
        if filesystem in filesystems:
            break
        print("Неверный выбор файловой системы.")

    # 5. Swap-раздел
    use_swap = input("Создать swap-раздел? (yes/no): ").lower() == "yes"
    swap_size = ""
    if use_swap:
        swap_size = input("Введите размер swap-раздела (например, 2G): ").strip() or "2G"

    # 6. Часовой пояс
    timezones = ["Europe/Moscow", "America/New_York", "Asia/Tokyo"]
    print("Доступные часовые пояса:", ", ".join(timezones))
    while True:
        timezone = input("Выберите часовой пояс: ")
        if timezone in timezones:
            break
        print("Неверный выбор часового пояса.")

    # 7. Локаль
    locales = ["ru_RU.UTF-8", "en_US.UTF-8", "ja_JP.UTF-8"]
    print("Доступные локали:", ", ".join(locales))
    while True:
        locale = input("Выберите локаль: ")
        if locale in locales:
            break
        print("Неверный выбор локали.")

    # 8. Шифрование LUKS
    use_luks = input("Использовать шифрование LUKS? (yes/no): ").lower() == "yes"
    luks_password = None
    if use_luks:
        while True:
            luks_password = input("Введите пароль для LUKS: ")
            luks_confirm = input("Повторите пароль для LUKS: ")
            if luks_password == luks_confirm and luks_password:
                break
            print("Пароли LUKS не совпадают или пустые.")

    # 9. Выбор загрузчика
    bootloaders = ["GRUB", "systemd-boot"]
    print("Доступные загрузчики:", ", ".join(bootloaders))
    while True:
        bootloader = input("Выберите загрузчик: ").upper()
        if bootloader in bootloaders:
            break
        print("Неверный выбор загрузчика.")

    # Финальная проверка
    print("\nВаши настройки:")
    print(f"Имя пользователя: {username}")
    print("Пароль: [скрыт]")
    print(f"Диск: {disk}")
    print(f"Файловая система: {filesystem}")
    print(f"Swap-раздел: {swap_size if use_swap else 'Нет'}")
    print(f"Часовой пояс: {timezone}")
    print(f"Локаль: {locale}")
    print(f"Шифрование LUKS: {'Да' if use_luks else 'Нет'}")
    print(f"Загрузчик: {bootloader}")

    confirm = input("Всё верно? Начать установку? (yes/no): ").lower() == "yes"
    if confirm:
        install_system(
            username, password, disk, filesystem, use_swap, swap_size,
            timezone, locale, use_luks, luks_password, bootloader
        )
        print("Установка завершена успешно!")
    else:
        print("Установка отменена.")

if __name__ == "__main__":
    main()