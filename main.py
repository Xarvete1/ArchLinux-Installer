import subprocess
import os
from prompt_toolkit import PromptSession
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.shortcuts import confirm, radiolist_dialog, input_dialog, password_dialog

class NonEmptyValidator(Validator):
    def validate(self, document):
        text = document.text
        if not text or " " in text:
            raise ValidationError(message="Имя не может быть пустым или содержать пробелы")

def get_available_disks():
    try:
        result = subprocess.run(["lsblk", "-d", "-n", "-o", "NAME"], capture_output=True, text=True)
        disks = [f"/dev/{line.strip()}" for line in result.stdout.splitlines()]
        return disks if disks else []
    except Exception as e:
        print(f"Ошибка получения дисков: {e}")
        exit(1)

def install_system(username, password, disk, filesystem, use_swap, swap_size, timezone, locale, use_luks, luks_password, bootloader):
    print("Шаг 1: Подготовка диска...")
    root_part = f"{disk}1"
    swap_part = f"{disk}2"
    print(f"Создание разделов на {disk}...")

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
    subprocess.run(["arch-chroot", "/mnt"], check=True)  # Требует доработки

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
    session = PromptSession()

    username = input_dialog(
        title="Имя пользователя",
        text="Введите имя пользователя:",
        validator=NonEmptyValidator()
    ).run()
    if not username:
        print("Ошибка ввода. Установка прервана.")
        exit(1)

    password = password_dialog(
        title="Пароль",
        text="Введите пароль:"
    ).run()
    password_confirm = password_dialog(
        title="Пароль",
        text="Повторите пароль:"
    ).run()
    if password != password_confirm or not password:
        print("Пароли не совпадают или пустые. Установка прервана.")
        exit(1)

    disks = get_available_disks()
    if not disks:
        print("Диски не найдены. Установка прервана.")
        exit(1)
    selected_disk = radiolist_dialog(
        title="Выбор диска",
        text="Выберите диск для установки:",
        values=[(disk, disk) for disk in disks]
    ).run()
    if not selected_disk:
        print("Диск не выбран. Установка прервана.")
        exit(1)

    filesystems = ["ext4", "btrfs", "xfs", "f2fs"]
    selected_fs = radiolist_dialog(
        title="Файловая система",
        text="Выберите тип файловой системы:",
        values=[(fs, fs) for fs in filesystems]
    ).run()
    if not selected_fs:
        print("Файловая система не выбрана. Установка прервана.")
        exit(1)

    use_swap = confirm("Создать swap-раздел?")
    swap_size = ""
    if use_swap:
        swap_size = session.prompt("Введите размер swap-раздела (например, 2G): ", default="2G")
        if not swap_size:
            print("Ошибка ввода. Установка прервана.")
            exit(1)

    timezones = ["Europe/Moscow", "America/New_York", "Asia/Tokyo"]
    selected_tz = radiolist_dialog(
        title="Часовой пояс",
        text="Выберите часовой пояс:",
        values=[(tz, tz) for tz in timezones]
    ).run()
    if not selected_tz:
        print("Часовой пояс не выбран. Установка прервана.")
        exit(1)

    locales = ["ru_RU.UTF-8", "en_US.UTF-8", "ja_JP.UTF-8"]
    selected_locale = radiolist_dialog(
        title="Локаль",
        text="Выберите локаль:",
        values=[(loc, loc) for loc in locales]
    ).run()
    if not selected_locale:
        print("Локаль не выбрана. Установка прервана.")
        exit(1)

    use_luks = confirm("Использовать шифрование LUKS?")
    luks_password = None
    if use_luks:
        luks_password = password_dialog(
            title="LUKS",
            text="Введите пароль для LUKS:"
        ).run()
        luks_confirm = password_dialog(
            title="LUKS",
            text="Повторите пароль для LUKS:"
        ).run()
        if luks_password != luks_confirm or not luks_password:
            print("Пароли LUKS не совпадают или пустые. Установка прервана.")
            exit(1)

    bootloaders = ["GRUB", "systemd-boot"]
    selected_bootloader = radiolist_dialog(
        title="Загрузчик",
        text="Выберите загрузчик:",
        values=[(bl, bl) for bl in bootloaders]
    ).run()
    if not selected_bootloader:
        print("Загрузчик не выбран. Установка прервана.")
        exit(1)

    print("\nВаши настройки:")
    print(f"Имя пользователя: {username}")
    print("Пароль: [скрыт]")
    print(f"Диск: {selected_disk}")
    print(f"Файловая система: {selected_fs}")
    print(f"Swap-раздел: {swap_size if use_swap else 'Нет'}")
    print(f"Часовой пояс: {selected_tz}")
    print(f"Локаль: {selected_locale}")
    print(f"Шифрование LUKS: {'Да' if use_luks else 'Нет'}")
    print(f"Загрузчик: {selected_bootloader}")

    if confirm("Всё верно? Начать установку?"):
        install_system(
            username, password, selected_disk, selected_fs, use_swap, swap_size,
            selected_tz, selected_locale, use_luks, luks_password, selected_bootloader
        )
        print("Установка завершена успешно!")
    else:
        print("Установка отменена.")

if __name__ == "__main__":
    main()