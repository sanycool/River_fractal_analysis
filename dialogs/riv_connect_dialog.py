from PyQt5.QtWidgets import (
    QDialog, QLabel, QComboBox, QTextEdit, QProgressBar, QPushButton,
    QHBoxLayout, QVBoxLayout, QMessageBox, QTextBrowser)
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QIcon, QFont

import pandas as pd

from data_processing.river_connector import RiverConnectorWorker

from dialogs.ui_helpers.styler import (apply_button_style, apply_separator_style,
                                       apply_label_style, apply_combobox_style)
from dialogs.ui_helpers.widgets_builder import (
    create_separator, log_and_progress_bar_builder, labeled_combobox_maker, checkbox_field_maker)


# --- Глобальные переменные ---
HELP_DOCS_PATH = "help_docs/connect_segments.html"
FONT_11 = QFont(); FONT_11.setPointSize(11)


class Ui_DialogRivConnect:
    def setupUi(self, window):
        """Настройка всего интерфейса диалога"""
        self._setup_my_window(window)
        self._setup_layout(window)
        self._setup_segments_layout()
        self._setup_segments_length_layout()
        self._setup_button_layout()

    def _setup_my_window(self, window):
        """Установка заголовка и размера окна"""
        window.setWindowTitle("Соединить фрагменты водотоков")
        window.setMinimumSize(550, 500)
        self.setWindowIcon(QIcon("icons/main.png"))

    def _setup_layout(self, window):
        """Создание основного layout'а"""
        self.main_layout = QVBoxLayout(window)
        window.setLayout(self.main_layout)

        # --- Заголовок и кнопка "Справка" --
        header_layout = QHBoxLayout()
        r_title_label = QLabel("Выберите имена нужных колонок")
        r_title_label.setFont(FONT_11)

        self.help_button = QPushButton("Справка")
        self.help_button.setCheckable(True)
        self.help_button.setFixedWidth(80)

        header_layout.addWidget(r_title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.help_button)

        self.main_layout.addLayout(header_layout)

        # --- Создание области выбора колонок сегментов ---
        self.segments_layout = QVBoxLayout()
        self.main_layout.addLayout(self.segments_layout)

        self.separator1 = create_separator()
        self.main_layout.addWidget(self.separator1)

        # --- Создание области выбора колонки с длинами сегментов ---
        self.segments_length_layout = QVBoxLayout()
        self.main_layout.addLayout(self.segments_length_layout)

        self.separator2 = create_separator()
        self.main_layout.addWidget(self.separator2)

        # --- Создание лога и прогресс бара ---
        self.log_text, self.progress_bar = log_and_progress_bar_builder(self.main_layout)

        # --- Создание основных кнопок ---
        self.button_layout = QHBoxLayout()
        self.main_layout.addLayout(self.button_layout)

    def _setup_segments_layout(self):
        grid_code_label = "Колонка порядков сегментов водотоков"
        from_node_label = "Колонка идентификатора начала узла"
        to_node_label = "Колонка идентификатора конца узла"

        grid_code_layout, _, self.grid_code_combobox = labeled_combobox_maker(grid_code_label)
        self.segments_layout.addLayout(grid_code_layout)

        from_node_layout, _, self.from_node_combobox = labeled_combobox_maker(from_node_label)
        self.segments_layout.addLayout(from_node_layout)

        to_node_layout, _, self.to_node_combobox = labeled_combobox_maker(to_node_label)
        self.segments_layout.addLayout(to_node_layout)

    def _setup_segments_length_layout(self):
        self.calculate_length_checkbox = checkbox_field_maker(self.segments_length_layout,
                                                              "Пересчитать длины для соединенных сегментов:",
                                                              reverse=True)
        segments_length_label = "Колонка длин сегментов"
        self.segments_length_h_layout, self.segments_length_label, self.segments_length_combobox = labeled_combobox_maker(segments_length_label)
        self.segments_length_layout.addLayout(self.segments_length_h_layout)

    def _setup_button_layout(self):
        """Создание layout'а основных кнопок"""
        self.cancel_button = QPushButton("Отмена")
        self.calculate_button = QPushButton("Расчет")
        self.done_button = QPushButton("Готово")
        self.button_layout.addWidget(self.cancel_button, alignment=Qt.AlignRight)
        self.button_layout.addWidget(self.calculate_button, alignment=Qt.AlignRight)
        self.button_layout.addWidget(self.done_button, alignment=Qt.AlignRight)

class DialogRivConnect(QDialog, Ui_DialogRivConnect):
    def __init__(self, data: pd.DataFrame, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.data = data  # Исходные данные в формате DataFrame

        # --- Данные для передачи в worker ---
        self.from_node_column: str or None = None
        self.to_node_column: str or None = None
        self.grid_code_column: str or None = None
        self.segments_length_column: str or None = None

        # --- Флаг включения расчета длин соединенных фрагментов ---
        self.calculate_length: bool = False

        # --- Заполняем combobox названиями колонок из исходного DataFrame ---
        self._fill_comboboxes()

        # --- Флаг состояния потока ---
        self.is_thread_running: bool = False

        # --- Применяем стили ---
        apply_button_style([self.cancel_button, self.calculate_button, self.done_button, self.help_button])
        apply_separator_style([self.separator1, self.separator2])
        apply_label_style([self.segments_length_label])
        apply_combobox_style([self.segments_length_combobox])

        # --- Связываем изменение checkbox с действием ---
        self.calculate_length_checkbox.stateChanged.connect(self._toggle_segments_length_section)

        # --- Связываем кнопки с действиями ---
        self.cancel_button.clicked.connect(self.cancel_calculation)
        self.calculate_button.clicked.connect(self.start_calculation)
        self.done_button.clicked.connect(self.accept)
        self.help_button.clicked.connect(self.toggle_help_window)

        # --- Отключение layout'а выбора колонки длины сегментов ---
        self._toggle_segments_length_section(Qt.Unchecked)

        # --- Устанавливаем состояние кнопок ---
        self.done_button.setEnabled(False)

    def _fill_comboboxes(self):
        """Заполняет combobox элементами с названиями колонок из DataFrame."""
        columns = self.data.columns
        self.grid_code_combobox.addItems(columns)
        self.from_node_combobox.addItems(columns)
        self.to_node_combobox.addItems(columns)
        self.segments_length_combobox.addItems(columns)

    def _toggle_segments_length_section(self, state):
        """
        Активирует или деактивирует блок выбора колонки длин сегментов
        в зависимости от состояния чекбокса, обновляя флаг calculate_length
        """
        is_enabled = state == Qt.Checked
        for i in range(self.segments_length_h_layout.count()):
            item = self.segments_length_h_layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.setEnabled(is_enabled)

        self.calculate_length = is_enabled

    def start_calculation(self):
        """Организует запуск процесса расчета"""
        self.calculate_button.setEnabled(False)     # Отключение кнопки "Расчет"
        self.done_button.setEnabled(False)          # Отключение кнопки "Готово"
        self.log_text.append("Начинается расчет...")
        self.progress_bar.setValue(0)

        # --- Получение параметров ---
        if not self._collect_parameters():
            self.calculate_button.setEnabled(True)
            return

        self._setup_worker_and_thread()  # Создание потока и экземпляра Worker'а

        # --- Запуск потока ---
        self.is_thread_running = True
        self.thread.start()

    def _collect_parameters(self) -> bool:
        """Собирает параметры. Возвращает True при успехе"""
        try:
            self.grid_code_column = self.grid_code_combobox.currentText()
            self.from_node_column = self.from_node_combobox.currentText()
            self.to_node_column = self.to_node_combobox.currentText()

            if self.calculate_length:
                self.segments_length_column = self.segments_length_combobox.currentText()

            return True

        except Exception as e:
            QMessageBox.warning(self, "Ошибка обработки параметров", str(e))
            return False

    def _setup_worker_and_thread(self):
        """Создает Worker и поток, подключает сигналы"""
        # --- Создание потока и экземпляра Worker'а ---
        self.thread = QThread(self)
        self.worker = RiverConnectorWorker()

        # --- Передача параметров Worker'у ---
        self.worker.set_from_node_column(self.from_node_column)
        self.worker.set_to_node_column(self.to_node_column)
        self.worker.set_grid_code_column(self.grid_code_column)

        if self.calculate_length:
            self.worker.do_calculate_length(self.calculate_length)
            self.worker.set_segments_length_column(self.segments_length_column)

        # --- Подключение сигналов прогресса и ошибок ---
        self.worker.progress_changed.connect(self._update_progress)
        self.worker.error_occurred.connect(self._handle_error)

        # --- Перемещение worker в поток ---
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(lambda: self.worker.river_data_reorganization(self.data))

    def cancel_calculation(self):
        """Прерывает выполнение расчета и закрывает диалог, если поток был запущен."""
        if self.is_thread_running:
            self._stop_thread()
        self.reject()  # Закрыть диалог

    def _update_progress(self, value, message):
        """Обновляет значение прогресс-бара."""
        self.progress_bar.setValue(value)
        self.log_text.append(message)
        if value == 100:
            self.log_text.append("Расчет завершен.")
            self.cancel_button.setEnabled(False)
            self.done_button.setEnabled(True)
            self.done_button.show()
            self._stop_thread()

    def _handle_error(self, error_message):
        """Обрабатывает ошибки, отображая их в логах и показывая предупреждение пользователю"""
        self.log_text.append(f"Ошибка: {error_message}")
        QMessageBox.critical(self, "Ошибка", error_message)
        self.calculate_button.setEnabled(True)
        self._stop_thread()

    def _stop_thread(self):
        """Останавливает и очищает поток и worker."""
        if self.is_thread_running and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
            self.is_thread_running = False

    def toggle_help_window(self):
        """
        Обрабатывает нажатие на кнопку "Справка":
        - При первом нажатии (состояние кнопки включено) открывает отдельное окно с HTML-справкой.
        - При повторном нажатии (состояние кнопки выключено) закрывает окно справки.

        Окно реализовано как QDialog с QTextBrowser, загружающим HTML-файл справки.
        При закрытии окна вручную сбрасывается состояние кнопки.
        """
        if self.help_button.isChecked():
            self.help_window = QDialog(self)
            self.help_window.setWindowTitle("Справка")
            self.help_window.setMinimumSize(800, 600)

            browser = QTextBrowser(self)
            try:
                with open(HELP_DOCS_PATH, encoding="utf-8") as f:
                    html = f.read()
                    browser.setHtml(html)
            except Exception as e:
                browser.setHtml(f"<p style='color:red;'>Ошибка загрузки справки: {e}</p>")

            browser.setOpenExternalLinks(True)
            browser.setStyleSheet("background-color: #2e2e2e; color: white; padding: 10px;")

            layout = QVBoxLayout(self.help_window)
            layout.addWidget(browser)

            self.help_window.finished.connect(lambda: self.help_button.setChecked(False))
            self.help_window.show()
        else:
            if hasattr(self, "help_window"):
                self.help_window.close()
