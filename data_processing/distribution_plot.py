from PyQt5.QtWidgets import QLabel, QLineEdit, QHBoxLayout, QMessageBox, QSizePolicy
from PyQt5.QtCore import QObject
from PyQt5.QtGui import QFont

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

import pandas as pd
import numpy as np


def extract_parameters_from_data(data:pd.DataFrame, id_column:str, parameter_column:str) -> list:
    """
    Извлекает значения параметров (например, площади или периметры)
    для каждого объекта с уникальным ID.

    :param data: DataFrame с исходными данными
    :param id_column: Название колонки с идентификатором
    :param parameter_column: Название колонки с параметром
    :return: Список значений параметров
    """
    parameters_list = []

    grouped_data = data.dropna(subset=[id_column]).groupby(id_column)

    for _, group in grouped_data:
        group_parameter = group[parameter_column].iloc[0]
        parameters_list.append(float(str(group_parameter).replace(',', '.')))

    if not parameters_list:
        raise ValueError("Нет данных.")

    return parameters_list


def extract_length_from_data(data:pd.DataFrame, bass_id_column:str, river_id_column:str, river_length_column:str,
                             grid_code_column:str, selected_grid_codes:list) -> list:
    """
    Формирует список длин рек, принадлежащих заданным порядкам (gridcode),
    удаляя дубликаты по ID реки в пределах каждого бассейна.

    :param data: DataFrame с исходными данными
    :param bass_id_column: Название колонки с ID бассейна
    :param river_id_column: Название колонки с ID реки
    :param river_length_column: Название колонки с длиной реки
    :param grid_code_column: Название колонки с порядками (gridcode)
    :param selected_grid_codes: Список выбранных gridcode'ов
    :return: Список длин
    """
    length_list = []
    grouped_data = data.dropna(subset=[bass_id_column]).groupby(bass_id_column)

    for _, group in grouped_data:
        filtered_riv_id_group = group[group[grid_code_column].isin(selected_grid_codes)]
        unique_filtered_riv_group = filtered_riv_id_group.drop_duplicates(subset=[river_id_column])
        group_length = unique_filtered_riv_group[river_length_column].tolist()
        length_list += group_length

    length_list = [float(str(value).replace(',', '.')) if isinstance(value, str) else value
                   for value in length_list]

    return length_list


def get_limits_values(min_value:str, max_value:str) -> list:
    """
    Преобразует строковые значения минимального и максимального порогов в числа (float).
    Если преобразование невозможно, возвращает None для соответствующих значений.

    :param min_value: Строка минимального значения
    :param max_value: Строка максимального значения
    :return: Список [min, max] как float или None
    """
    try:
        # Преобразуем строки в числа с плавающей точкой
        low_value = float(min_value) if min_value else None
        upper_value = float(max_value) if max_value else None
    except ValueError:
        # В случае ошибки возвращаем None
        low_value, upper_value = None, None

    return [low_value, upper_value]


class DistributionPlot(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.parameters_list = None  # Список значений параметра

        # --- Параметры фильтрации ---
        self.bins_num: int | None = None             # Число интервалов гистограммы
        self.percents_values: list | None = None     # Пороги в процентах от среднего
        self.percentiles_values: list | None = None  # Пороги в виде процентилей
        self.min_max_values: list | None = None      # Заданные пользователем пределы

        # --- Вычисленные пороговые значения ---
        self.mean_threshold_lower = None      # Нижний порог по среднему
        self.mean_threshold_upper = None      # Верхний порог по среднему
        self.quantile_threshold_lower = None  # Нижний квантиль
        self.quantile_threshold_upper = None  # Верхний квантиль

        # --- Подписи осей ---
        self.x_label: str | None = None  # Подпись оси X
        self.y_label: str | None = None  # Подпись оси Y

        # --- Графики ---
        self.canvas_mean = FigureCanvas(plt.figure())      # График по среднему
        self.canvas_quantile = FigureCanvas(plt.figure())  # График по квантилям
        self.canvas_manual = FigureCanvas(plt.figure())    # График по ручным границам

        # --- Шрифты ---
        self.text_font_11 = QFont(); self.text_font_11.setPointSize(11)
        self.text_font_10 = QFont(); self.text_font_10.setPointSize(10)

    def set_parameters_list(self, value_list: list): self.parameters_list = value_list
    def set_bins_num(self, value: int): self.bins_num = value
    def set_percents_values(self, value_list: list): self.percents_values = value_list
    def set_percentiles_values(self, value_list: list): self.percentiles_values = value_list
    def set_min_max_values(self, value_list: list): self.min_max_values = value_list
    def set_x_label(self, label: str): self.x_label = label
    def set_y_label(self, label: str): self.y_label = label

    def reset_parameters(self) -> None:
        """Сбрасывает все параметры фильтрации и данные класса в None"""
        self.bins_num = None
        self.percents_values = None
        self.percentiles_values = None
        self.min_max_values = None
        self.parameters_list = None

    def plot_filtered_data(self, layout) -> None:
        """
        Строит три гистограммы распределения логарифмов значений параметров с выделением "мусорных" данных:
        по порогу от среднего значения, квантильному методу и вручную заданным границам.

        Метод выполняет:
        - логарифмирование значений,
        - построение гистограммы по общим интервалам,
        - выделение "мусорных" данных по каждому из трёх методов фильтрации,
        - отображение графиков с подписями и визуальными ограничениями,
        - добавление всех графиков и границ в интерфейс (layout).

        Параметры:
        ----------
        layout : QVBoxLayout
            Qt Layout, в который будет отрисован результат в виде графиков и порогов для каждого способа фильтрации

        Требования:
        -----------
        Перед вызовом метода необходимо установить параметры:
        - self.parameters_list: список исходных значений (до логарифмирования);
        - self.percents_values: список [нижний %, верхний %] от среднего значения;
        - self.percentiles_values: список [нижний процентиль, верхний];
        - self.min_max_values: список [min, max] — пользовательские границы фильтрации.

        Результат:
        ----------
        Три отрисованных графика распределения значений:
        - по порогам от среднего значения;
        - по квантильным границам;
        - по вручную заданным значениям (если есть).
        """
        # --- Очистка layout ---
        self._clear_layout(layout)

        # --- Логарифмируем параметры для работы с ними ---
        log_params_list = np.log10(self.parameters_list)

        # --- Определяем общие границы для всех графиков ---
        x_min = np.floor(min(log_params_list))  # Минимальное значение логарифмов, округленное вниз
        x_max = np.ceil(max(log_params_list))  # Максимальное значение логарифмов, округленное вверх

        # --- Способ 1: Порог на основе средней площади ---
        mean_area = np.mean(self.parameters_list)  # Среднее значение параметров
        self.mean_threshold_lower = (self.percents_values[0] * 0.01) * mean_area
        self.mean_threshold_upper = (self.percents_values[1] * 0.01) * mean_area

        # --- Способ 2: Использование порога квантиля ---
        self.quantile_threshold_lower = np.percentile(self.parameters_list, self.percentiles_values[0])  # Нижний 1-й процентиль
        self.quantile_threshold_upper = np.percentile(self.parameters_list, self.percentiles_values[1])  # Верхний 99-й процентиль

        # --- Рассчитываем гистограмму один раз ---
        counts_all, bin_edges, bin_centers, bin_width = (
            self._calculate_histogram(log_params_list, x_min, x_max))

        # --- График 1: Порог по средней площади ---
        is_trash_mean = (bin_centers <= np.log10(self.mean_threshold_lower)) | (
                    bin_centers >= np.log10(self.mean_threshold_upper))  # Условие для "мусорных" значений
        self._plot_trash_highlight(self.canvas_mean, bin_centers, counts_all, bin_width, is_trash_mean,
                                   thresholds={"lower": np.log10(self.mean_threshold_lower),
                                               "upper": np.log10(self.mean_threshold_upper)})

        # --- График 2: Порог квантиля ---
        is_trash_quantile = (bin_centers <= np.log10(self.quantile_threshold_lower)) | (
                    bin_centers > np.log10(self.quantile_threshold_upper))  # Условие для "мусорных" значений
        self._plot_trash_highlight(self.canvas_quantile, bin_centers, counts_all, bin_width, is_trash_quantile,
                                   thresholds={"lower": np.log10(self.quantile_threshold_lower),
                                               "upper": np.log10(self.quantile_threshold_upper)})

        # --- График 3: По заданным значениям минимума и максимума ---
        if self.min_max_values and any(value is not None for value in self.min_max_values):
            min_value = np.log10(self.min_max_values[0]) if self.min_max_values[0] else min(bin_centers)
            max_value = np.log10(self.min_max_values[1]) if self.min_max_values[1] else max(bin_centers)
            is_trash_min_max = (bin_centers <= min_value) | (bin_centers >= max_value)
            self._plot_trash_highlight(self.canvas_manual, bin_centers, counts_all, bin_width, is_trash_min_max,
                                       thresholds={"lower": min_value, "upper": max_value})
        else:
            # Если min_max_values не заданы, рисуем все значения как нормальные
            self._plot_trash_highlight(self.canvas_manual, bin_centers, counts_all, bin_width,
                                       np.zeros_like(bin_centers, dtype=bool), None)

        # --- Создаем виджеты в layout ---
        self._update_layout(layout)

    def _clear_layout (self, layout) -> None:
        """
        Рекурсивно удаляет все виджеты из layout, кроме экземпляров FigureCanvas.

        :param layout: QLayout для очистки
        """
        while layout.count():
            item = layout.takeAt(0)  # Получаем первый элемент
            if item.widget():
                if not isinstance(item.widget(), FigureCanvas):  # Сохраняем только FigureCanvas
                    item.widget().deleteLater()  # Удаляем виджет
            elif item.layout():
                self._clear_layout(item.layout())  # Рекурсивно очищаем вложенный лэйаут

    def _update_layout (self, layout) -> None:
        """
        Добавляет в layout графики и соответствующие поля границ для всех типов фильтрации.

        :param layout: QLayout для обновления
        """
        self._rebuild_layout(layout, "средней площади", self.mean_threshold_lower, self.mean_threshold_upper,
                             self.canvas_mean)
        self._rebuild_layout(layout, "порога квантиля", self.quantile_threshold_lower, self.quantile_threshold_upper,
                             self.canvas_quantile)

        temp_min_max = [None, None] if not self.min_max_values else self.min_max_values
        self._rebuild_layout(layout, "пользовательских значений", temp_min_max[0], temp_min_max[1], self.canvas_manual)

    def _rebuild_layout (self, layout, main_label_text, min_value, max_value, canvas) -> None:
        """
        Добавляет текст, график и числовые границы в layout.

        :param layout: QLayout для вставки
        :param main_label_text: Название метода фильтрации
        :param min_value: Нижний порог (логарифм)
        :param max_value: Верхний порог (логарифм)
        :param canvas: Объект FigureCanvas с графиком
        """
        main_label = QLabel("Границы на основе " + main_label_text)
        main_label.setFont(self.text_font_11)
        layout.addWidget(main_label)

        # --- График распределения ---
        try:
            canvas.setFixedHeight(300)
            canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            layout.addWidget(canvas)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка",
                                f"Ошибка при загрузке изображения фильтрации {main_label_text}:\n{e}")

        # --- Layout для вывода вычисленных границ ---
        results_layout = QHBoxLayout()
        results_label1 = QLabel("Нижняя граница:")
        results_label1.setFont(self.text_font_10)
        if min_value:
            lower_bound_line = QLineEdit(str(round(min_value, 1)))
        else:
            lower_bound_line = QLineEdit()
            lower_bound_line.setPlaceholderText("min")
        lower_bound_line.setFont(self.text_font_10)
        lower_bound_line.setReadOnly(True)  # Делаем поле только для чтения
        lower_bound_line.setMinimumWidth(200)

        results_label2 = QLabel("верхняя граница:")
        results_label2.setFont(self.text_font_10)
        if max_value:
            upper_bound_line = QLineEdit(str(round(max_value, 1)))
        else:
            upper_bound_line = QLineEdit()
            upper_bound_line.setPlaceholderText("max")
        upper_bound_line.setFont(self.text_font_10)
        upper_bound_line.setReadOnly(True)
        upper_bound_line.setMinimumWidth(200)

        results_layout.addStretch(1)  # Добавляем пустое пространство слева от элементов
        results_layout.addWidget(results_label1)
        results_layout.addWidget(lower_bound_line)
        results_layout.addWidget(results_label2)
        results_layout.addWidget(upper_bound_line)
        layout.addLayout(results_layout)

    def _calculate_histogram(self, parameter_list, x_min, x_max):
        """
        Строит логарифмическую гистограмму по данным:
        вычисляет частоты (counts), границы бинов и их центры.
        Используется фиксированное число интервалов (bins_num),
        возможна установка границ вручную.

        :param parameter_list: Логарифмы значений параметров
        :param x_min: Нижняя граница
        :param x_max: Верхняя граница
        :return: counts_all, bin_edges, bin_centers, bin_width
        """
        if x_min or x_max:
            if not x_min: x_min = min(parameter_list)
            if not x_max: x_max = max(parameter_list)
            counts_all, bin_edges = np.histogram(parameter_list, bins=self.bins_num, range=(x_min, x_max))
        else:
            counts_all, bin_edges = np.histogram(parameter_list, bins=self.bins_num)

        bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])  # Центры бинов
        bin_width = bin_edges[1] - bin_edges[0]  # Ширина одного бина
        return counts_all, bin_edges, bin_centers, bin_width

    def _plot_trash_highlight(self, canvas, bin_centers, counts, bin_width, is_trash, thresholds) -> None:
        """
        Рисует гистограмму с выделением нормальных и мусорных значений,
        включая вертикальные линии для порогов

        :param canvas: Объект FigureCanvas
        :param bin_centers: Центры бинов
        :param counts: Частоты значений
        :param bin_width: Ширина интервалов
        :param is_trash: Логическое выделение мусорных значений
        :param thresholds: dict с порогами: {'lower': float, 'upper': float}
        """
        canvas.figure.clear()
        ax = canvas.figure.add_subplot(111)
        # canvas_distribution.figure.set_size_inches(10, 6)

        real_centers = 10 ** bin_centers
        real_width = 10 ** (bin_centers + bin_width / 2) - 10 ** (bin_centers - bin_width / 2)

        if not np.any(is_trash):
            ax.bar(real_centers, counts, width=real_width, color="green", alpha=0.7)
        else:
            # Нормальные значения
            ax.bar(real_centers[~is_trash], counts[~is_trash], width=real_width[~is_trash], color="green", alpha=0.7,
                   label="Нормальные значения")
            # Мусорные значения
            ax.bar(real_centers[is_trash], counts[is_trash], width=real_width[is_trash], color="red", alpha=0.7,
                   label="Мусорные значения")

            # Добавляем вертикальные линии для порогов
            if thresholds:
                if "lower" in thresholds:
                    ax.axvline(10**thresholds["lower"], color="purple", linestyle="--", linewidth=1.5)
                if "upper" in thresholds:
                    ax.axvline(10**thresholds["upper"], color="purple", linestyle="--", linewidth=1.5)

            # Добавление легенды
            ax.legend(fontsize=12, loc='upper left', bbox_to_anchor=(0.01, 0.99))

        # Настройки графика
        ax.set_xlabel(self.x_label, fontsize=12)
        ax.set_xscale('log')
        ax.set_ylabel(self.y_label, fontsize=12)

        ax.tick_params(axis='both', which='major', labelsize=12)  # Устанавливаем размер шрифта меток осей
        ax.grid(True)

        canvas.draw()
