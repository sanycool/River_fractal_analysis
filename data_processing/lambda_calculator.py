import numpy as np
import pandas as pd
from PyQt5.QtCore import QObject, pyqtSignal
from data_processing.fract_dimension_calc import fract_dimension_finder, coords_to_log


class LambdaCalculatorWorker(QObject):
    error_occurred = pyqtSignal(str)                # Сигнал для передачи сообщений об ошибках
    progress_changed = pyqtSignal(int, str)         # Сигнал для обновления прогресса и логов
    log_changed = pyqtSignal(str)                   # Сигнал для обновления логов

    def __init__(self):
        super().__init__(parent=None)

        # --- Названия колонок ---
        self.bass_id_col: str | None = None       # Колонка с ID бассейна
        self.lat_col: str | None = None           # Колонка с широтой центроида
        self.long_col: str | None = None          # Колонка с долготой центроида
        self.perimeter_col: str | None = None     # Колонка с периметром
        self.area_col: str | None = None          # Колонка с площадью
        self.gridcode_col: str | None = None      # Колонка с порядком (gridcode)
        self.river_id_col: str | None = None      # Колонка с ID реки
        self.river_length_col: str | None = None  # Колонка с длиной реки

        # --- Ограничения (на площадь/периметр) ---
        self.bass_area_limits: list | None = None       # [min, max] по площади
        self.bass_perimeter_limits: list | None = None  # [min, max] по периметру

        # --- Настройки фильтрации и анализа ---
        self.selected_grid_codes: list[int] = []          # Выбранные gridcode'ы
        self.gridcode_ranges: dict[int, tuple] = {}       # Диапазоны длин: {gridcode: (min, max)}
        self.interval_step: int | None = None             # Шаг интервалов
        self.length_limits: list[float] = []              # Общие границы длин [min, max]
        self.min_approximate_interval: int | None = None  # Минимальное количество точек для аппроксимации

        # --- Внутренние структуры данных ---
        self.length_for_basins: list[list[float]] = []    # Длины русел по бассейнам
        self.results_dict: dict[str, list] = {            # Накопленные результаты
            'bass_id': [],
            'lon': [],
            'lat': [],
            'perimeter': [],
            'area': [],
            'interval_step': [],
            'rivers_num': [],
            'approximation_interval': [],
            'fractal_lambda': [],
            'r_squared': [],
            'std_error': []
        }
        self.result: pd.DataFrame | None = None           # Финальный результат

    def set_bass_id_col(self, column_name: str): self.bass_id_col = column_name
    def set_lat_col(self, column_name: str): self.lat_col = column_name
    def set_long_col(self, column_name: str): self.long_col = column_name
    def set_perimeter_col(self, column_name: str): self.perimeter_col = column_name
    def set_area_col(self, column_name: str): self.area_col = column_name
    def set_gridcode_col(self, column_name: str): self.gridcode_col = column_name
    def set_river_id_col(self, column_name: str): self.river_id_col = column_name
    def set_river_length_col(self, column_name: str): self.river_length_col = column_name
    def set_selected_gridcodes(self, gridcodes_list: list): self.selected_grid_codes = gridcodes_list
    def set_gridcode_ranges(self, ranges_dict): self.gridcode_ranges = ranges_dict
    def set_interval_step(self, value: int): self.interval_step = value
    def set_min_approximate_interval(self, min_value: int): self.min_approximate_interval = min_value
    def set_bass_area_limits(self, limits_list: list): self.bass_area_limits = limits_list
    def set_bass_perimeter_limits(self, limits_list: list): self.bass_perimeter_limits = limits_list
    def set_length_limits(self, limits_list:list): self.length_limits = limits_list

    def calculate_lambda(self, data: pd.DataFrame):
        """
        Выполняет расчёт фрактальной размерности λ (lambda) для каждого бассейна
        на основе длины русел, сгруппированных по порядкам (gridcode), с использованием
        логарифмической аппроксимации частотной гистограммы.

        Метод проходит по каждому бассейну, применяет фильтрацию по площади, периметру и
        допустимым длинам русел, строит гистограмму распределения длин, и находит оптимальный
        интервал для линейной аппроксимации в логарифмическом масштабе, рассчитывая:
        - фрактальную размерность (lambda)
        - коэффициент детерминации (R²)
        - стандартную ошибку (std_error)

        Все промежуточные и итоговые данные сохраняются в self.results_dict и затем собираются
        в итоговый DataFrame self.result.

        Параметры:
        ----------
        data : pd.DataFrame
            Входной DataFrame, содержащий информацию о бассейнах и водотоках, включая:
            - координаты центроидов бассейнов (широта, долгота),
            - площадь и периметр бассейна,
            - ID рек, длину русел, gridcode.

        Предполагается, что имена колонок заранее заданы через set_методы:
        - set_bass_id_col, set_perimeter_col, set_area_col и др.

        Требования:
        -----------
        Перед вызовом метода необходимо установить:
        - self.interval_step — шаг для построения интервалов гистограммы;
        - self.min_approximate_interval — минимальное число точек для аппроксимации;
        - self.selected_grid_codes — список разрешённых порядков (gridcode);
        - self.gridcode_ranges — словарь допустимых диапазонов длин по порядкам;
        - optionally: ограничения по площади/периметру бассейна.

        Результат:
        ----------
        Заполняет атрибут self.result — DataFrame с фрактальными характеристиками для каждого бассейна:
            - fractal_lambda, r_squared, std_error, interval_step и др.

        Исключения:
        -----------
        При возникновении ошибок в расчётах или фильтрации — вызываются сигналы:
            - error_occurred(str) — с описанием ошибки;
            - log_changed(str) — для логирования этапов фильтрации/обработки.
        """

        # --- Удаляем строки с пустыми значениями, группируем данные по bass_id_col ---
        grouped_data = data.dropna(subset=[self.bass_id_col]).groupby(self.bass_id_col)
        total_steps = len(grouped_data)
        step = 0

        # --- Замена десятичных разделителей на точку ---
        for column in [self.perimeter_col, self.area_col, self.river_length_col, self.lat_col, self.long_col]:
            data[column] = data[column].apply(
                lambda x: float(str(x).replace(',', '.')) if isinstance(x, str) else x)

        try:
            for _, group in grouped_data:
                current_bass_id = int(group[self.bass_id_col].iloc[0])
                current_bass_area = float(group[self.perimeter_col].iloc[0])
                current_bass_perimeter = float(group[self.area_col].iloc[0])

                # --- Фильтрация главных бассейнов ---
                if (self.bass_area_limits is not None and
                        not self._is_within_limits(current_bass_area, self.bass_area_limits)):
                    self.log_changed.emit(f"<span style='color:orange;'>Пропускаем бассейн {current_bass_id}: "
                                          f"недопустимая площадь</span>")
                    continue
                if (self.bass_perimeter_limits is not None and
                        not self._is_within_limits(current_bass_perimeter, self.bass_perimeter_limits)):
                    self.log_changed.emit(f"<span style='color:orange;'>Пропускаем бассейн {current_bass_id}: "
                                          f"недопустимый периметр</span>")
                    continue

                # --- Запись характеристик бассейна в результаты ---
                self.results_dict['bass_id'].append(current_bass_id)
                self.results_dict['lon'].append(float(group[self.lat_col].iloc[0]))
                self.results_dict['lat'].append(float(group[self.long_col].iloc[0]))
                self.results_dict['perimeter'].append(current_bass_area)
                self.results_dict['area'].append(current_bass_perimeter)
                self.results_dict['interval_step'].append(self.interval_step)

                # --- Получение списка длин для бассейна ---
                self._set_group_parameters_lists(group)
        except Exception as e:
            self.error_occurred.emit(f"Ошибка составления списка длин бассейнов:\n{e}")
            return

        if not self.length_limits[0]:
            self.length_limits[0] = min(min(sublist) for sublist in self.length_for_basins if sublist)
        if not self.length_limits[1]:
            self.length_limits[1] = max(max(sublist) for sublist in self.length_for_basins if sublist)

        # Определение границ интервалов на основе self.interval_step и округления границ к ближайшему кратному числу
        min_limit = np.ceil(self.length_limits[0] / self.interval_step) * self.interval_step
        max_limit = np.ceil(self.length_limits[1] / self.interval_step) * self.interval_step
        interval_edges = np.arange(min_limit, max_limit + self.interval_step, self.interval_step)

        for basin in range(len(self.length_for_basins)):
            step += 1
            progress = int((step / total_steps) * 100)
            if progress == 100: progress = 99
            self.progress_changed.emit(progress,
                                       f"Обработка главных бассейнов: {self.results_dict['bass_id'][basin]}")

            self.results_dict['rivers_num'].append(len(self.length_for_basins[basin]))

            # Вычисление гистограммы: length_frequencies - количество элементов в каждом интервале
            basin_length_frequencies, _ = np.histogram(self.length_for_basins[basin], bins=interval_edges)
            # Вычисляем центры интервалов (среднее арифметическое из границ каждого интервала)
            basin_interval_centers = (interval_edges[:-1] + interval_edges[1:]) / 2

            try:
                fractal_lambda, r_squared, std_error, begin, end = (
                    self._dimension_with_best_interval(basin_interval_centers, basin_length_frequencies))
            except Exception as e:
                self.error_occurred.emit(f"Ошибка расчета :\n{e}")
                return

            # Если результаты аппроксимации не найдены (некорректные значения), пропускаем бассейн
            if fractal_lambda is None or fractal_lambda == 0.0:
                self.log_changed.emit(f"<span style='color:red;'>Пропускаем бассейн с "
                                      f"{len(self.length_for_basins[basin])} руслами</span>")
                self.results_dict['approximation_interval'].append('')
                self.results_dict['fractal_lambda'].append('')
                self.results_dict['r_squared'].append('')
                self.results_dict['std_error'].append('')
                continue

            self.results_dict['approximation_interval'].append(f"{begin+1}-{end+1}")
            self.results_dict['fractal_lambda'].append(fractal_lambda * (-1))
            self.results_dict['r_squared'].append(r_squared)
            self.results_dict['std_error'].append(std_error)

        self.result = pd.DataFrame(self.results_dict)
        self.progress_changed.emit(100, "Расчет окончен. Файл готов к сохранению")

    def _set_group_parameters_lists(self, group):
        """
        Формирует список длин рек (водотоков) для одного бассейна.

        Выполняется фильтрация по выбранным порядкам (gridcode) и диапазонам длин,
        после чего извлекаются уникальные ID русел, прошедших фильтрацию, и сохраняются их длины.

        :param group: Подтаблица по одному бассейну, сгруппированная по bass_id
        :return: None (обновляет self.length_for_basins)
        """
        # --- Фильтрация по gridcode ---
        mask_gridcode = group[self.gridcode_col].isin(self.selected_grid_codes)
        filtered_group = group.loc[mask_gridcode].copy()

        if not filtered_group.empty:
            # --- Фильтрация по диапазонам длин ---
            mask_length = filtered_group.apply(
                lambda row: self._is_within_limits(row[self.river_length_col],
                                                   self.gridcode_ranges.get(row[self.gridcode_col], (None, None))),
                axis=1
            )
            filtered_group = filtered_group.loc[mask_length]

            # --- Получение списка длин уникальных рек после всех фильтраций ---
            unique_rivers = filtered_group.drop_duplicates(subset=[self.river_id_col])
            length_list = unique_rivers[self.river_length_col].tolist()
        else:
            length_list = []

        # --- Добавление длин данного бассейна в общий список ---
        self.length_for_basins.append(length_list)

    def _is_within_limits(self, value, limits):
        """
        Проверяет, входит ли значение в заданные границы.
        Если нижняя или верхняя граница равна None — соответствующее условие не проверяется.

        :param value: Число для проверки
        :param limits: Список [min, max], где min и/или max могут быть None
        :return: True, если значение входит в диапазон, иначе False
        """
        min_limit, max_limit = limits
        return (min_limit is None or value >= min_limit) and (max_limit is None or value <= max_limit)

    def _dimension_with_best_interval(self, x_coords, y_coords):
        """
        Подбирает лучший интервал точек для линейной аппроксимации в логарифмическом масштабе.

        Перебираются все возможные отрезки, начиная от минимального допустимого количества точек.
        Для каждого интервала рассчитывается наклон (λ), коэффициент детерминации (R²) и стандартная ошибка.
        Возвращается интервал с наименьшим λ.

        :param x_coords: Центры интервалов (ось X)
        :param y_coords: Частоты (ось Y)
        :return: (lambda, r_squared, std_error, begin_index, end_index) или (None, ...) если расчёт невозможен
        """
        # --- Инициализация переменных для хранения наилучшего интервала ---
        best_begin = 0          # Индекс начала наилучшего интервала
        best_end = 0            # Индекс конца наилучшего интервала
        best_lambda = 0.0       # Лучшее значение наклона (λ)
        best_r_squared = 0.0    # Наилучшее значение R²
        best_std_error = 0.0    # Наименьшая ошибка аппроксимации

        # --- Логарифмирование координат ---
        log_x, log_y = coords_to_log(x_coords, y_coords)

        if (log_x[0] or log_y[0]) is None:
            return None, None, None, None, None

        n = len(log_x)

        # --- Проверка на достаточность точек ---
        if n < self.min_approximate_interval:
            return None, None, None, None, None

        # --- Перебор всех допустимых интервалов ---
        for begin in range(n - self.min_approximate_interval + 1):
            for end in range(begin + self.min_approximate_interval - 1, n):
                fractal_lambda, r_squared, std_error = fract_dimension_finder(
                    log_x[begin:end + 1], log_y[begin:end + 1]
                )
                if fractal_lambda is None:
                    continue

                # --- Выбор наилучшего интервала по минимальному λ ---
                if float(fractal_lambda) < best_lambda:
                    best_lambda = float(fractal_lambda)
                    best_begin = begin
                    best_end = end
                    best_r_squared = r_squared
                    best_std_error = std_error

        return best_lambda, best_r_squared, best_std_error, best_begin, best_end
