import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from data_processing.fract_dimension_calc import fract_dimension_finder, coords_to_log
import pandas as pd

class DpsCalculatorWorker(QObject):
    error_occurred = pyqtSignal(str)            # Сигнал для передачи сообщений об ошибках
    progress_changed = pyqtSignal(int, str)     # Сигнал для обновления прогресса и логов
    log_changed = pyqtSignal(str)               # Сигнал для обновления логов

    def __init__(self):
        super().__init__(parent=None)

        # --- Названия колонок ---
        self.columns = {
            'main_id_col': None,                # ID главного бассейна
            'lat_col': None,                    # Широта
            'long_col': None,                   # Долгота
            'main_perimeter_col': None,         # Периметр главного бассейна
            'main_area_col': None               # Площадь главного бассейна
        }
        self.perimeter_col: list | None = None  # Периметры вложенных бассейнов
        self.area_col: list | None = None       # Площади вложенных бассейнов
        self.id_col: list | None = None         # ID вложенных бассейнов

        # --- Ограничения ---
        self.bass_area_limits: list | None = None       # Ограничения по площади [min, max] для всех уровней
        self.bass_perimeter_limits: list | None = None  # Ограничения по периметру [min, max] для всех уровней

        # --- Внутренние структуры данных ---
        self.area_list: list = []               # Список площадей выбранного бассейна
        self.perimeter_list: list = []          # Список периметров выбранного бассейна
        self.result: list = []                  # Финальный результат

    def set_perimeter_col(self, value:list): self.perimeter_col = value
    def set_area_col(self, value:list): self.area_col = value
    def set_id_col(self, value:list): self.id_col = value
    def set_area_limits(self, limits_list): self.bass_area_limits = limits_list
    def set_perimeter_limits(self, limits_list): self.bass_perimeter_limits = limits_list

    def set_column(self, column_name, value:str):
        """Устанавливает значение для указанной колонки"""
        if column_name in self.columns:
            self.columns[column_name] = value
        else:
            raise ValueError(f"Неизвестная колонка: {column_name}")

    def calculate_dps(self, data):
        """
        Выполняет расчёт параметра Dps (Dimensionless Perimeter-to-Area Scaling)
        для каждого главного бассейна на основе логарифмической аппроксимации
        связи между площадью и периметром.

        Метод итерируется по каждому главному бассейну и собирает вложенные бассейны
        всех уровней, применяя фильтрацию по заданным ограничениям на периметр и площадь.
        На основе списка пар (периметр, площадь) строится логарифмическая модель,
        позволяющая оценить показатель Dps:
            - Dps = 2 / λ, где λ — наклон аппроксимации в логарифмическом масштабе
            - также рассчитываются R² и стандартная ошибка аппроксимации

        Все результаты сохраняются в self.result в виде таблицы с итоговыми метриками
        по каждому главному бассейну.

        Параметры:
        ----------
        data : pd.DataFrame
            Исходный DataFrame, содержащий:
            - координаты центроидов (широта, долгота),
            - периметры и площади главных и вложенных бассейнов,
            - ID всех уровней иерархии.

        Требования:
        -----------
        Перед запуском метода необходимо установить:
        - self.columns['main_id_col'], ..., self.columns['main_area_col']
        - self.id_col, self.area_col, self.perimeter_col — списки вложенных уровней
        - ограничения по площади и периметру (set_area_limits, set_perimeter_limits)

        Результат:
        ----------
        Сохраняет в self.result таблицу с колонками:
            - bas_id, lon, lat, perimeter, area, bas_num, Dps, R², std_error

        Исключения:
        -----------
        В случае ошибок фильтрации, расчёта или недопустимых значений:
            - вызывает error_occurred(str)
            - прогресс обновляется через progress_changed(int, str)
        """
        # --- Удаляем строки с пустыми значениями ---
        data.dropna(subset=[self.columns["main_area_col"], self.columns["main_perimeter_col"]], inplace=True)
        for column in self.area_col + self.perimeter_col:
            data.dropna(subset=[column], inplace=True)

        # --- Замена десятичных разделителей на точку ---
        columns_to_fix = (
                [self.columns["main_area_col"], self.columns["main_perimeter_col"],
                 self.columns["long_col"], self.columns["lat_col"]]
                + self.area_col + self.perimeter_col
        )

        for column in columns_to_fix:
            data[column] = pd.to_numeric(
                data[column].astype(str).str.replace(',', '.', regex=False),
                errors='coerce'
            )

        # --- Группируем данные по bass_id_col ---
        grouped_data = data.groupby(self.columns["main_id_col"])

        total_steps = len(grouped_data)
        step = 0

        # --- Обработка главных бассейнов ---
        for _, group in grouped_data:
            step += 1
            progress = int((step / total_steps) * 100)
            if progress == 100: progress = 99

            try:
                current_bass_id = int(group[self.columns["main_id_col"]].iloc[0])           # ID текущего бассейна
                current_bass_area = group[self.columns["main_area_col"]].iloc[0]            # Площадь текущего бассейна
                current_bass_perimeter = group[self.columns["main_perimeter_col"]].iloc[0]  # Периметр текущего бассейна
            except Exception as e:
                self.log_changed.emit(
                    f"<span style='color:red;'>Ошибка получения параметров бассейна "
                    f"{int(group[self.columns["main_id_col"]].iloc[0])}:\n{e}</span>")
                continue

            self.progress_changed.emit(progress,
                                       f"Обработка главных бассейнов: {current_bass_id}")

            # --- Фильтрация главных бассейнов ---
            if (self.bass_area_limits is not None and
                    not self._is_within_limits(current_bass_area, self.bass_area_limits[-1])):
                self.log_changed.emit(f"<span style='color:orange;'>Пропускаем бассейн {current_bass_id}: "
                                      f"недопустимая площадь</span>")
                continue

            if (self.bass_perimeter_limits is not None and
                    not self._is_within_limits(current_bass_perimeter, self.bass_perimeter_limits[-1])):
                self.log_changed.emit(f"<span style='color:orange;'>Пропускаем бассейн {current_bass_id}: "
                                      f"недопустимый периметр</span>")
                continue

            # --- Инициализируем новые списки для периметров и площадей текущего бассейна ---
            self.area_list = [current_bass_area]
            self.perimeter_list = [current_bass_perimeter]

            # --- Обработка вложенных бассейнов ---
            try:
                for selected_bass_id in range(len(self.id_col)):
                    selected_id_column = self.id_col[selected_bass_id]  # Колонка с текущими ID вложенных бассейнов

                    # --- Выделение строк с уникальными ID ---
                    unique_bass_group = group.drop_duplicates(subset=selected_id_column)

                    # --- Исключение строк, где параметры выходят за пределы заданных границ ---
                    filtered_bass_group = unique_bass_group[
                        unique_bass_group.apply(
                            lambda row: (self._is_within_limits(row[self.area_col[selected_bass_id]],
                                                                self.bass_area_limits[selected_bass_id]) and
                                         self._is_within_limits(row[self.perimeter_col[selected_bass_id]],
                                                                self.bass_perimeter_limits[selected_bass_id])),
                            axis=1
                        )
                    ]

                    # --- Добавляем в списки периметр и площадь для текущего уровня ---
                    self.perimeter_list.extend(filtered_bass_group[self.perimeter_col[selected_bass_id]].tolist())
                    self.area_list.extend(filtered_bass_group[self.area_col[selected_bass_id]].tolist())
            except Exception as e:
                self.log_changed.emit(
                    f"<span style='color:red;'>Ошибка формирования списков периметров и площадей "
                    f"для бассейна {current_bass_id}:\n{e}</span>")

                self.result.append({
                    "bas_id": int(current_bass_id),
                    "lon": float(group[self.columns["long_col"]].iloc[0]),
                    "lat": float(group[self.columns["lat_col"]].iloc[0]),
                    "perimeter": float(current_bass_perimeter),
                    "area": '',
                    "bas_num": '',
                    "Dps": '',
                    "R^2": '',
                    "d": ''
                })
                continue

            try:
                # Проверка: минимум 3 уникальных значения
                if len(set(self.perimeter_list)) < 3 or len(set(self.area_list)) < 3:
                    self.log_changed.emit(
                        f"<span style='color:red;'>Недостаточно уникальных значений для регрессии "
                        f"в бассейне {current_bass_id}</span>")

                    self.result.append({
                        "bas_id": int(current_bass_id),
                        "lon": float(group[self.columns["long_col"]].iloc[0]),
                        "lat": float(group[self.columns["lat_col"]].iloc[0]),
                        "perimeter": float(current_bass_perimeter),
                        "area": '',
                        "bas_num": '',
                        "Dps": '',
                        "R^2": '',
                        "d": ''
                    })
                    continue

                log_x, log_y = coords_to_log(self.perimeter_list, self.area_list)
                dps, r_squared, std_error = fract_dimension_finder(log_x, log_y)
            except Exception as e:
                self.error_occurred.emit(f"Ошибка вычисления Dps:\n{e}")
                return

            self.result.append({
                "bas_id": int(current_bass_id),
                "lon": float(group[self.columns["long_col"]].iloc[0]),
                "lat": float(group[self.columns["lat_col"]].iloc[0]),
                "perimeter": float(current_bass_perimeter),
                "area": float(current_bass_area),
                "bas_num": len(self.perimeter_list),
                "Dps": 2 / dps,
                "R^2": float(r_squared),
                "d": float(std_error)
            })

        self.result = pd.DataFrame(self.result)
        self.progress_changed.emit(100, "Расчет окончен. Файл готов к сохранению")

    def _is_within_limits(self, value, limits) -> bool:
        """
        Проверяет, входит ли значение в заданные границы.
        Если нижняя или верхняя граница равна None — соответствующее условие не проверяется.

        :param value: Число для проверки
        :param limits: Список [min, max], где min и/или max могут быть None
        :return: True, если значение входит в диапазон, иначе False
        """
        min_limit, max_limit = limits
        return (min_limit is None or value >= min_limit) and (max_limit is None or value <= max_limit)
