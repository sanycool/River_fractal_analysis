from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QTextBrowser,
    QFileDialog, QSpinBox, QScrollArea, QWidget, QMessageBox)
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QIcon, QFont, QDoubleValidator

import pandas as pd

from data_processing.distribution_plot import (
    DistributionPlot, extract_length_from_data, extract_parameters_from_data, get_limits_values)
from data_processing.sum_av_calculator import DsumAvCalculatorWorker

from dialogs.ui_helpers.styler import apply_button_style, apply_separator_style
from dialogs.ui_helpers.widgets_builder import (
    create_separator, create_icon_button, button_layout_builder, log_and_progress_bar_builder, filter_layout_builder,
    labeled_combobox_maker, limits_fields_maker, checkbox_field_w_limits_maker, layout_cleaner, parameters_fields_changing)


# --- Глобальные переменные ---
DIAGRAM_IMAGE_PATH = "icons/distribution.png"
HELP_DOCS_PATH = "help_docs/dsum_av.html"
FONT_11 = QFont(); FONT_11.setPointSize(11)
FONT_10 = QFont(); FONT_10.setPointSize(10)


class Ui_DialogCalcDsumAv:
    """
        Класс, отвечающий за создание и настройку пользовательского интерфейса для диалога
        расчета Dh sum/ave. Все элементы интерфейса и их поведение настраиваются через
        соответствующие методы.
    """
    def setupUi(self, window):
        """Настройка всего интерфейса диалога"""
        self._setup_my_window(window)
        self._setup_layouts(window)
        self._setup_left_layout(window)
        self._setup_right_layout(window)
        self._setup_main_bass_columns_layout()
        self._setup_river_columns_layout(window)

    def _setup_my_window(self, window):
        """Установка заголовка и размера окна"""
        window.setWindowTitle("Рассчитать D_Hav и D_Hsum")
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

    def _setup_right_layout(self, parent):
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
        self.main_bass_columns_layout = QVBoxLayout(parent)
        self.right_layout.addLayout(self.main_bass_columns_layout)

        self.separator1 = create_separator()
        self.right_layout.addWidget(self.separator1)

        # --- Создание области выбора колонок параметров рек ---
        self.river_column_layout = QVBoxLayout(parent)
        self.right_layout.addLayout(self.river_column_layout)

        self.separator2 = create_separator()
        self.right_layout.addWidget(self.separator2)

        # --- Создание лога и прогресс бара ---
        self.log_text, self.progress_bar = log_and_progress_bar_builder(self.right_layout)

        # --- Создание основных кнопок ---
        self.cancel_button, self.calculate_button, self.save_button, self.done_button = (
            button_layout_builder(self.right_layout))

    def _setup_main_bass_columns_layout(self):
        """Настройка layout'а виджетов для параметров старших бассейнов"""
        self.main_bass_label = QLabel("Колонки параметров бассейнов")
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

    def _setup_river_columns_layout(self, parent):
        """Настройка layout'а виджетов для параметров рек"""
        self.river_label = QLabel("Колонки параметров русел")
        self.river_label.setFont(FONT_10)
        self.river_column_layout.addWidget(self.river_label, alignment=Qt.AlignCenter)

        gridcode_label = "Порядки отрезков рек (grid code)"
        river_id_label = "ID объединенных рек"
        river_length_label = "Длины объединенных рек"

        gridcode_layout, _, self.gridcode_combobox = labeled_combobox_maker(gridcode_label)
        self.river_column_layout.addLayout(gridcode_layout)

        river_id_layout, _, self.river_id_combobox = labeled_combobox_maker(river_id_label)
        self.river_column_layout.addLayout(river_id_layout)

        river_length_layout, _, self.river_length_combobox = labeled_combobox_maker(river_length_label)
        self.river_column_layout.addLayout(river_length_layout)

        self.horizontal_layout = QHBoxLayout()
        self.river_column_layout.addLayout(self.horizontal_layout)

        self.select_gridcode_label = QLabel("Выберите порядки рек для расчетов:")
        self.horizontal_layout.addWidget(self.select_gridcode_label)
        self.horizontal_layout.addStretch()

        self.show_length_distribution_button = QPushButton(
            "Показать графики распределения длин русел для бассейнов")
        self.horizontal_layout.addWidget(self.show_length_distribution_button)

        self.gridcode_scroll_area = QScrollArea(parent)
        self.gridcode_scroll_area.setWidgetResizable(True)
        self.gridcode_scroll_area.setFixedHeight(150)
        self.river_column_layout.addWidget(self.gridcode_scroll_area)

        self.gridcode_scroll_content = QWidget(parent)
        self.gridcode_scroll_layout = QVBoxLayout(self.gridcode_scroll_content)
        self.gridcode_scroll_area.setWidget(self.gridcode_scroll_content)

        self.min_gridcode_num_layout = QHBoxLayout()
        self.river_column_layout.addLayout(self.min_gridcode_num_layout)

        self.min_gridcode_num_layout.addWidget(QLabel("Выберите минимальное количество порядков русел:"))
        self.min_gridcode_num_spinbox = QSpinBox(parent)
        self.min_gridcode_num_spinbox.setMinimum(1)
        self.min_gridcode_num_spinbox.setFixedWidth(50)
        self.min_gridcode_num_layout.addWidget(self.min_gridcode_num_spinbox)
        self.min_gridcode_num_layout.addStretch()

        self.parameters_num_layout = QHBoxLayout()
        self.river_column_layout.addLayout(self.parameters_num_layout)

        self.min_max_parameters_layout = QHBoxLayout()
        self.river_column_layout.addLayout(self.min_max_parameters_layout)


class DialogCalcDsumAv(QDialog, Ui_DialogCalcDsumAv):
    def __init__(self, data: pd.DataFrame, parent=None):
        """
            Конструктор для диалога расчета Dh sum/ave.
            :param data: DataFrame, содержащий исходные данные для расчета
        """
        super().__init__(parent)
        self.setupUi(self)

        self.data: pd.DataFrame = data              # Исходные данные в формате DataFrame
        self.out_data: pd.DataFrame | None = None   # Данные для вывода, пока не заданы

        # --- Данные для передачи в worker ---
        self.main_id_column: str or None = None         # Колонка с ID бассейна
        self.lat_column: str or None = None             # Колонка с широтой центроида
        self.long_column: str or None = None            # Колонка с долготой центроида
        self.main_perimeter_column: str or None = None  # Колонка с периметром бассейна
        self.main_area_column: str or None = None       # Колонка с площадью бассейна
        self.main_perimeter_limits: list or None = None # Ограничения [min, max] по площади
        self.main_area_limits: list or None = None      # Ограничения [min, max] по периметру
        self.grid_code_column: str or None = None       # Колонка с порядком (gridcode)
        self.river_id_column: str or None = None        # Колонка с ID реки
        self.river_length_column: str or None = None    # Колонка с длиной реки
        self.active_ranges: dict or None = None         # Текущие диапазоны выбранных порядков русел
        self.min_gridcode_num: int or None = None       # Минимальное количество точек для аппроксимации

        self.selected_grid_codes: list[int] = []        # Список для хранения выбранных порядков
        self.gridcode_ranges: dict[int, tuple] = {}     # Словарь для хранения диапазонов {gridcode: (min_lineedit, max_lineedit)}

        self.parameters_statistics = {
            "parameters_num": None,
            "parameters_min": None,
            "parameters_max": None,
            "parameters_list": []
        }
        self._parameters_layout_changing()

        # --- Создаем экземпляр DistributionPlot для отображения графика распределения ---
        self.distribution_plot = DistributionPlot()

        # --- Параметры фильтрации ---
        self.bins_num: int or None = None                   # Значение количества интервалов
        self.threshold_percents: list or None = None        # Ограничения [min, max] по проценту от среднего
        self.threshold_percentiles: list or None = None     # Ограничения [min, max] по процентилям
        self.threshold_manual: list or None = None          # Ограничения [min, max] заданные пользователем

        # --- Заполняем combobox названиями колонок из исходного DataFrame ---
        self.fill_comboboxes()

        # --- Применяем стиль кнопок и разделителей ---
        apply_button_style([self.cancel_button, self.calculate_button, self.done_button, self.save_button,
                            self.help_button])
        apply_separator_style([self.separator1, self.separator2])

        # --- Связываем сигналы изменения выбора с действиями ---
        self.gridcode_combobox.currentIndexChanged.connect(self.on_gridcode_changed)
        self.river_id_combobox.currentIndexChanged.connect(self.get_parameters_statistics)
        self.river_length_combobox.currentIndexChanged.connect(self.get_parameters_statistics)
        self.main_id_combobox.currentIndexChanged.connect(self.get_parameters_statistics)

        # --- Связываем кнопки с действиями ---
        self.show_length_distribution_button.clicked.connect(self.do_length_distribution_filtration)
        self.perimeter_button.clicked.connect(
            lambda: self.do_parameter_distribution_filtration(
                self.main_perimeter_combobox, self.main_id_combobox, "log10(Периметр)"))
        self.area_button.clicked.connect(
            lambda: self.do_parameter_distribution_filtration(
                self.main_area_combobox, self.main_id_combobox, "log10(Площадь)"))
        self.cancel_button.clicked.connect(self.cancel_calculation)
        self.calculate_button.clicked.connect(self.start_calculation)
        self.save_button.clicked.connect(self.save_results)
        self.done_button.clicked.connect(self.accept)
        self.help_button.clicked.connect(self.toggle_help_window)

        # --- Флаг состояния потока ---
        self.is_thread_running = False

        # --- Устанавливаем состояние кнопок ---
        self.show_length_distribution_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.done_button.setEnabled(False)

        # --- Создание форм для отображения фильтрации ---
        self.distribution_plot._update_layout(self.scroll_layout)

    def fill_comboboxes(self):
        """Заполняет combobox элементами с названиями колонок из DataFrame"""
        columns = self.data.columns
        self.main_id_combobox.addItems(columns)
        self.latitude_combobox.addItems(columns)
        self.longitude_combobox.addItems(columns)
        self.main_perimeter_combobox.addItems(columns)
        self.main_area_combobox.addItems(columns)

        self.gridcode_combobox.addItems(columns)
        self.river_id_combobox.addItems(columns)
        self.river_length_combobox.addItems(columns)

    def on_gridcode_changed(self):
        """Слот для обработки изменения выбора в gridcode_combobox"""
        self.selected_grid_codes = []

        selected_column = self.gridcode_combobox.currentText()
        if selected_column:
            # --- Очищаем предыдущие виджеты в layout ---
            layout_cleaner(self.gridcode_scroll_layout)

            # --- Получаем уникальные значения из выбранной колонки и сортируем их ---
            unique_values = sorted(self.data[selected_column].unique())

            # --- Добавляем checkbox для каждого уникального значения ---
            for value in unique_values:
                checkbox, value_min, value_max = checkbox_field_w_limits_maker(self.gridcode_scroll_layout, value)
                checkbox.stateChanged.connect(self.on_checkbox_state_changed)  # Подключаем checkbox к обработчику
                self.gridcode_ranges[value] = (value_min, value_max)  # Сохраняем QLineEdit в словарь

        # --- Обновляем данные статистики ---
        self.parameters_statistics = {
            "parameters_num": None,
            "parameters_min": None,
            "parameters_max": None,
            "parameters_list": []
        }

        self._parameters_layout_changing()

    def _get_current_ranges(self):
        """Возвращает актуальный словарь с текущими диапазонами для выбранных gridcodes"""
        current_ranges = {}

        for gridcode in self.selected_grid_codes:
            if gridcode in self.gridcode_ranges:
                min_edit, max_edit = self.gridcode_ranges[gridcode]

                # Получаем значения из QLineEdit (или None, если поле пустое)
                min_val = float(min_edit.text()) if min_edit.text() else None
                max_val = float(max_edit.text()) if max_edit.text() else None

                current_ranges[gridcode] = (min_val, max_val)

        return current_ranges

    def on_checkbox_state_changed(self, state):
        """Слот для обработки изменения состояния checkbox"""
        checkbox = self.sender()
        value = int(checkbox.text())
        if state == Qt.Checked:
            self.selected_grid_codes.append(value)
        else:
            self.selected_grid_codes.remove(value)

        # --- Обновляем состояние кнопки ---
        self.update_distribution_button_state()

        # --- Обновляем данные статистики ---
        self.get_parameters_statistics()

    def update_distribution_button_state(self):
        """Обновляет состояние кнопки show_length_distribution_button на основе условий"""
        self.show_length_distribution_button.setEnabled(len(self.selected_grid_codes) > 0)

    def _parameters_layout_changing(self):
        """Метод для изменения виджетов отображения статистики параметров"""
        error_str = parameters_fields_changing(self.parameters_num_layout, self.min_max_parameters_layout,
                                          self.parameters_statistics["parameters_num"],
                                          self.parameters_statistics["parameters_min"],
                                          self.parameters_statistics["parameters_max"])
        if error_str:
            QMessageBox.warning(self, "Ошибка", f"Ошибка отображения параметров статистики:\n{error_str}")
            return

    def get_parameters_statistics(self):
        bass_id_col = self.main_id_combobox.currentText()
        grid_code_col = self.gridcode_combobox.currentText()
        river_id_col = self.river_id_combobox.currentText()
        river_length_col = self.river_length_combobox.currentText()

        length_list = extract_length_from_data(self.data, bass_id_col, river_id_col, river_length_col, grid_code_col,
                                               self.selected_grid_codes)

        try:
            self.parameters_statistics["parameters_num"] = len(length_list) if length_list else None
            self.parameters_statistics["parameters_min"] = min(length_list) if length_list else None
            self.parameters_statistics["parameters_max"] = max(length_list) if length_list else None
            self.parameters_statistics["parameters_list"] = length_list if length_list else None
        except Exception as e:
            QMessageBox(self, "Ошибка", f"Ошибка при получении статистики:\n{e}")
            return

        self._parameters_layout_changing()

    def do_parameter_distribution_filtration(self, parameter_column:str, id_column:str, x_label:str):
        """
        Создает график распределения периметров/площадей бассейнов с фильтрацией.

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

    def do_length_distribution_filtration(self):
        """
        Создает график распределения длин русел с фильтрацией.

        Этот метод собирает параметры распределения из пользовательского интерфейса
        и self.parameters_statistics, передает их в объект DistributionPlot для обработки
        и дальнейшего отображения в виде графиков.
        """
        if not self.parameters_statistics["parameters_list"]:
            QMessageBox(self, "Ошибка", "Нет данных для построения гистограммы распределения!")
            return

        # --- Получение параметров фильтрации из пользовательского интерфейса ---
        if not self._get_filtration_parameters():
            return

        # --- Передача параметров фильтрации в объект DistributionPlot ---
        self._setup_filtration_parameters(self.parameters_statistics["parameters_list"], "log10(Длина)", "Частота")

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
        if not self.selected_grid_codes:
            QMessageBox.warning(self, "Ошибка", "Не выбран ни один порядок русел!")
            return

        self.out_data = None                        # Обновление выходных данных
        self.calculate_button.setEnabled(False)     # Отключение кнопки "Расчет"
        self.save_button.setEnabled(False)          # Отключение кнопки "Сохранить"
        self.done_button.setEnabled(False)          # Отключение кнопки "Готово"
        self.log_text.append("Начинается расчет длин отрезков...")
        self.progress_bar.setValue(0)

        # --- Получение параметров бассейнов ---
        if not self._collect_parameters():
            self.calculate_button.setEnabled(True)
            return

        self._setup_worker_and_thread()  # Создание потока и экземпляра Worker'а

        # --- Запуск потока ---
        self.is_thread_running = True
        self.thread.start()

    def _collect_parameters(self):
        """Собирает параметры главных бассейнов. Возвращает True при успехе"""
        try:
            # Параметры главных бассейнов
            self.main_id_column = self.main_id_combobox.currentText()
            self.lat_column = self.latitude_combobox.currentText()
            self.long_column = self.longitude_combobox.currentText()
            self.main_perimeter_column = self.main_perimeter_combobox.currentText()
            self.main_area_column = self.main_area_combobox.currentText()

            # Лимиты главных бассейнов
            self.main_perimeter_limits = self._get_limits_values(
                self.min_main_perimeter.text(),
                self.max_main_perimeter.text())
            self.main_area_limits = self._get_limits_values(
                self.min_main_area.text(),
                self.max_main_area.text())

            # Параметры русел
            self.grid_code_column = self.gridcode_combobox.currentText()
            self.river_id_column = self.river_id_combobox.currentText()
            self.river_length_column = self.river_length_combobox.currentText()
            self.min_gridcode_num = self.min_gridcode_num_spinbox.value()

            # Получаем текущие диапазоны для выбранных grid_codes
            self.active_ranges = self._get_current_ranges()

            return True
        except Exception as e:
            QMessageBox.warning(self, "Ошибка обработки параметров главных бассейнов", str(e))
            return False

    def _setup_worker_and_thread(self):
        """Создает Worker и поток, подключает сигналы"""
        # --- Создание потока и экземпляра Worker'а ---
        self.thread = QThread(self)
        self.worker = DsumAvCalculatorWorker()

        # --- Передача параметров Worker'у ---
        self.worker.set_bass_id_col(self.main_id_column)
        self.worker.set_lat_col(self.lat_column)
        self.worker.set_long_col(self.long_column)
        self.worker.set_perimeter_col(self.main_perimeter_column)
        self.worker.set_area_col(self.main_area_column)
        self.worker.set_area_limits(self.main_area_limits)
        self.worker.set_perimeter_limits(self.main_perimeter_limits)

        self.worker.set_gridcode_col(self.grid_code_column)
        self.worker.set_river_id_col(self.river_id_column)
        self.worker.set_river_length_col(self.river_length_column)
        self.worker.set_selected_gridcodes(self.selected_grid_codes)
        self.worker.set_gridcode_ranges(self.active_ranges)

        self.worker.set_min_gridcode_num(self.min_gridcode_num)

        # --- Подключение сигналов прогресса и ошибок ---
        self.worker.progress_changed.connect(self._update_progress)
        self.worker.error_occurred.connect(self._handle_error)
        self.worker.log_changed.connect(self._update_logs)

        # --- Перемещение worker в поток ---
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(lambda: self.worker.calculate_dsum_av(self.data))

    def _get_limits_values(self, min_value, max_value) -> list:
        """
        Преобразует строковые значения минимального и максимального порогов в числа (float).
        Если преобразование невозможно, возвращает None для соответствующих значений.
        """
        try:
            # Преобразуем строки в числа с плавающей точкой
            low_value = float(min_value) if min_value else None
            upper_value = float(max_value) if max_value else None
        except ValueError:
            # В случае ошибки возвращаем None
            low_value, upper_value = None, None

        return [low_value, upper_value]

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
