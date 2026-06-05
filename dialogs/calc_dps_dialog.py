from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QTextBrowser,
    QMessageBox, QFileDialog, QScrollArea, QWidget, QGridLayout)
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QIcon, QFont, QDoubleValidator

import pandas as pd

from data_processing.distribution_plot import DistributionPlot, get_limits_values, extract_parameters_from_data
from data_processing.dps_calculator import DpsCalculatorWorker

from dialogs.ui_helpers.styler import apply_button_style, apply_separator_style
from dialogs.ui_helpers.widgets_builder import (
    create_separator, create_icon_button, button_layout_builder, log_and_progress_bar_builder,
    labeled_combobox_maker, limits_fields_maker, filter_layout_builder)


# --- Глобальные переменные ---
DIAGRAM_IMAGE_PATH = "icons/distribution.png"
HELP_DOCS_PATH = "help_docs/dps.html"
FONT_11 = QFont(); FONT_11.setPointSize(11)
FONT_10 = QFont(); FONT_10.setPointSize(10)


class Ui_DialogCalcDps:
    """
        Класс, отвечающий за создание и настройку пользовательского интерфейса для диалога
        расчета Dps. Все элементы интерфейса и их поведение настраиваются через
        соответствующие методы.
    """
    def setupUi(self, window):
        """Настройка всего интерфейса диалога"""
        self._setup_my_window(window)
        self._setup_layouts(window)
        self._setup_left_layout(window)
        self._setup_right_layout()
        self._setup_main_bass_columns_layout()
        self._setup_nested_bass_columns_layout(window)

    def _setup_my_window(self, window):
        """Установка заголовка и размера окна"""
        window.setWindowTitle("Рассчитать D")
        window.setWindowState(Qt.WindowMaximized)
        self.setWindowIcon(QIcon("icons/main.png"))

    def _setup_layouts(self, parent):
        """Создание основных layout'ов"""
        self.main_layout = QHBoxLayout(parent)
        parent.setLayout(self.main_layout)
        self.left_layout = QVBoxLayout(parent)
        self.main_layout.addLayout(self.left_layout)
        self.right_layout = QVBoxLayout(parent)
        self.main_layout.addLayout(self.right_layout)

    def _setup_left_layout(self, parent):
        """Настройка левого layout'а для фильтрации данных"""
        self.l_title_label = QLabel("Фильтрация данных")
        self.l_title_label.setFont(FONT_11)
        self.left_layout.addWidget(self.l_title_label, alignment=Qt.AlignCenter)

        self.scroll_area = QScrollArea(parent)
        self.scroll_area.setWidgetResizable(True)
        self.left_layout.addWidget(self.scroll_area)

        self.scroll_content = QWidget(parent)
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)

        (self.lower_threshold_percent, self.upper_threshold_persent, self.lower_threshold_percentile,
         self.upper_threshold_percentile, self.lower_threshold_value, self.upper_threshold_value,
         self.bin_nums_spinbox) = filter_layout_builder(self.left_layout)

    def _setup_right_layout(self):
        """Настройка правого layout'а для выбора параметров расчета и настроек фильтрации"""
        # --- Заголовок и кнопка "Справка" --
        header_layout = QHBoxLayout()
        self.r_title_label = QLabel("Выберите имена нужных колонок")
        self.r_title_label.setFont(FONT_11)

        self.help_button = QPushButton("Справка")
        self.help_button.setCheckable(True)
        self.help_button.setFixedWidth(80)

        header_layout.addWidget(self.r_title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.help_button)

        self.right_layout.addLayout(header_layout)

        # --- Создание области выбора колонок главных бассейнов ---
        self.main_bass_columns_layout = QVBoxLayout()
        self.right_layout.addLayout(self.main_bass_columns_layout)

        self.separator1 = create_separator()
        self.right_layout.addWidget(self.separator1)

        # --- Создание области выбора колонок вложенных бассейнов ---
        self.nested_bass_columns_layout = QVBoxLayout()
        self.right_layout.addLayout(self.nested_bass_columns_layout)

        self.separator2 = create_separator()
        self.right_layout.addWidget(self.separator2)

        # --- Создание лога и прогресс бара ---
        self.log_text, self.progress_bar = log_and_progress_bar_builder(self.right_layout)

        # --- Создание основных кнопок ---
        self.cancel_button, self.calculate_button, self.save_button, self.done_button = (
            button_layout_builder(self.right_layout))

    def _setup_main_bass_columns_layout(self):
        """Настройка layout'а виджетов для параметров старших бассейнов"""
        self.main_bass_label = QLabel("Колонки старшего бассейна")
        self.main_bass_label.setFont(FONT_10)
        self.main_bass_columns_layout.addWidget(self.main_bass_label, alignment=Qt.AlignCenter)

        main_id_label = "ID старшего бассейна"
        latitude_label = "Широта (latitude, Y) центроида бассейна"
        longitude_label = "Долгота (longitude, X) центроида бассейна"
        main_perimeter_label = "Периметр старшего бассейна"
        main_area_label = "Площадь старшего бассейна"

        self.perimeter_button = create_icon_button(DIAGRAM_IMAGE_PATH)
        self.area_button = create_icon_button(DIAGRAM_IMAGE_PATH)

        main_id_layout, _, self.main_id_combobox = labeled_combobox_maker(main_id_label)
        self.main_bass_columns_layout.addLayout(main_id_layout)

        latitude_layout, _, self.latitude_combobox = labeled_combobox_maker(latitude_label)
        self.main_bass_columns_layout.addLayout(latitude_layout)

        longitude_layout, _, self.longitude_combobox = labeled_combobox_maker(longitude_label)
        self.main_bass_columns_layout.addLayout(longitude_layout)

        main_perimeter_layout, _, self.main_perimeter_combobox = labeled_combobox_maker(main_perimeter_label)
        self.main_bass_columns_layout.addLayout(main_perimeter_layout)

        perimeter_limits_layout, self.min_main_perimeter, self.max_main_perimeter = limits_fields_maker(
            label_text="диапазон:", stretch=True, min_width=150, btn=self.perimeter_button)
        self.main_bass_columns_layout.addLayout(perimeter_limits_layout)

        main_area_layout, _, self.main_area_combobox = labeled_combobox_maker(main_area_label)
        self.main_bass_columns_layout.addLayout(main_area_layout)

        area_limits_layout, self.min_main_area, self.max_main_area = limits_fields_maker(
            label_text="диапазон:", stretch=True, min_width=150, btn=self.area_button)
        self.main_bass_columns_layout.addLayout(area_limits_layout)

    def _setup_nested_bass_columns_layout(self, parent):
        """Настройка layout'а виджетов для параметров вложенных бассейнов"""
        self.nest_bass_label = QLabel("Колонки вложенных бассейнов")
        self.nest_bass_label.setFont(FONT_10)
        self.nested_bass_columns_layout.addWidget(self.nest_bass_label, alignment=Qt.AlignCenter)

        # --- Создание области прокрутки для вложенных бассейнов
        self.nested_scroll = QScrollArea(parent)
        self.nested_scroll.setWidgetResizable(True)
        self.nested_scroll.setMinimumHeight(300)
        self.nested_bass_columns_layout.addWidget(self.nested_scroll)

        # --- Контейнер для элементов вложенных бассейнов ---
        self.nested_container = QWidget(parent)
        self.nested_layout = QVBoxLayout(self.nested_container)
        self.nested_layout.setAlignment(Qt.AlignTop)
        self.nested_scroll.setWidget(self.nested_container)  # Устанавливаем контейнер в ScrollArea

        # --- Создание кнопок действия со вложенными бассейнами ---
        self.button_row_layout = QHBoxLayout()
        self.add_bass_button = QPushButton("Добавить вложенный бассейн")
        self.remove_bass_button = QPushButton("Удалить последний бассейн")
        self.button_row_layout.addWidget(self.add_bass_button, alignment=Qt.AlignCenter)
        self.button_row_layout.addWidget(self.remove_bass_button, alignment=Qt.AlignCenter)
        self.nested_bass_columns_layout.addLayout(self.button_row_layout)

    def _create_nested_bass_widgets(self):
        """Фабрика для создания набора виджетов вложенного бассейна"""
        layout = QGridLayout()

        # ID
        id_layout, id_label, id_combobox = labeled_combobox_maker("ID:")
        layout.addLayout(id_layout, 0, 0)

        # Perimeter
        perimeter_layout, perimeter_label, perimeter_combobox = labeled_combobox_maker("Perimeter:")
        perimeter_button = create_icon_button(DIAGRAM_IMAGE_PATH)
        perimeter_layout.addWidget(perimeter_button)
        layout.addLayout(perimeter_layout, 0, 1)

        perim_limits_layout, min_perim, max_perim = limits_fields_maker()
        layout.addLayout(perim_limits_layout, 1, 1)

        # Area
        area_layout, area_label, area_combobox = labeled_combobox_maker("Area:")
        area_button = create_icon_button(DIAGRAM_IMAGE_PATH)
        area_layout.addWidget(area_button)
        layout.addLayout(area_layout, 0, 2)

        area_limits_layout, min_area, max_area = limits_fields_maker()
        layout.addLayout(area_limits_layout, 1, 2)

        widgets = {
            "layout": layout,
            "id_label": id_label,
            "id_combobox": id_combobox,
            "perimeter_label": perimeter_label,
            "perimeter_combobox": perimeter_combobox,
            "perimeter_button": perimeter_button,
            "min_perimeter": min_perim,
            "max_perimeter": max_perim,
            "area_label": area_label,
            "area_combobox": area_combobox,
            "area_button": area_button,
            "min_area": min_area,
            "max_area": max_area
        }
        return widgets

    def _remove_nested_bass_widgets(self, bassin_dict:dict):
        """Удаляет виджеты и layout вложенного бассейна"""
        # --- Удаление всех виджетов ---
        for _, widget in bassin_dict.items():
            if isinstance(widget, QWidget):
                widget.deleteLater()

        # --- Удаление layout из основного контейнера ---
        self.nested_layout.removeItem(bassin_dict["layout"])
        bassin_dict["layout"].deleteLater()

class DialogCalcDps(QDialog, Ui_DialogCalcDps):
    def __init__(self, data: pd.DataFrame, parent=None):
        """
            Конструктор для диалога расчета Dps.
            :param data: DataFrame, содержащий исходные данные для расчета
        """
        super().__init__(parent)
        self.setupUi(self)

        self.data: pd.DataFrame = data              # Исходные данные в формате DataFrame
        self.columns = self.data.columns            # Список колонок исходных данных
        self.out_data: pd.DataFrame | None = None   # Данные для вывода, пока не заданы

        # --- Данные для передачи в worker ---
        self.main_id_column: str or None = None         # Колонка с ID старшего бассейна
        self.lat_column: str or None = None             # Колонка с широтой центроида старшего бассейна
        self.long_column: str  or None = None           # Колонка с долготой центроида старшего бассейна
        self.main_perimeter_column: str or None = None  # Колонка с периметром старшего бассейна
        self.main_area_column: str or None = None       # Колонка с площадью старшего бассейна
        self.id_column: list or None = None             # Список с ID вложенных бассейнов
        self.perimeter_column: list or None = None      # Список с периметром вложенных бассейнов
        self.area_column: list or None = None           # Список с площадью вложенных бассейнов
        self.perimeter_limits: list or None = None      # Список с ограничениями [min, max] по периметру
        self.area_limits: list or None = None           # Список с ограничениями [min, max] по площади

        # --- Заполняем combobox названиями колонок из исходного DataFrame ---
        self._fill_comboboxes()

        # --- Инициализируем словарь для динамических полей ---
        self.nested_bass_data: list = []

        # --- Создаем экземпляр DistributionPlot для отображения графика распределения ---
        self.distribution_plot = DistributionPlot()

        # --- Параметры фильтрации ---
        self.bins_num: int or None = None                   # Значение количества интервалов
        self.threshold_percents: list or None = None        # Ограничения [min, max] по проценту от среднего
        self.threshold_percentiles: list or None = None     # Ограничения [min, max] по процентилям
        self.threshold_manual: list or None = None          # Ограничения [min, max] заданные пользователем

        # --- Применяем стиль кнопок и разделителей ---
        apply_button_style([self.cancel_button, self.calculate_button, self.done_button,
                                  self.save_button, self.add_bass_button, self.remove_bass_button,
                                  self.perimeter_button, self.area_button, self.help_button])
        apply_separator_style([self.separator1, self.separator2])

        # --- Связываем кнопки с действиями ---
        self.cancel_button.clicked.connect(self.cancel_calculation)
        self.calculate_button.clicked.connect(self.start_calculation)
        self.save_button.clicked.connect(self.save_results)
        self.done_button.clicked.connect(self.accept)
        self.add_bass_button.clicked.connect(self.add_nested_bass)
        self.remove_bass_button.clicked.connect(self.remove_nested_bass)
        self.perimeter_button.clicked.connect(
            lambda: self.do_distribution_filtration(
                self.main_perimeter_combobox, self.main_id_combobox, "log10(Периметр)"))
        self.area_button.clicked.connect(
            lambda: self.do_distribution_filtration(
                self.main_area_combobox, self.main_id_combobox, "log10(Площадь)"))
        self.help_button.clicked.connect(self.toggle_help_window)

        # --- Устанавливаем состояние кнопок ---
        self.save_button.setEnabled(False)
        self.done_button.setEnabled(False)
        self.remove_bass_button.setEnabled(False)

        # --- Добавляем минимум один вложенный бассейн при инициализации ---
        self.add_nested_bass()

        # --- Флаг состояния потока ---
        self.is_thread_running = False

        # --- Создание форм для отображения фильтрации ---
        self.distribution_plot._update_layout(self.scroll_layout)

    def _fill_comboboxes(self):
        """Заполняет combobox элементами с названиями колонок из DataFrame"""
        self.main_id_combobox.addItems(self.columns)
        self.latitude_combobox.addItems(self.columns)
        self.longitude_combobox.addItems(self.columns)
        self.main_perimeter_combobox.addItems(self.columns)
        self.main_area_combobox.addItems(self.columns)

    def add_nested_bass(self):
        """Добавляет новый набор полей для вложенного бассейна"""
        widgets = self._create_nested_bass_widgets()

        # --- Подключение событий ---
        widgets["perimeter_button"].clicked.connect(
            lambda: self.do_distribution_filtration(
                widgets["perimeter_combobox"], widgets["id_combobox"], "log10(Периметр)"))
        widgets["area_button"].clicked.connect(
            lambda: self.do_distribution_filtration(
                widgets["area_combobox"], widgets["id_combobox"], "log10(Площадь)"))

        # --- Заполнение combobox ---
        widgets["id_combobox"].addItems(self.columns)
        widgets["perimeter_combobox"].addItems(self.columns)
        widgets["area_combobox"].addItems(self.columns)

        # --- Добавление на форму ---
        self.nested_layout.addLayout(widgets["layout"])

        # --- Сохраняем в один словарь для возможности удаления ---
        self.nested_bass_data.append(widgets)

        # --- Активируем кнопку удаления ---
        self.remove_bass_button.setEnabled(True)

        # --- Применяем стиль ---
        apply_button_style([widgets["perimeter_button"], widgets["area_button"]])

    def remove_nested_bass(self):
        """Удаляет последний набор полей для вложенного бассейна"""
        if not self.nested_bass_data:
            return

        # --- Извлекаем последний добавленный набор данных ---
        last_bass = self.nested_bass_data.pop()

        # --- Передаем layout в Ui_DialogCalcDps для удаления виджетов
        self._remove_nested_bass_widgets(last_bass)

        # --- Деактивируем кнопку удаления, если остался только один бассейн ---
        if len(self.nested_bass_data) == 1:
            self.remove_bass_button.setEnabled(False)

    def do_distribution_filtration(self, parameter_column, id_column, x_label:str):
        """
        Выполняет фильтрацию данных на основе заданных параметров и отображает результаты.

        Этот метод собирает параметры фильтрации из пользовательского интерфейса,
        передает их в объект DistributionPlot для обработки и отображает результаты
        фильтрации в виде графиков и текстовых данных.

        :param parameter_column: QComboBox, Виджет выбора колонки с параметром для фильтрации.
        :param id_column: QComboBox, Виджет выбора колонки с идентификатором для фильтрации.

        """
        # --- Получение параметров фильтрации из пользовательского интерфейса ---
        if not self._get_filtration_parameters():
            return

        # --- Получение выбранных колонок для фильтрации ---
        current_column = parameter_column.currentText()
        current_id = id_column.currentText()

        parameters_list = extract_parameters_from_data(self.data, current_id, current_column)

        # --- Передача параметров фильтрации в объект DistributionPlot ---
        self._setup_filtration_parameters(parameters_list, x_label, "Частота")

        # --- Выполнение фильтрации данных и построение графиков ---
        try:
            self.distribution_plot.plot_filtered_data(self.scroll_layout)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при выполнении фильтрации.\n{e}")
            self.distribution_plot.reset_parameters()
            return

        # --- Сброс значений фильтрации в экземпляре DistributionPlot ---
        self.distribution_plot.reset_parameters()

    def _get_filtration_parameters(self):
        """Получение параметров фильтрации из пользовательского интерфейса"""
        try:
            # --- Получение процентных порогов фильтрации ---
            self.threshold_percents = [float(self.lower_threshold_percent.text()),
                                  float(self.upper_threshold_persent.text())]

            # --- Получение квантильных порогов фильтрации ---
            self.threshold_percentiles = [float(self.lower_threshold_percentile.text()),
                                     float(self.upper_threshold_percentile.text())]

            # --- Получение пользовательских границ фильтрации, если они заданы ---
            self.threshold_manual = get_limits_values(self.lower_threshold_value.text(),
                                                       self.upper_threshold_value.text())

            self.bins_num = int(self.bin_nums_spinbox.value())  # Количество интервалов в гистограмме
            return True
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Введены некорректные параметры фильтрации.\n{e}")
            return False

    def _setup_filtration_parameters(self, parameters_list:list, x_label:str, y_label:str):
        """Передача параметров фильтрации в объект DistributionPlot"""
        self.distribution_plot.set_parameters_list(parameters_list)
        self.distribution_plot.set_bins_num(self.bins_num)
        self.distribution_plot.set_percents_values(self.threshold_percents)
        self.distribution_plot.set_percentiles_values(self.threshold_percentiles)
        self.distribution_plot.set_min_max_values(self.threshold_manual)
        self.distribution_plot.set_x_label(x_label)
        self.distribution_plot.set_y_label(y_label)

    def start_calculation(self):
        """Организует запуск процесса расчета"""
        self.out_data = None  # Обновление выходных данных
        self.calculate_button.setEnabled(False)  # Отключение кнопки "Расчет"
        self.save_button.setEnabled(False)  # Отключение кнопки "Сохранить"
        self.done_button.setEnabled(False)  # Отключение кнопки "Готово"
        self.log_text.append("Начинается расчет...")
        self.progress_bar.setValue(0)

        # --- Получение параметров бассейнов ---
        if not self._collect_nested_bass_parameters() or not self._collect_main_bass_parameters():
            self.calculate_button.setEnabled(True)
            return

        # --- Создание потока и экземпляра Worker'а ---
        self._setup_worker_and_thread()

        # --- Запуск потока ---
        self.is_thread_running = True
        self.thread.start()

    def _collect_nested_bass_parameters(self):
        """Собирает параметры вложенных бассейнов. Возвращает True при успехе"""
        try:
            self.id_column = [field["id_combobox"].currentText() for field in self.nested_bass_data]
            self.perimeter_column = [field["perimeter_combobox"].currentText() for field in self.nested_bass_data]
            self.area_column = [field["area_combobox"].currentText() for field in self.nested_bass_data]

            self.perimeter_limits = [
                get_limits_values(field["min_perimeter"].text(), field["max_perimeter"].text())
                for field in self.nested_bass_data
            ]
            self.area_limits = [
                get_limits_values(field["min_area"].text(), field["max_area"].text())
                for field in self.nested_bass_data
            ]

            # --- Проверка корректности выбора колонок ---
            if not len({len(self.id_column), len(self.perimeter_column), len(self.area_column)}) == 1:
                QMessageBox.warning(self, "Пожалуйста, выберите все необходимые колонки.")
                return False

            return True
        except Exception as e:
            QMessageBox.warning(self, "Ошибка обработки параметров вложенных бассейнов", str(e))
            return False

    def _collect_main_bass_parameters(self):
        """Собирает параметры главных бассейнов. Возвращает True при успехе"""
        try:
            self.main_id_column = self.main_id_combobox.currentText()
            self.lat_column = self.latitude_combobox.currentText()
            self.long_column = self.longitude_combobox.currentText()
            self.main_perimeter_column = self.main_perimeter_combobox.currentText()
            self.main_area_column = self.main_area_combobox.currentText()

            # Лимиты главных бассейнов
            main_perimeter_limits = get_limits_values(
                self.min_main_perimeter.text(),
                self.max_main_perimeter.text())
            main_area_limits = get_limits_values(
                self.min_main_area.text(),
                self.max_main_area.text())

            self.perimeter_limits.append(main_perimeter_limits)
            self.area_limits.append(main_area_limits)

            return True
        except Exception as e:
            QMessageBox.warning(self, "Ошибка обработки параметров главных бассейнов", str(e))
            return False

    def _setup_worker_and_thread(self):
        """Создает Worker и поток, подключает сигналы"""
        # --- Создание потока и экземпляра Worker'а ---
        self.thread = QThread(self)
        self.worker = DpsCalculatorWorker()

        # --- Передача параметров Worker'у ---
        self.worker.set_column("main_id_col", self.main_id_column)
        self.worker.set_column("lat_col", self.lat_column)
        self.worker.set_column("long_col", self.long_column)
        self.worker.set_column("main_perimeter_col", self.main_perimeter_column)
        self.worker.set_column("main_area_col", self.main_area_column)

        self.worker.set_perimeter_col(self.perimeter_column)
        self.worker.set_area_col(self.area_column)
        self.worker.set_id_col(self.id_column)
        self.worker.set_perimeter_limits(self.perimeter_limits)
        self.worker.set_area_limits(self.area_limits)

        # --- Подключение сигналов прогресса и ошибок ---
        self.worker.progress_changed.connect(self._update_progress)
        self.worker.error_occurred.connect(self._handle_error)
        self.worker.log_changed.connect(self._update_logs)

        # --- Перемещение worker в поток ---
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(lambda: self.worker.calculate_dps(self.data))

    def cancel_calculation(self):
        """Прерывает выполнение расчета и потока, закрывает диалог"""
        if self.is_thread_running:
            self._stop_thread()
        self.reject()  # Закрыть диалог

    def save_results(self):
        """Сохранение выходного файла"""
        # --- Проверка валидности данных ---
        if self.out_data is None or not isinstance(self.out_data, pd.DataFrame):
            QMessageBox.warning(self, "Ошибка", "Нет данных для сохранения.")
            return

        # --- Получение пути сохранения ---
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить как", "", "CSV Files (*.csv)")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не получить путь сохранения:\n{e}")

        # --- Сохранение данных ---
        if file_path:
            try:
                self.out_data.to_csv(file_path, sep=";", index=False)
                QMessageBox.information(self, "Файл сохранён", f"Файл успешно сохранён в {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")

    def _update_progress(self, value: int, message: str):
        """Обновляет значение прогресс-бара"""
        self.progress_bar.setValue(value)
        self.log_text.append(message)
        if value == 100:
            self.out_data = self.worker.result
            self.log_text.append("Расчет завершен.")
            self.cancel_button.setEnabled(False)
            self.save_button.setEnabled(True)
            self.done_button.setEnabled(True)
            self._stop_thread()

    def _update_logs(self, log_message: str):
        """Обновляет логи"""
        self.log_text.append(log_message)

    def _handle_error(self, error_message: str):
        """Обрабатывает ошибки, отображая их в логах и показывая предупреждение пользователю"""
        self.log_text.append(f"Ошибка: {error_message}")
        QMessageBox.critical(self, "Ошибка", error_message)
        self.calculate_button.setEnabled(True)
        self._stop_thread()

    def _stop_thread(self):
        """Останавливает и очищает поток и worker"""
        if self.is_thread_running and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
            self.worker.deleteLater()  # Безопасное уничтожение worker
            self.thread.deleteLater()  # Безопасное уничтожение потока
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
