from PyQt5.QtWidgets import (
    QFrame, QPushButton, QHBoxLayout, QVBoxLayout, QTextEdit, QProgressBar, QLabel, QGridLayout, QLineEdit, QSpinBox,
    QComboBox, QCheckBox)
from PyQt5.QtGui import QFont, QIcon, QDoubleValidator
from PyQt5.QtCore import Qt


# --- Глобальные переменные ---
FONT_10 = QFont(); FONT_10.setPointSize(10)
DOUBLE_VALIDATOR = QDoubleValidator(0, 1e10, 5)  # Валидатор


def create_separator() -> QFrame:
    """Создание и настройка разделителя"""
    separator = QFrame(parent=None)
    separator.setFrameShape(QFrame.HLine)
    separator.setFrameShadow(QFrame.Sunken)
    return separator


def create_icon_button(icon_path:str, size:int=30) -> QPushButton:
    """Создание и настройка кнопки"""
    button = QPushButton()
    button.setIcon(QIcon(icon_path))
    button.setFixedSize(size, size)
    return button


def button_layout_builder(layout) -> tuple[QPushButton, QPushButton, QPushButton, QPushButton]:
    """Создание layout'а основных кнопок"""
    button_layout = QHBoxLayout()
    cancel_button = QPushButton("Отмена")
    calculate_button = QPushButton("Расчет")
    save_button = QPushButton("Сохранить")
    done_button = QPushButton("Готово")
    button_layout.addWidget(cancel_button, alignment=Qt.AlignRight)
    button_layout.addWidget(calculate_button, alignment=Qt.AlignRight)
    button_layout.addWidget(save_button, alignment=Qt.AlignRight)
    button_layout.addWidget(done_button, alignment=Qt.AlignRight)
    layout.addLayout(button_layout)

    return cancel_button, calculate_button, save_button, done_button


def log_and_progress_bar_builder(layout) -> tuple[QTextEdit, QProgressBar]:
    """Настройка лога и прогресс бара"""
    log_text = QTextEdit()
    log_text.setReadOnly(True)
    log_text.setPlaceholderText("Здесь будут отображаться логи...")
    layout.addWidget(log_text)

    progress_bar = QProgressBar(parent=None)
    progress_bar.setValue(0)
    layout.addWidget(progress_bar)

    return log_text, progress_bar


def filter_layout_builder(layout) -> tuple:
    """Настройка виджетов таблицы для параметров фильтрации"""
    filter_layout = QVBoxLayout()
    layout.addLayout(filter_layout)

    filter_label = QLabel("Параметры фильтрации")
    filter_label.setFont(FONT_10)
    filter_layout.addWidget(filter_label, alignment=Qt.AlignCenter)

    filter_grid_layout = QGridLayout()
    filter_layout.addLayout(filter_grid_layout)

    # --- Настройка заголовков колонок таблицы для параметров фильтрации ---
    filter_grid_layout.addWidget(QLabel("Порог"), 0, 0)
    filter_grid_layout.addWidget(QLabel("Нижний"), 1, 0)
    filter_grid_layout.addWidget(QLabel("Верхний"), 2, 0)
    filter_grid_layout.addWidget(QLabel("По средней площади (%)"), 0, 1)
    filter_grid_layout.addWidget(QLabel("По квантилям (%)"), 0, 2)
    filter_grid_layout.addWidget(QLabel("По значениям"), 0, 3)

    # --- Настройка виджетов таблицы для параметров фильтрации ---
    lower_threshold_percent = QLineEdit()
    lower_threshold_percent.setText("1")
    lower_threshold_percent.setValidator(DOUBLE_VALIDATOR)
    upper_threshold_persent = QLineEdit()
    upper_threshold_persent.setText("99")
    upper_threshold_persent.setValidator(DOUBLE_VALIDATOR)
    filter_grid_layout.addWidget(lower_threshold_percent, 1, 1)
    filter_grid_layout.addWidget(upper_threshold_persent, 2, 1)

    lower_threshold_percentile = QLineEdit()
    lower_threshold_percentile.setText("1")
    lower_threshold_percent.setValidator(DOUBLE_VALIDATOR)
    upper_threshold_percentile = QLineEdit()
    upper_threshold_percentile.setText("99")
    lower_threshold_percentile.setValidator(DOUBLE_VALIDATOR)
    filter_grid_layout.addWidget(lower_threshold_percentile, 1, 2)
    filter_grid_layout.addWidget(upper_threshold_percentile, 2, 2)

    lower_threshold_value = QLineEdit()
    lower_threshold_value.setPlaceholderText("min")
    lower_threshold_value.setValidator(DOUBLE_VALIDATOR)
    upper_threshold_value = QLineEdit()
    upper_threshold_value.setValidator(DOUBLE_VALIDATOR)
    upper_threshold_value.setPlaceholderText("max")
    filter_grid_layout.addWidget(lower_threshold_value, 1, 3)
    filter_grid_layout.addWidget(upper_threshold_value, 2, 3)

    bin_nums_layout = QHBoxLayout()
    filter_layout.addLayout(bin_nums_layout)

    bin_nums_label = QLabel("Количество интервалов в гистограмме")
    bin_nums_layout.addWidget(bin_nums_label)
    bin_nums_spinbox = QSpinBox(parent=None)
    bin_nums_spinbox.setMinimum(1)
    bin_nums_spinbox.setFixedWidth(100)
    bin_nums_spinbox.setMaximum(1000000)
    bin_nums_spinbox.setValue(100)
    bin_nums_layout.addWidget(bin_nums_spinbox)
    bin_nums_layout.addStretch()

    return (lower_threshold_percent, upper_threshold_persent, lower_threshold_percentile, upper_threshold_percentile,
            lower_threshold_value, upper_threshold_value, bin_nums_spinbox)


def labeled_combobox_maker(label_text: str) -> tuple:
    """Создает горизонтальный layout с меткой и combobox"""
    h_layout = QHBoxLayout()  # Горизонтальный лэйаут
    label = QLabel(label_text)  # Создаем и добавляем метку
    h_layout.addWidget(label)
    combobox = QComboBox(parent=None)  # Создаем combobox и добавляем его
    h_layout.addWidget(combobox)

    # Возвращаем лэйаут и сам combobox для дальнейшего использования
    return h_layout, label, combobox


def limits_fields_maker(label_text: str = None, stretch: bool = False, min_width: int = None,
                        btn: QPushButton = None) -> tuple:
    """
    Создает горизонтальный layout с полями для ввода минимального и максимального значения,
    а также добавляет кнопку, если она указана
    """
    h_layout = QHBoxLayout()
    if stretch:
        h_layout.addStretch(1)

    if label_text:
        label = QLabel(label_text)
        h_layout.addWidget(label)

    min_edit = QLineEdit()
    min_edit.setPlaceholderText("min")
    if min_width: min_edit.setMinimumWidth(min_width)
    min_edit.setValidator(DOUBLE_VALIDATOR)
    h_layout.addWidget(min_edit)

    max_edit = QLineEdit()
    max_edit.setPlaceholderText("max")
    if min_width: max_edit.setMinimumWidth(min_width)
    max_edit.setValidator(DOUBLE_VALIDATOR)
    h_layout.addWidget(max_edit)

    if btn: h_layout.addWidget(btn)

    # Возвращаем лэйаут и поля для минимального и максимального значений
    return h_layout, min_edit, max_edit


def checkbox_field_w_limits_maker(main_layout, value_text:str) -> tuple:
    checkbox_layout = QHBoxLayout()

    checkbox = QCheckBox(str(value_text))
    checkbox_layout.addWidget(checkbox)

    checkbox_layout.addWidget(QLabel("  диапазон:"))

    value_min = QLineEdit()
    value_min.setPlaceholderText("min")
    value_min.setFixedWidth(150)
    value_min.setValidator(DOUBLE_VALIDATOR)
    checkbox_layout.addWidget(value_min)

    value_max = QLineEdit()
    value_max.setPlaceholderText("max")
    value_max.setFixedWidth(150)
    value_max.setValidator(DOUBLE_VALIDATOR)
    checkbox_layout.addWidget(value_max)
    checkbox_layout.addStretch()

    main_layout.addLayout(checkbox_layout)
    return checkbox, value_min, value_max


def checkbox_field_maker(main_layout, value_text:str, reverse=False) -> QCheckBox:
    checkbox = QCheckBox(str(value_text))
    if reverse:
        checkbox.setLayoutDirection(Qt.RightToLeft)
    main_layout.addWidget(checkbox)
    return checkbox


def layout_cleaner(layout):
    """Рекурсивно очищает все элементы в данном layout"""
    while layout.count():
        item = layout.takeAt(0)  # Получаем первый элемент
        if item.widget():
            item.widget().deleteLater()  # Удаляем виджет
        elif item.layout():
            layout_cleaner(item.layout())  # Рекурсивно очищаем вложенный лэйаут


def parameters_fields_changing(parameters_num_layout, min_max_parameters_layout,
                               param_num:int or None, param_min:float or None, param_max:float or None) -> str:
    """Метод для изменения виджетов отображения статистики параметров"""
    try:
        layout_cleaner(parameters_num_layout)
        layout_cleaner(min_max_parameters_layout)

        parameters_num_label = QLabel("Количество параметров:")
        parameters_num_layout.addWidget(parameters_num_label)
        if param_num:
            parameters_num_value = QLineEdit(str(param_num))
        else:
            parameters_num_value = QLineEdit()
            parameters_num_value.setPlaceholderText("тут будет количество параметров")
        parameters_num_value.setReadOnly(True)
        parameters_num_layout.addWidget(parameters_num_value)
        parameters_num_layout.addStretch()

        min_max_parameters_label = QLabel(" " * 11 + "со значениями от")
        min_max_parameters_layout.addWidget(min_max_parameters_label)
        if param_num:
            min_parameter_value = QLineEdit(str(param_min))
            max_parameter_value = QLineEdit(str(param_max))
        else:
            min_parameter_value = QLineEdit()
            min_parameter_value.setPlaceholderText("minimum")
            max_parameter_value = QLineEdit()
            max_parameter_value.setPlaceholderText("maximum")
        min_parameter_value.setReadOnly(True)
        min_max_parameters_layout.addWidget(min_parameter_value)
        min_max_parameters_layout.addWidget(QLabel("до"))
        max_parameter_value.setReadOnly(True)
        min_max_parameters_layout.addWidget(max_parameter_value)
        return ""

    except Exception as e:
        return str(e)
