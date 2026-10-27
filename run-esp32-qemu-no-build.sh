
#!/usr/bin/env bash
source ~/esp/esp-idf/export.sh
set -Eeuo pipefail

PROJECT_DIR="${1:-$PWD}"
ENV_NAME="${2:-esp32dev}"

PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
BUILD_DIR="$PROJECT_DIR/.pio/build/$ENV_NAME"
FLASH_ARGS="$BUILD_DIR/flash_args"
FLASH_IMAGE="$BUILD_DIR/flash_image.bin"

QEMU="${QEMU:-$HOME/.espressif/tools/qemu-xtensa/esp_develop_9.0.0_20240606/qemu/bin/qemu-system-xtensa}"

if [[ ! -f "$FLASH_ARGS" ]]; then
    echo "[ERROR] Не найден файл: $FLASH_ARGS" >&2
    exit 1
fi

if [[ ! -x "$QEMU" ]]; then
    echo "[ERROR] Не найден QEMU: $QEMU" >&2
    exit 1
fi

PYTHON="$(command -v python || command -v python3)"

if ! "$PYTHON" -m esptool version >/dev/null 2>&1; then
    echo "[ERROR] esptool недоступен в $PYTHON" >&2
    echo "Выполни: source ~/esp/esp-idf/export.sh" >&2
    exit 1
fi

echo "[INFO] Проект: $PROJECT_DIR"
echo "[INFO] Environment: $ENV_NAME"
echo "[INFO] Использую существующую сборку: $BUILD_DIR"
echo "[INFO] Сборку PlatformIO не запускаю."

# Читаем flash_args и отдельно формируем параметры и пары адрес/файл.
mapfile -d '' -t MERGE_ARGS < <(
python3 - "$BUILD_DIR" "$FLASH_ARGS" <<'PY'
import shlex
import sys
from pathlib import Path

build = Path(sys.argv[1])
args_file = Path(sys.argv[2])

tokens = []
for line in args_file.read_text().splitlines():
    tokens.extend(shlex.split(line, comments=True))

options = []
pairs = []

i = 0
while i < len(tokens):
    token = tokens[i]

    if token in ("--flash-mode", "--flash_mode",
                 "--flash-freq", "--flash_freq",
                 "--flash-size", "--flash_size"):
        if i + 1 >= len(tokens):
            raise SystemExit(f"Нет значения параметра {token}")

        option_map = {
            "--flash-mode": "--flash_mode",
            "--flash_mode": "--flash_mode",
            "--flash-freq": "--flash_freq",
            "--flash_freq": "--flash_freq",
            "--flash-size": "--flash_size",
            "--flash_size": "--flash_size",
        }

        options.extend([option_map[token], tokens[i + 1]])
        i += 2
        continue

    # Адреса в flash_args имеют вид 0x1000, 0x8000, 0x10000.
    if token.lower().startswith("0x"):
        if i + 1 >= len(tokens):
            raise SystemExit(f"Нет имени файла после адреса {token}")
        pairs.append((token, tokens[i + 1]))
        i += 2
        continue

    if token.startswith("--"):
        raise SystemExit(f"Неизвестный параметр flash_args: {token}")

    raise SystemExit(f"Неожиданный токен в flash_args: {token}")

if not pairs:
    raise SystemExit("В flash_args не найдены адреса прошивки.")

aliases = {
    "bootloader.bin": ["bootloader.bin"],
    "partition-table.bin": ["partition-table.bin", "partitions.bin"],
    "partitions.bin": ["partitions.bin", "partition-table.bin"],
    "minifct_espidf.bin": ["minifct_espidf.bin", "firmware.bin"],
    "firmware.bin": ["firmware.bin", "minifct_espidf.bin"],
}

resolved = []

for address, filename in pairs:
    candidate = build / filename

    if not candidate.is_file():
        candidate = build / Path(filename).name

    if not candidate.is_file():
        alternatives = aliases.get(Path(filename).name, [])
        candidate = next(
            (build / name for name in alternatives
             if (build / name).is_file()),
            candidate
        )

    if not candidate.is_file():
        raise SystemExit(
            f"Не найден BIN-файл для адреса {address}: {filename}"
        )

    resolved.extend([address, str(candidate)])

# ВАЖНО: параметры и пары адрес/файл передаются отдельно,
# все аргументы разделены NUL, чтобы Bash не склеивал их.
for item in options + resolved:
    sys.stdout.buffer.write(item.encode() + b"\0")
PY
)

echo "[INFO] Создаю образ SPI Flash..."
"$PYTHON" -m esptool \
    --chip esp32 \
    merge_bin \
    --output "$FLASH_IMAGE" \
    --fill-flash-size 2MB \
    "${MERGE_ARGS[@]}"

if [[ ! -s "$FLASH_IMAGE" ]]; then
    echo "[ERROR] Образ SPI Flash не создан." >&2
    exit 1
fi

echo "[INFO] Образ создан: $FLASH_IMAGE"
echo "[INFO] Запускаю QEMU. Для выхода нажми Ctrl+C."

exec "$QEMU" \
    -nographic \
    -machine esp32 \
    -drive "file=$FLASH_IMAGE,if=mtd,format=raw"
