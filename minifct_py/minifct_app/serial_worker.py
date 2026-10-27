import json
import time
from PySide6.QtCore import QObject, Signal, Slot
import serial
from serial.tools import list_ports

class SerialWorker(QObject):
    ports_found = Signal(list)
    connected = Signal(str)
    disconnected = Signal()
    message = Signal(str)
    info_received = Signal(dict)
    test_result = Signal(dict)
    run_complete = Signal(dict)
    error = Signal(str)
    finished = Signal()

    def __init__(self):
        super().__init__()
        self._serial = None
        self._running = False

    @Slot()
    def refresh_ports(self):
        ports = [p.device for p in list_ports.comports()]
        self.ports_found.emit(ports)

    @Slot(str, int)
    def connect_port(self, port, baud):
        if self._serial and self._serial.is_open:
            self.disconnect_port()
        try:
            self._serial = serial.Serial(port, baudrate=baud, timeout=0.2, write_timeout=1)
            # Some USB-UART bridges reset the ESP32 when the port opens.
            time.sleep(1.8)
            self._serial.reset_input_buffer()
            self.connected.emit(port)
            self.message.emit(f"Подключено: {port} @ {baud}")
            self.send_command({"cmd": "INFO"})
        except Exception as exc:
            self._serial = None
            self.error.emit(f"Не удалось открыть порт {port}: {exc}")

    @Slot()
    def disconnect_port(self):
        try:
            if self._serial:
                self._serial.close()
        except Exception:
            pass
        self._serial = None
        self.disconnected.emit()
        self.message.emit("Соединение закрыто")

    @Slot(dict)
    def send_command(self, command):
        if not self._serial or not self._serial.is_open:
            self.error.emit("Сначала подключитесь к ESP32.")
            return
        try:
            payload = json.dumps(command, ensure_ascii=False, separators=(",", ":")) + "\n"
            self._serial.write(payload.encode("utf-8"))
            self._serial.flush()
            self.message.emit(f"> {payload.strip()}")
            # Read one JSON-lines response at a time. Firmware emits one line per command.
            deadline = time.monotonic() + 8.0
            while time.monotonic() < deadline:
                raw = self._serial.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                self.message.emit(f"< {line}")
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    self.message.emit("Получена не-JSON строка (возможно, boot log ESP-IDF).")
                    continue
                kind = data.get("type")
                if data.get("device") == "MiniFCT" or "firmware" in data and "tests" in data:
                    self.info_received.emit(data)
                    return
                if kind == "test_result":
                    self.test_result.emit(data)
                    return
                if kind == "run_complete":
                    self.run_complete.emit(data)
                    return
                if data.get("ok") is False:
                    self.error.emit(data.get("error", "Ошибка устройства"))
                    return
                # Accept other response shapes for forward compatibility.
                self.message.emit(f"Ответ устройства: {data}")
                return
            self.error.emit("Тайм-аут ожидания ответа ESP32.")
        except Exception as exc:
            self.error.emit(f"Ошибка последовательного порта: {exc}")

    @Slot()
    def shutdown(self):
        self.disconnect_port()
        self.finished.emit()
