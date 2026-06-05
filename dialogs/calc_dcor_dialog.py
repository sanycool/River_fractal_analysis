from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QLineEdit,
    QFileDialog, QSpinBox, QScrollArea, QWidget, QMessageBox, QTextBrowser)
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QIcon, QFont, QDoubleValidator

import pandas as pd

from data_processing.distribution_plot import (
    DistributionPlot, extract_parameters_from_data, get_limits_values)
from data_processing.dcor_calculator import DcorCalculatorWorker

from dialogs.ui_helpers.styler import (apply_button_style, apply_separator_style,
                                       apply_spin_boxes_style, apply_label_style)
from dialogs.ui_helpers.widgets_builder import (
    create_separator, create_icon_button, button_layout_builder, log_and_progress_bar_builder, filter_layout_builder,
    labeled_combobox_maker, limits_fields_maker, checkbox_field_maker, layout_cleaner, parameters_fields_changing)


# --- Глобальные переменные ---
HELP_DOCS_PATH = "help_docs/dcor.html"
FONT_11 = QFont(); FONT_11.setPointSize(11)
FONT_10 = QFont(); FONT_10.setPointSize(10)
DOUBLE_VALIDATOR = QDoubleValidator(1, 1e10, 5)  # Валидатор


class Ui_DialogCalcDcorAv:
    """
    Класс, отвечающий за создание и настройку пользовательского интерфейса для диалога
    расчета D_cor. Все элементы интерфейса и их поведение настраиваются через
    соответствующие методы.
    """
    def setupUi(self, window):
        """Настройка всего интерфейса диалога"""
        self._setup_my_window(window)
        self._setup_layouts(window)
        self._setup_left_layout(window)
        self._setup_right_layout(window)
        self._setup_main_bass_columns_layout()
        self._setup_nodes_columns_layout(window)
        self._setup_calculation_parameters_layout(window)

    def _setup_my_window(self, window):
        """Установка заголовка и размера окна"""
        window.setWindowTitle("Рассчитать D_cor")
        self.setWindowIcon(QIcon("icons/main.png"))
        # window.setWindowState(Qt.WindowMaximized)

    def _setup_layouts(self, parent):
        """Создание основного layout'а"""
        self.main_layout = QHBoxLayout(parent)
        parent.setLayout(self.main_layout)
        self.left_layout = QVBoxLayout(parent)
        self.main_layout.addLayout(self.left_layout)
        self.right_layout = QVBoxLayout(parent)
        self.main_layout.addLayout(self.right_layout)

    def _setup_left_layout(self, parent):
        """Настройка левого layout'а для фильтрации данных"""
        # --- Заголовок и кнопка "Справка" --
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Настройка расчетов")
        self.title_label.setFont(FONT_11)

        self.help_button = QPushButton("Справка")
        self.help_button.setCheckable(True)
        self.help_button.setFixedWidth(80)

        header_layout.addWidget(self.help_button)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.left_layout.addLayout(header_layout)

        # --- Создание области выбора колонок главных бассейнов ---
        self.main_bass_columns_layout = QVBoxLayout(parent)
        self.left_layout.addLayout(self.main_bass_columns_layout)

        self.separator1 = create_separator()
        self.left_layout.addWidget(self.separator1)

        # --- Создание области настроек расчетов ---
        self.calculation_parameters_layout = QVBoxLayout(parent)
        self.left_layout.addLayout(self.calculation_parameters_layout)

        self.separator2 = create_separator()
        self.left_layout.addWidget(self.separator2)

        self.left_layout.addStretch()


    def _setup_right_layout(self, parent):
        """Настройка правого layout'а для выбора параметров расчета и настроек фильтрации"""
        # --- Создание области выбора колонок для параметров точек бифуркации ---
        self.nodes_column_layout = QVBoxLayout(parent)
        self.right_layout.addLayout(self.nodes_column_layout)

        self.separator3 = create_separator()
        self.right_layout.addWidget(self.separator3)

        # --- Создание лога и прогресс бара ---
        self.log_text, self.progress_bar = log_and_progress_bar_builder(self.right_layout)

        # --- Создание основных кнопок ---
        self.cancel_button, self.calculate_button, self.save_button, self.done_button = (
            button_layout_builder(self.right_layout))

    def _setup_main_bass_columns_layout(self):
        """Настройка layout'а виджетов для параметров старших бассейнов"""
        main_bass_label = QLabel("Колонки параметров бассейнов")
        main_bass_label.setFont(FONT_10)
        self.main_bass_columns_layout.addWidget(main_bass_label, alignment=Qt.AlignCenter)

        main_id_label = "ID старшего бассейна"
        latitude_label = "Широта (latitude, Y) центроида бассейна"
        longitude_label = "Долгота (longitude, X) центроида бассейна"
        main_perimeter_label = "Периметр старшего бассейна"
        main_area_label = "Площадь старшего бассейна"

        # self.perimeter_button = create_icon_button(DIAGRAM_IMAGE_PATH)
        # self.area_button = create_icon_button(DIAGRAM_IMAGE_PATH)

        main_id_layout, _, self.main_id_combobox = labeled_combobox_maker(main_id_label)
        self.main_bass_columns_layout.addLayout(main_id_layout)

        latitude_layout, _, self.latitude_combobox = labeled_combobox_maker(latitude_label)
        self.main_bass_columns_layout.addLayout(latitude_layout)

        longitude_layout, _, self.longitude_combobox = labeled_combobox_maker(longitude_label)
        self.main_bass_columns_layout.addLayout(longitude_layout)

        main_perimeter_layout, _, self.main_perimeter_combobox = labeled_combobox_maker(main_perimeter_label)
        self.main_bass_columns_layout.addLayout(main_perimeter_layout)

        perimeter_limits_layout, self.min_main_perimeter, self.max_main_perimeter = limits_fields_maker(
            label_text="диапазон:", stretch=True, min_width=150)
        self.main_bass_columns_layout.addLayout(perimeter_limits_layout)

        main_area_layout, _, self.main_area_combobox = labeled_combobox_maker(main_area_label)
        self.main_bass_columns_layout.addLayout(main_area_layout)

        area_limits_layout, self.min_main_area, self.max_main_area = limits_fields_maker(
            label_text="диапазон:", stretch=True, min_width=150)
        self.main_bass_columns_layout.addLayout(area_limits_layout)

    def _setup_nodes_columns_layout(self, parent):
        """Настройка layout'а виджетов для параметров точек бифуркации"""
        nodes_label = QLabel("Колонки параметров точек бифуркации")
        nodes_label.setFont(FONT_10)
        self.nodes_column_layout.addWidget(nodes_label, alignment=Qt.AlignCenter)

        node_id_label = "ID точек бифуркации"
        node_lat_label = "Широта (latitude, Y) точек бифуркации"
        node_long_label = "Долгота (longitude, X) точек бифуркации"
        node_grid_code_label = "Порядки точек бифуркации (grid code)"

        node_id_layout, _, self.node_id_combobox = labeled_combobox_maker(node_id_label)
        self.nodes_column_layout.addLayout(node_id_layout)

        node_lat_layout, _, self.node_lat_combobox = labeled_combobox_maker(node_lat_label)
        self.nodes_column_layout.addLayout(node_lat_layout)

        node_long_layout, _, self.node_long_combobox = labeled_combobox_maker(node_long_label)
        self.nodes_column_layout.addLayout(node_long_layout)

        node_grid_code_layout, _, self.node_grid_code_combobox = labeled_combobox_maker(node_grid_code_label)
        self.nodes_column_layout.addLayout(node_grid_code_layout)

        self.nodes_column_layout.addWidget(QLabel("Выберите порядки рек для расчетов:"))

        gridcode_scroll_area = QScrollArea(parent)
        gridcode_scroll_area.setWidgetResizable(True)
        gridcode_scroll_area.setFixedHeight(70)
        self.nodes_column_layout.addWidget(gridcode_scroll_area)

        gridcode_scroll_content = QWidget(parent)
        self.gridcode_scroll_layout = QHBoxLayout(gridcode_scroll_content)
        gridcode_scroll_area.setWidget(gridcode_scroll_content)

        min_nodes_num_layout = QHBoxLayout()
        self.nodes_column_layout.addLayout(min_nodes_num_layout)

        min_nodes_num_layout.addWidget(QLabel("Минимальное число точек бифуркации:"))
        self.min_nodes_num_spinbox = QSpinBox(parent)
        self.min_nodes_num_spinbox.setMinimum(1)
        self.min_nodes_num_spinbox.setMaximum(int(1e9))
        self.min_nodes_num_spinbox.setValue(4)
        self.min_nodes_num_spinbox.setFixedWidth(70)
        min_nodes_num_layout.addWidget(self.min_nodes_num_spinbox)
        min_nodes_num_layout.addStretch()

        self.nodes_column_layout.addWidget(QLabel("Выберите критически важные порядки точек бифуркации:"))

        target_gridcode_scroll_area = QScrollArea(parent)
        target_gridcode_scroll_area.setWidgetResizable(True)
        target_gridcode_scroll_area.setFixedHeight(70)
        self.nodes_column_layout.addWidget(target_gridcode_scroll_area)

        target_gridcode_scroll_content = QWidget(parent)
        self.target_gridcode_scroll_layout = QHBoxLayout(target_gridcode_scroll_content)
        target_gridcode_scroll_area.setWidget(target_gridcode_scroll_content)

        min_target_grid_codes_num_layout = QHBoxLayout()
        self.nodes_column_layout.addLayout(min_target_grid_codes_num_layout)

        self.min_target_grid_codes_num_label = QLabel("Минимальное число критических порядков точек бифуркации:")
        min_target_grid_codes_num_layout.addWidget(self.min_target_grid_codes_num_label)

        self.min_target_grid_codes_spinbox = QSpinBox(parent)
        self.min_target_grid_codes_spinbox.setMinimum(1)
        self.min_target_grid_codes_spinbox.setFixedWidth(70)
        min_target_grid_codes_num_layout.addWidget(self.min_target_grid_codes_spinbox)

        self.all_target_checkbox = checkbox_field_maker(min_target_grid_codes_num_layout,
                                                          "Все выбранные", reverse=True)
        min_target_grid_codes_num_layout.addStretch()

    def _setup_calculation_parameters_layout(self, parent):
        """Настройка layout'а виджетов для параметров расчетов"""
        calculation_parameters_label = QLabel("Настройки вычислений")
        calculation_parameters_label.setFont(FONT_10)
        self.calculation_parameters_layout.addWidget(calculation_parameters_label, alignment=Qt.AlignCenter)

        scale_step_layout = QHBoxLayout()
        self.calculation_parameters_layout.addLayout(scale_step_layout)

        scale_step_layout.addWidget(QLabel("Шаг масштаба r (в метрах):"))
        self.scale_step_spinbox = QSpinBox(parent)
        self.scale_step_spinbox.setMinimum(1)
        self.scale_step_spinbox.setMaximum(int(1e9))
        self.scale_step_spinbox.setValue(1000)
        self.scale_step_spinbox.setFixedWidth(70)
        scale_step_layout.addWidget(self.scale_step_spinbox)
        scale_step_layout.addStretch()

        min_approximation_interval_layout = QHBoxLayout()
        self.calculation_parameters_layout.addLayout(min_approximation_interval_layout)

        self.min_approximation_interval_label = QLabel("Минимальный интервал аппроксимации:")
        min_approximation_interval_layout.addWidget(self.min_approximation_interval_label)

        self.min_approximation_interval_spinbox = QSpinBox(parent)
        self.min_approximation_interval_spinbox.setMinimum(3)
        self.min_approximation_interval_spinbox.setValue(4)
        self.min_approximation_interval_spinbox.setFixedWidth(70)
        min_approximation_interval_layout.addWidget(self.min_approximation_interval_spinbox)

        self.all_interval_checkbox = checkbox_field_maker(min_approximation_interval_layout,
                                                          "Использовать весь интервал", reverse=True)
        min_approximation_interval_layout.addStretch()

        earth_radius_layout = QHBoxLayout()
        self.calculation_parameters_layout.addLayout(earth_radius_layout)

        earth_radius_layout.addWidget(QLabel("Радиус Земли для исследуемой области (в километрах):"))
        self.earth_radius_line = QLineEdit()
        self.earth_radius_line.setText("6371")
        self.earth_radius_line.setPlaceholderText("km")
        self.earth_radius_line.setValidator(DOUBLE_VALIDATOR)
        earth_radius_layout.addWidget(self.earth_radius_line)


class DialogCalcDcor(QDialog, Ui_DialogCalcDcorAv):
    def __init__(self, data: pd.DataFrame, parent=None):
        """
            Конструктор для диалога расчета D cor.
            :param data: DataFrame, содержащий исходные данные для расчета
        """
        super().__init__(parent)
        self.setupUi(self)

        self.data: pd.DataFrame = data             # Исходные данные в формате DataFrame
        self.out_data: pd.DataFrame | None = None  # Данные для вывода, пока не заданы

        # --- Данные для передачи в worker ---
        self.main_id_column: str | None = None             # Колонка с ID бассейна
        self.lat_column: str | None = None                 # Колонка с широтой центроида
        self.long_column: str | None = None                # Колонка с долготой центроида
        self.main_perimeter_column: str | None = None      # Колонка с периметром бассейна
        self.main_area_column: str | None = None           # Колонка с площадью бассейна
        self.main_perimeter_limits: list | None = None     # Ограничения [min, max] по площади
        self.main_area_limits: list | None = None          # Ограничения [min, max] по периметру

        self.node_id_column: str | None = None             # Колонка с ID точки бифуркации
        self.node_lat_column: str | None = None            # Колонка с широтой точки бифуркации
        self.node_long_column: str | None = None           # Колонка с долготой точки бифуркации
        self.node_grid_code_col: str | None = None         # Колонка с порядком точки бифуркации
        self.min_nodes_num: int | None = None              # Минимальное число точек бифуркации
        self.min_target_grid_codes: int | None = None      # Минимальное число критических порядков
        self.scale_step_num: int | None = None             # Значение шага масштабов r (в метрах)
        self.min_approximation_interval: int | None = None # Значение минимального интервала аппроксимации
        self.earth_radius_value: float = 6371.0            # Значение радиуса Земли в области исследования (в км)

        self.selected_grid_codes: list[int] = []            # Список для хранения выбранных порядков
        self.target_grid_codes: list[int] = []              # Список для хранения выбранных критических порядков

        # --- Словари соответствий checkbox'ов по gridcode ---
        self.checkbox_map: dict[int, QtWidgets.QCheckBox] = {}          # Соответствие значений и обычных checkbox'ов
        self.target_checkbox_map: dict[int, QtWidgets.QCheckBox] = {}   # Соответствие значений и target-checkbox'ов

        # --- Флаг наличия минимального интервала аппроксимации ---
        self.use_full_interval = False

        # --- Флаг учета всех выбранных критических порядков точек бифуркации ---
        self.require_all_target_codes = False

        # --- Заполняем combobox названиями колонок из исходного DataFrame ---
        self.fill_comboboxes()

        # --- Применяем стиль кнопок, разделителей и счетчиков---
        apply_button_style([self.cancel_button, self.calculate_button, self.done_button, self.save_button,
                            self.help_button])
        apply_separator_style([self.separator1, self.separator2, self.separator3])
        apply_spin_boxes_style([self.min_approximation_interval_spinbox, self.min_target_grid_codes_spinbox])
        apply_label_style([self.min_approximation_interval_label, self.min_target_grid_codes_num_label])

        # --- Связываем сигналы изменения выбора с действиями ---
        self.node_grid_code_combobox.currentIndexChanged.connect(self.on_gridcode_changed)

        # --- Связываем кнопки с действиями ---
        self.cancel_button.clicked.connect(self.cancel_calculation)
        self.calculate_button.clicked.connect(self.start_calculation)
        self.save_button.clicked.connect(self.save_results)
        self.done_button.clicked.connect(self.accept)
        self.help_button.clicked.connect(self.toggle_help_window)

        # --- Связываем изменение checkbox'ов с действиями ---
        self.all_interval_checkbox.stateChanged.connect(self.on_full_interval_changed)
        self.all_target_checkbox.stateChanged.connect(self.on_all_target_changed)

        # --- Флаг состояния потока ---
        self.is_thread_running = False

        # --- Устанавливаем состояние кнопок ---
        self.save_button.setEnabled(False)
        self.done_button.setEnabled(False)

    def fill_comboboxes(self):
        """Заполняет combobox элементами с названиями колонок из DataFrame"""
        columns = self.data.columns
        self.main_id_combobox.addItems(columns)
        self.latitude_combobox.addItems(columns)
        self.longitude_combobox.addItems(columns)
        self.main_perimeter_combobox.addItems(columns)
        self.main_area_combobox.addItems(columns)

        self.node_id_combobox.addItems(columns)
        self.node_lat_combobox.addItems(columns)
        self.node_long_combobox.addItems(columns)
        self.node_grid_code_combobox.addItems(columns)

    def on_gridcode_changed(self):
        """Слот для обработки изменения выбора в gridcode_combobox"""
        self.selected_grid_codes = []   # Обновление списка выбранных порядков
        self.target_grid_codes = []     # Обновление списка выбранных критических порядков
        self.checkbox_map = {}          # Обновление словарей для обычных checkbox'ов
        self.target_checkbox_map = {}   # Обновление словарей для target-checkbox'ов

        selected_column = self.node_grid_code_combobox.currentText()
        if selected_column:
            # --- Очищаем предыдущие виджеты в layout ---
            layout_cleaner(self.gridcode_scroll_layout)
            layout_cleaner(self.target_gridcode_scroll_layout)

            # --- Получаем уникальные значения из выбранной колонки и сортируем их ---
            unique_values = sorted(self.data[selected_column].unique())

            # --- Добавляем checkbox для каждого уникального значения ---
            for value in unique_values:
                checkbox = checkbox_field_maker(self.gridcode_scroll_layout, value)
                checkbox.stateChanged.connect(self.on_checkbox_state_changed)  # Подключаем checkbox к обработчику
                self.checkbox_map[value] = checkbox  # Сохраняем в словарь

                target_checkbox = checkbox_field_maker(self.target_gridcode_scroll_layout, value)
                target_checkbox.stateChanged.connect(self.on_target_checkbox_state_changed)
                self.target_checkbox_map[value] = target_checkbox  # Сохраняем в словарь

    def on_checkbox_state_changed(self, state: int):
        """Слот для обработки изменения состояния checkbox"""
        checkbox = self.sender()
        value = int(checkbox.text())

        if state == Qt.Checked:
            self.selected_grid_codes.append(value)
        else:
            self.selected_grid_codes.remove(value)

    def on_target_checkbox_state_changed(self, state: int):
        """Слот для обработки изменения состояния target checkbox"""
        target_checkbox = self.sender()
        value = int(target_checkbox.text())

        if state == Qt.Checked:
            self.target_grid_codes.append(value)

            # --- Активация соответствующего основного checkbox'а, если он деактивирован ---
            checkbox = self.checkbox_map.get(value)
            if checkbox and not checkbox.isChecked():
                checkbox.setChecked(True)  # вызов on_checkbox_state_changed
        else:
            self.target_grid_codes.remove(value)

    def on_full_interval_changed(self, state: int):
        """
        Слот для обработки выбора 'использовать весь интервал'.
        Делает spinbox неактивным, если флажок включён.
        """
        self.use_full_interval = (state == Qt.Checked)
        self.min_approximation_interval_spinbox.setEnabled(not self.use_full_interval)
        self.min_approximation_interval_label.setEnabled(not self.use_full_interval)

    def on_all_target_changed(self, state: int):
        """
        Слот для обработки выбора 'все выбранные как критические'.
        Делает spinbox неактивным, если флажок включён.
        """
        self.require_all_target_codes = (state == Qt.Checked)
        self.min_target_grid_codes_spinbox.setEnabled(not self.require_all_target_codes)
        self.min_target_grid_codes_num_label.setEnabled(not self.require_all_target_codes)

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

    def _collect_parameters(self) -> bool:
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

            # Параметры точек бифуркации
            self.node_id_column = self.node_id_combobox.currentText()
            self.node_lat_column = self.node_lat_combobox.currentText()
            self.node_long_column = self.node_long_combobox.currentText()
            self.node_grid_code_col = self.node_grid_code_combobox.currentText()
            self.min_nodes_num = self.min_nodes_num_spinbox.value()
            self.min_target_grid_codes = len(self.target_grid_codes) if self.require_all_target_codes \
                else self.min_target_grid_codes_spinbox.value()

            if self.min_target_grid_codes > len(self.selected_grid_codes):
                QMessageBox.warning(self,
                                    "Ошибка параметров",
                                    "Выберите минимальное число критически важных порядков точек бифуркации, "
                                    "не превосходящее число выбранных порядков!")
                return False

            # Настройки вычислений
            self.scale_step_num = self.scale_step_spinbox.value()

            earth_radius = self.earth_radius_line.text()
            if earth_radius == '':
                QMessageBox.warning(self,
                                    "Ошибка параметров",
                                    "Введите значение радиуса Земли для вашей исследуемой области "
                                    "(например, 6371)!")
                return False
            else:
                self.earth_radius_value = float(earth_radius)

            self.min_approximation_interval = None  if self.use_full_interval \
                else self.min_approximation_interval_spinbox.value()
            return True
        except Exception as e:
            QMessageBox.warning(self, "Ошибка обработки параметров", str(e))
            return False

    def _setup_worker_and_thread(self):
        """Создает Worker и поток, подключает сигналы"""
        # --- Создание потока и экземпляра Worker'а ---
        self.thread = QThread(self)
        self.worker = DcorCalculatorWorker()

        # --- Передача параметров Worker'у ---
        self.worker.set_bass_id_col(self.main_id_column)
        self.worker.set_lat_col(self.lat_column)
        self.worker.set_long_col(self.long_column)
        self.worker.set_perimeter_col(self.main_perimeter_column)
        self.worker.set_area_col(self.main_area_column)
        self.worker.set_area_limits(self.main_area_limits)
        self.worker.set_perimeter_limits(self.main_perimeter_limits)

        self.worker.set_node_id_col(self.node_id_column)
        self.worker.set_node_lat_col(self.node_lat_column)
        self.worker.set_node_long_col(self.node_long_column)
        self.worker.set_node_grid_code_col(self.node_grid_code_col)

        self.worker.set_selected_grid_codes(self.selected_grid_codes)
        self.worker.set_target_grid_codes(self.target_grid_codes)

        self.worker.set_scale_step_num(self.scale_step_num)
        self.worker.set_min_nodes_num(self.min_nodes_num)
        self.worker.set_min_target_grid_codes(self.min_target_grid_codes)
        self.worker.set_min_approximation_interval(self.min_approximation_interval)
        self.worker.set_earth_radius_value(self.earth_radius_value)

        # --- Подключение сигналов прогресса и ошибок ---
        self.worker.progress_changed.connect(self._update_progress)
        self.worker.error_occurred.connect(self._handle_error)
        self.worker.log_changed.connect(self._update_logs)

        # --- Перемещение worker в поток ---
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(lambda: self.worker.calculate_dcor(self.data))

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
