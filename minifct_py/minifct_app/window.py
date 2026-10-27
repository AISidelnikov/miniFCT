import csv
import json
import os
from datetime import datetime, timezone

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QTextEdit, QFileDialog, QMessageBox, QGroupBox,
    QHeaderView
)

from .serial_worker import SerialWorker

class MainWindow(QMainWindow):
    request_refresh = Signal()
    request_connect = Signal(str, int)
    request_disconnect = Signal()
    request_command = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MiniFCT — Functional Test Console")
        self.resize(980, 700)
        self._connected = False
        self._current_results = []
        self._run_started = None

        self.thread = QThread(self)
        self.worker = SerialWorker()
        self.worker.moveToThread(self.thread)
        self.thread.start()

        self.request_refresh.connect(self.worker.refresh_ports)
        self.request_connect.connect(self.worker.connect_port)
        self.request_disconnect.connect(self.worker.disconnect_port)
        self.request_command.connect(self.worker.send_command)

        self.worker.ports_found.connect(self.on_ports)
        self.worker.connected.connect(self.on_connected)
        self.worker.disconnected.connect(self.on_disconnected)
        self.worker.message.connect(self.log)
        self.worker.info_received.connect(self.on_info)
        self.worker.test_result.connect(self.on_test_result)
        self.worker.run_complete.connect(self.on_run_complete)
        self.worker.error.connect(self.on_error)

        self._build_ui()
        self.request_refresh.emit()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        connection_box = QGroupBox("Подключение к тестеру")
        connection = QHBoxLayout(connection_box)
        self.port_combo = QComboBox()
        self.refresh_button = QPushButton("Обновить порты")
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["115200", "921600"])
        self.connect_button = QPushButton("Подключить")
        self.disconnect_button = QPushButton("Отключить")
        self.disconnect_button.setEnabled(False)
        connection.addWidget(QLabel("COM-порт:"))
        connection.addWidget(self.port_combo, 1)
        connection.addWidget(self.refresh_button)
        connection.addWidget(QLabel("Скорость:"))
        connection.addWidget(self.baud_combo)
        connection.addWidget(self.connect_button)
        connection.addWidget(self.disconnect_button)
        layout.addWidget(connection_box)

        info_box = QGroupBox("Изделие и запуск")
        form = QFormLayout(info_box)
        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText("Например, MFCT-2026-000001")
        self.serial_input.setText(self._suggest_serial())
        self.operator_input = QLineEdit()
        self.operator_input.setPlaceholderText("Необязательно")
        self.product_input = QLineEdit()
        self.product_input.setPlaceholderText("Модель / ревизия платы")
        form.addRow("Серийный номер изделия *:", self.serial_input)
        form.addRow("Модель / ревизия:", self.product_input)
        form.addRow("Оператор:", self.operator_input)
        layout.addWidget(info_box)

        actions = QHBoxLayout()
        self.info_button = QPushButton("Получить INFO")
        self.info_button.setEnabled(False)
        self.run_all_button = QPushButton("▶ Запустить все тесты")
        self.run_all_button.setMinimumHeight(42)
        self.run_all_button.setEnabled(False)
        self.save_button = QPushButton("Сохранить отчёт CSV…")
        self.save_button.setEnabled(False)
        actions.addWidget(self.info_button)
        actions.addWidget(self.run_all_button, 1)
        actions.addWidget(self.save_button)
        layout.addLayout(actions)

        self.status_label = QLabel("Статус: не подключено")
        self.status_label.setStyleSheet("font-weight: bold; padding: 6px;")
        layout.addWidget(self.status_label)

        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(
            ["Тест", "Результат", "Значение", "Единицы", "Сообщение"]
        )
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.results_table.setAlternatingRowColors(True)
        layout.addWidget(self.results_table, 1)

        log_box = QGroupBox("Журнал обмена")
        log_layout = QVBoxLayout(log_box)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(150)
        log_layout.addWidget(self.log_view)
        layout.addWidget(log_box)

        self.refresh_button.clicked.connect(self.request_refresh.emit)
        self.connect_button.clicked.connect(self.connect_device)
        self.disconnect_button.clicked.connect(self.request_disconnect.emit)
        self.info_button.clicked.connect(lambda: self.request_command.emit({"cmd": "INFO"}))
        self.run_all_button.clicked.connect(self.run_all)
        self.save_button.clicked.connect(self.save_report)

    @staticmethod
    def _suggest_serial():
        return "MFCT-" + datetime.now().strftime("%Y%m%d-%H%M%S")

    @Slot(list)
    def on_ports(self, ports):
        current = self.port_combo.currentText()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        if current in ports:
            self.port_combo.setCurrentText(current)
        if not ports:
            self.log("COM-порты не найдены. Проверьте USB-кабель и драйвер CP210x/CH340.")

    def connect_device(self):
        port = self.port_combo.currentText().strip()
        if not port:
            QMessageBox.warning(self, "Нет COM-порта", "Выберите COM-порт ESP32.")
            return
        self.request_connect.emit(port, int(self.baud_combo.currentText()))

    @Slot(str)
    def on_connected(self, port):
        self._connected = True
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.run_all_button.setEnabled(True)
        self.info_button.setEnabled(True)
        self.status_label.setText(f"Статус: подключено к {port}; ожидание данных устройства")

    @Slot()
    def on_disconnected(self):
        self._connected = False
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.run_all_button.setEnabled(False)
        self.info_button.setEnabled(False)
        self.status_label.setText("Статус: не подключено")

    @Slot(dict)
    def on_info(self, data):
        self._firmware = data.get("firmware", "")
        self.status_label.setText(
            f"Статус: подключено · устройство {data.get('device', 'MiniFCT')} · "
            f"прошивка {data.get('firmware', 'неизвестна')}"
        )
        tests = data.get("tests", [])
        if tests:
            self.log("Доступные тесты: " + ", ".join(map(str, tests)))

    def run_all(self):
        serial_number = self.serial_input.text().strip()
        if not serial_number:
            QMessageBox.warning(self, "Нужен серийный номер", "Введите серийный номер изделия.")
            self.serial_input.setFocus()
            return
        if not self._connected:
            QMessageBox.warning(self, "Нет подключения", "Сначала подключите тестер.")
            return
        self._current_results = []
        self._run_started = datetime.now(timezone.utc).astimezone()
        self.results_table.setRowCount(0)
        self.run_all_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.status_label.setText(f"Статус: тестирование изделия {serial_number}…")
        self.request_command.emit({"cmd": "RUN_ALL"})

    @Slot(dict)
    def on_test_result(self, data):
        self._add_result(data)
        passed = bool(data.get("passed", False))
        self.status_label.setText("Статус: тест пройден" if passed else "Статус: тест FAIL")
        self.run_all_button.setEnabled(self._connected)
        self.save_button.setEnabled(bool(self._current_results))

    @Slot(dict)
    def on_run_complete(self, data):
        results = data.get("results", [])
        self._current_results = []
        for row in results:
            self._add_result(row)
        total = data.get("total_count", len(results))
        passed_count = data.get("passed_count", sum(1 for r in results if r.get("passed")))
        all_passed = bool(data.get("passed", False))
        verdict = "PASS" if all_passed else "FAIL"
        self.status_label.setText(f"Итог: {verdict} · пройдено {passed_count}/{total}")
        self.run_all_button.setEnabled(self._connected)
        self.save_button.setEnabled(bool(results))
        self.log(f"RUN_ALL завершён: {verdict}, {passed_count}/{total}")

    def _add_result(self, result):
        self._current_results.append(result)
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        passed = bool(result.get("passed", False))
        values = [
            str(result.get("test", "")),
            "PASS" if passed else "FAIL",
            str(result.get("value", "")),
            str(result.get("unit", "")),
            str(result.get("message", "")),
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if col == 1:
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(Qt.darkGreen if passed else Qt.red)
            self.results_table.setItem(row, col, item)

    def save_report(self):
        if not self._current_results:
            QMessageBox.information(self, "Нет результатов", "Сначала запустите тесты.")
            return
        serial_number = self.serial_input.text().strip()
        safe_serial = "".join(c if c.isalnum() or c in "-_." else "_" for c in serial_number)
        suggested = f"MiniFCT_{safe_serial}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчёт", os.path.join(os.path.expanduser("~"), "Documents", suggested),
            "CSV (*.csv)"
        )
        if not path:
            return
        started = self._run_started.isoformat(timespec="seconds") if self._run_started else ""
        all_passed = all(bool(r.get("passed", False)) for r in self._current_results)
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "serial_number", "product", "operator", "timestamp",
                        "firmware", "overall_result", "test", "passed",
                        "value", "unit", "message"
                    ],
                    extrasaction="ignore"
                )
                writer.writeheader()
                for result in self._current_results:
                    writer.writerow({
                        "serial_number": serial_number,
                        "product": self.product_input.text().strip(),
                        "operator": self.operator_input.text().strip(),
                        "timestamp": started,
                        "firmware": getattr(self, "_firmware", ""),
                        "overall_result": "PASS" if all_passed else "FAIL",
                        "test": result.get("test", ""),
                        "passed": bool(result.get("passed", False)),
                        "value": result.get("value", ""),
                        "unit": result.get("unit", ""),
                        "message": result.get("message", ""),
                    })
            QMessageBox.information(self, "Отчёт сохранён", f"Файл сохранён:\n{path}")
            self.log(f"Отчёт сохранён: {path}")
        except OSError as exc:
            QMessageBox.critical(self, "Ошибка сохранения", str(exc))

    @Slot(str)
    def on_error(self, message):
        self.log("ОШИБКА: " + message)
        self.status_label.setText("Статус: ошибка")
        self.run_all_button.setEnabled(self._connected)

    @Slot(str)
    def log(self, message):
        self.log_view.append(message)

    @Slot()
    def closeEvent(self, event):
        try:
            self.request_disconnect.emit()
            self.thread.quit()
            self.thread.wait(2000)
        except Exception:
            pass
        event.accept()
