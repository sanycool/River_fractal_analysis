def apply_button_style(buttons_list: list):
    """Настройка стилей для кнопок"""
    button_style = """
        QPushButton:enabled:hover {
            background-color: rgba(85, 85, 85, 0.8);
        }
        QPushButton:disabled {
            background-color: #444444;
            color: gray;
        }
    """
    for button in buttons_list:
        button.setStyleSheet(button_style)


def apply_separator_style(separators_list: list):
    """Настройка стилей для разделителей"""
    separator_style = """
        QFrame {
            border: 1px solid black;
            background-color: black;
        }
    """
    for separator in separators_list:
        separator.setStyleSheet(separator_style)

def apply_spin_boxes_style(spin_boxes_list: list):
    """Настройка стилей для счетчиков"""
    spin_boxes_style = """
        QSpinBox:disabled {
            color: gray;
            background-color: #444444;
        }
    """
    for spinbox in spin_boxes_list:
        spinbox.setStyleSheet(spin_boxes_style)

def apply_label_style(labels_list: list):
    """Настройка стилей для QLabel"""
    label_style = """
        QLabel:disabled {
            color: gray;
        }
    """
    for label in labels_list:
        label.setStyleSheet(label_style)


def apply_combobox_style(comboboxes_list: list):
    """Настройка стилей для QComboBox"""
    combobox_style = """
        QComboBox:disabled {
            color: gray;
            background-color: #444444;
        }
    """
    for combobox in comboboxes_list:
        combobox.setStyleSheet(combobox_style)