import pandas as pd
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from data_processing.fract_dimension_calc import fract_dimension_finder, coords_to_log


class DcorCalculatorWorker(QObject):
    error_occurred = pyqtSignal(str)                 # Сигнал для передачи сообщений об ошибках
    progress_changed = pyqtSignal(int, str)    # Сигнал для обновления прогресса и логов
    log_changed = pyqtSignal(str)                    # Сигнал для обновления логов

    def __init__(self):
        super().__init__(parent=None)

        # --- Названия колонок ---
        self.bass_id_col: str | None = None             # Колонка с ID бассейна
        self.lat_col: str | None = None                 # Колонка с широтой центроида
        self.long_col: str | None = None                # Колонка с долготой центроида
        self.perimeter_col: str | None = None           # Колонка с периметром бассейна
        self.area_col: str | None = None                # Колонка с площадью бассейна
        self.node_id_col: str | None = None             # Колонка с ID точки бифуркации
        self.node_lat_col: str | None = None            # Колонка с широтой точки бифуркации
        self.node_long_col: str | None = None           # Колонка с долготой точки бифуркации
        self.node_grid_code_col: str | None = None      # Колонка с порядком точки бифуркации

        # --- Ограничения (на площадь/периметр) ---
        self.bass_area_limits: list | None = None           # [min, max] по площади
        self.bass_perimeter_limits: list | None = None      # [min, max] по периметру

        # --- Настройки фильтрации и анализа ---
        self.selected_grid_codes: list[int] = []            # Список выбранных gridcode'ов
        self.target_grid_codes: list[int] = []              # Список выбранных критических порядков
        self.scale_step_num: int or None = None             # Значение шага масштабов r (в метрах)
        self.min_nodes_num: int | None = None               # Минимальное число точек бифуркации
        self.min_target_grid_codes_num: int | None = None   # Минимальное число критических порядков
        self.min_approximation_interval: int | None = None  # Значение минимального интервала аппроксимации
        self.earth_radius_value: float = 6371.0             # Значение радиуса Земли в области исследования (в км)

        # --- Внутренние структуры данных ---
        self.nodes_grid_codes_sorted_list: list[int] = []   # Список порядков точек бифуркации текущего бассейна
        self.result_dict: dict = {                          # Хранилище результатов
            'bass_id': [],
            'bass_lat': [],
            'bass_long': [],
            'bass_perimeter': [],
            'bass_area': [],
            'grid_codes': [],
            'nodes_num': [],
            'approximation_interval': [],
            'd_cor': [],
            'r_squared_c': [],
            'std_error_c': [],
        }
        self.result: pd.DataFrame | None = None             # Финальный DataFrame-результат

    def set_bass_id_col(self, column_name: str): self.bass_id_col = column_name
    def set_lat_col(self, column_name: str): self.lat_col = column_name
    def set_long_col(self, column_name: str): self.long_col = column_name
    def set_perimeter_col(self, column_name: str): self.perimeter_col = column_name
    def set_area_col(self, column_name: str): self.area_col = column_name
    def set_area_limits(self, limits_list): self.bass_area_limits = limits_list
    def set_perimeter_limits(self, limits_list): self.bass_perimeter_limits = limits_list
    def set_node_id_col(self, column_name: str): self.node_id_col = column_name
    def set_node_lat_col(self, column_name: str): self.node_lat_col = column_name
    def set_node_long_col(self, column_name: str): self.node_long_col = column_name
    def set_node_grid_code_col(self, column_name: str): self.node_grid_code_col = column_name
    def set_selected_grid_codes(self, grid_codes_list: list): self.selected_grid_codes = grid_codes_list
    def set_target_grid_codes(self, grid_codes_list: list): self.target_grid_codes = grid_codes_list
    def set_scale_step_num(self, value: int): self.scale_step_num = value
    def set_min_nodes_num(self, value: int): self.min_nodes_num = value
    def set_min_target_grid_codes(self, value: int): self.min_target_grid_codes_num = value
    def set_min_approximation_interval(self, value: int): self.min_approximation_interval = value
    def set_earth_radius_value(self, value: float): self.earth_radius_value = value

    def calculate_dcor(self, data:pd.DataFrame):
        """
        Выполняет расчёт корреляционной размерности D_c для каждого бассейна
        на основе пространственного распределения точек бифуркации.

        Метод проходит по каждому бассейну (группировка по self.bass_id_col), предварительно
        удаляя строки с пропущенными координатами, и преобразует данные с десятичным
        разделителем в числовой формат.

        Для каждого бассейна:
            - проверяется соответствие ограничениям площади и периметра,
            - извлекаются уникальные точки бифуркации (по self.node_id_col),
            - проверяется наличие достаточного количества точек и порядков (gridcode),
            - вычисляется матрица попарных расстояний между точками (в метрах),
            - формируется набор масштабов (радиусов) r,
            - по логарифму C(r) — корреляционной суммы — строится линейная модель.

        На основе логарифмической аппроксимации ln(C(r)) ~ D_c·ln(r) рассчитываются:
            - корреляционная размерность (D_c),
            - коэффициент детерминации (R²),
            - стандартная ошибка аппроксимации.

        Все промежуточные и итоговые данные сохраняются в self.result_dict
        и формируют выходной DataFrame self.result.

        Параметры:
        ----------
        data : pd.DataFrame
            Входной DataFrame, содержащий:
            - координаты центроидов и точек бифуркации,
            - площадь, периметр, ID бассейнов,
            - gridcode'ы и идентификаторы точек.

        Требования:
        -----------
        Перед запуском метода необходимо установить:
        - имена всех колонок (set_bass_id_col и др.),
        - список допустимых gridcode'ов (set_selected_grid_codes),
        - минимальное количество точек (set_min_nodes_num),
        - (опционально) ограничения по площади и периметру (set_area_limits, set_perimeter_limits),
        - шаг масштабов (set_scale_step_num),
        - (опционально) минимальный интервал аппроксимации (set_min_approximation_interval),
        - значение радиуса Земли в регионе (set_earth_radius_value).

        Результат:
        ----------
        Заполняет self.result — DataFrame с колонками:
            - bass_id, longitude, latitude, perimeter, area,
            - grid_codes, nodes_num, approximation_interval,
            - d_cor, r_squared_c, std_error_c

        Исключения:
        -----------
        При возникновении ошибок:
        - вызывается error_occurred(str) или log_changed(str),
        - прогресс обновляется через progress_changed(int, str)
        """
        # --- Удаляем строки с пустыми значениями ---
        data = data.dropna(subset=[self.bass_id_col, self.node_lat_col, self.node_long_col])

        # --- Замена десятичных разделителей на точку ---
        for column in [self.perimeter_col, self.area_col, self.long_col, self.lat_col,
                       self.node_long_col, self.node_lat_col]:
            if column in data.columns:
                data.loc[:, column] = pd.to_numeric(data[column].astype(str).str.replace(',', '.'), errors='coerce')

        # --- Группировка данных по bass_id_col ---
        grouped_data = data.groupby(self.bass_id_col)

        total_steps = len(grouped_data)
        step = 0

        # --- Обработка главных бассейнов ---
        for _, bass_group in grouped_data:
            step += 1
            progress = int((step / total_steps) * 100)
            if progress == 100: progress = 99

            try:
                current_bass_id = int(bass_group[self.bass_id_col].iloc[0])  # ID текущего бассейна
                current_bass_area = bass_group[self.area_col].iloc[0]  # Площадь текущего бассейна
                current_bass_perimeter = bass_group[self.perimeter_col].iloc[0]  # Периметр текущего бассейна
            except Exception as e:
                self.error_occurred.emit(f"Ошибка получения параметров бассейна {current_bass_id}:\n{e}")
                return

            self.progress_changed.emit(progress, f"Обработка старших бассейнов: {current_bass_id}")

            # --- Фильтрация бассейнов ---
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

            self.result_dict['bass_id'].append(int(current_bass_id))
            self.result_dict['bass_lat'].append(float(bass_group[self.long_col].iloc[0]))
            self.result_dict['bass_long'].append(float(bass_group[self.lat_col].iloc[0]))
            self.result_dict['bass_perimeter'].append(float(current_bass_area))
            self.result_dict['bass_area'].append(float(current_bass_perimeter))

            unique_nodes_data = bass_group.drop_duplicates(subset=self.node_id_col)
            self.nodes_grid_codes_sorted_list = []

            # --- Проверка бассейна на валидность ---
            nodes_num = self._validate_bass_requirements(unique_nodes_data)
            if not self.nodes_grid_codes_sorted_list:
                self.log_changed.emit(f"<span style='color:red;'>Пропускаем бассейн {self.result_dict['bass_id'][-1]}"
                                      f" с количеством порядков точек бифуркации: {nodes_num}</span>")

                self.result_dict['grid_codes'].append('')
                self.result_dict['nodes_num'].append(nodes_num)
                self.result_dict['approximation_interval'].append('')
                self.result_dict['d_cor'].append('')
                self.result_dict['r_squared_c'].append('')
                self.result_dict['std_error_c'].append('')
                continue

            # --- Получение списка попарных расстояний между точками бифуркации ---
            distances = self._calculate_pairwise_distances(unique_nodes_data, nodes_num)

            # --- Получение списка масштабов r ---
            try:
                r_values = self._generate_r_values(distances)  # Значения масштабов для анализа
            except Exception as e:
                self.log_changed.emit(f"<span style='color:red;'>Ошибка при генерации списка радиусов для бассейна "
                                      f"{self.result_dict['bass_id'][-1]} с попарными расстояниями: {distances}:\n{e}</span>")

                self.result_dict['grid_codes'].append("_".join(map(str, self.nodes_grid_codes_sorted_list)))
                self.result_dict['nodes_num'].append(nodes_num)
                self.result_dict['approximation_interval'].append('')
                self.result_dict['d_cor'].append('')
                self.result_dict['r_squared_c'].append('')
                self.result_dict['std_error_c'].append('')
                continue

            # --- Вычисление корреляционной размерности ---
            d_cor, r_squared, std_error, begin, end = self._calculate_correlation_dimension(distances, nodes_num,
                                                                                            r_values)

            if d_cor is None:
                self.log_changed.emit(f"<span style='color:red;'>Ошибка при вычислении корреляционной размерности для бассейна"
                                      f"{self.result_dict['bass_id'][-1]}.\n"
                                      f"Уменьшите Значение шага масштабов r:\n{e}</span>")

                self.result_dict['grid_codes'].append("_".join(map(str, self.nodes_grid_codes_sorted_list)))
                self.result_dict['nodes_num'].append(nodes_num)
                self.result_dict['approximation_interval'].append('')
                self.result_dict['d_cor'].append('')
                self.result_dict['r_squared_c'].append('')
                self.result_dict['std_error_c'].append('')
                continue

            self.result_dict['grid_codes'].append("_".join(map(str, self.nodes_grid_codes_sorted_list)))
            self.result_dict['nodes_num'].append(nodes_num)
            self.result_dict['approximation_interval'].append(f"{begin + 1}-{end + 1}")
            self.result_dict['d_cor'].append(d_cor)
            self.result_dict['r_squared_c'].append(r_squared)
            self.result_dict['std_error_c'].append(std_error)

        self.result = pd.DataFrame(self.result_dict)
        self.progress_changed.emit(100, "Выходной файл создан и ожидает сохранения")

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

    def _validate_bass_requirements(self, unique_nodes_data: pd.DataFrame) -> int:
        """
        Проверка бассейна на минимальное число точек бифуркации и требуемые grid_code.

        :param unique_nodes_data: pd.DataFrame — уникальные точки бифуркации.
        :return: int — число уникальных точек.
        # --- Пояснение: Использование для предварительной фильтрации бассейнов.
        """
        # --- Получение числа уникальных точек бифуркации в бассейне ---
        nodes_num = len(unique_nodes_data)
        if nodes_num < self.min_nodes_num:
            self.log_changed.emit(f"<span style='color:red;'>Пропускаем бассейн {self.result_dict['bass_id'][-1]}"
                                  f" с недостаточным количеством точек бифуркации: {nodes_num}</span>")
            return nodes_num

        # --- Проверка наличия минимального количества критических порядков точек бифуркации ---
        nodes_grid_codes_list = unique_nodes_data[self.node_grid_code_col].unique().tolist()
        common_elements = set(nodes_grid_codes_list) & set(self.target_grid_codes)  # Используем пересечение множеств

        if len(common_elements) < self.min_target_grid_codes_num:
            self.log_changed.emit(f"<span style='color:red;'>Пропускаем бассейн {self.result_dict['bass_id'][-1]} "
                                  f"с недостаточным количеством требуемых порядков точек бифуркации: {common_elements}</span>")
            return nodes_num

        self.nodes_grid_codes_sorted_list = sorted(nodes_grid_codes_list)

        return nodes_num

    def _calculate_pairwise_distances(self, data: pd.DataFrame, nodes_num: int) -> np.ndarray:
        """
        Вычисление всех попарных расстояний между точками бифуркации.
        Используется сферическая формула для вычисления расстояний.

        :param data: pd.DataFrame — координаты точек.
        :param nodes_num: int — число точек.
        :return: np.ndarray — массив расстояний (в метрах).
        """
        # --- Преобразование координат к радианам для использования в формуле сферической тригонометрии ---
        coordinates = data[[self.node_lat_col, self.node_long_col]].astype(float).to_numpy()
        lat_rad = np.radians(coordinates[:, 0])
        lon_rad = np.radians(coordinates[:, 1])

        # --- Формирование двумерных сеток координат для попарного сравнения каждой точки с каждой ---
        # lat1, lon1: вертикальные векторы (столбцы); lat2, lon2: горизонтальные векторы (строки)
        lat1 = lat_rad[:, np.newaxis]  # (N, 1)
        lat2 = lat_rad[np.newaxis, :]  # (1, N)
        lon1 = lon_rad[:, np.newaxis]  # (N, 1)
        lon2 = lon_rad[np.newaxis, :]  # (1, N)

        # --- Вычисление попарных расстояний на сфере с помощью сферической косинусной формулы ---
        dlon = lon2 - lon1  # dlon — разница долгот между всеми парами точек
        cos_c = np.sin(lat1) * np.sin(lat2) + np.cos(lat1) * np.cos(lat2) * np.cos(dlon)
        cos_c = np.clip(cos_c, -1.0, 1.0)  # cos_c — косинусы центральных углов между точками
        c = np.arccos(cos_c)  # c — матрица центральных углов между точками (в радианах)
        distances_matrix = self.earth_radius_value * c * 1000  # в метрах

        # --- Использование верхней треугольной матрицы для получения уникальных пар расстояний ---
        i_upper = np.triu_indices(nodes_num, k=1)
        return distances_matrix[i_upper]

    def _generate_r_values(self, distances: np.ndarray) -> list:
        """
        Формирование списка масштабов r для анализа размерности.
        Формирует равномерную сетку r в диапазоне расстояний.

        :param distances: np.ndarray — массив расстояний.
        :return: list — список масштабов r (в метрах).
        """
        # --- Минимальное и максимальное значения ---
        min_distance = min(distances)
        max_distance = max(distances)

        # --- Стартовое значение не меньше scale_step_num ---
        start = max(self.scale_step_num, self.scale_step_num * np.ceil(min_distance / self.scale_step_num))
        end = self.scale_step_num * np.floor(max_distance / self.scale_step_num)

        if end <= start:
            return []

        # --- Генерация r со step = self.scale_step_num ---
        r_values = np.arange(start, end + self.scale_step_num, self.scale_step_num)
        return r_values.tolist()

    def _calculate_correlation_dimension(self, distances, nodes_num, r_values) -> tuple:
        """
        Вычисляет корреляционную размерность D_c на основе массива расстояний и шкал r.

        :param distances: np.ndarray, попарные расстояния между точками
        :param nodes_num: int, количество точек (узлов)
        :param r_values: list[float], значения масштабов (радиусов)
        :return: (d_cor, r_squared, std_error, begin, end) — параметры аппроксимации
            d_cor — фрактальная размерность
            r_squared — коэффициент детерминации
            std_error — ошибка аппроксимации
            begin, end — индексы интервала аппроксимации
        """
        # --- Вычисление корреляционной суммы C(r) для каждого r ---
        r_values = np.array(r_values, dtype=np.float64)
        correlation_sum_r = np.array([self._correlation_sum(distances, r) / (nodes_num ** 2) for r in r_values], dtype=np.float64)

        # --- Логарифмирование значений ---
        if correlation_sum_r[0] == 0:
            log_r = np.log(r_values[1:])
            log_correlation_sum_r = np.log(correlation_sum_r[1:])
        else:
            log_r = np.log(r_values)
            log_correlation_sum_r = np.log(correlation_sum_r)

        # --- Аппроксимация ---
        if self.min_approximation_interval and len(log_r) >= self.min_approximation_interval:
            # Поиск наилучшего интервала с достаточным количеством точек
            d_cor, r_squared, std_error, begin, end = self._dimension_with_best_interval(log_r, log_correlation_sum_r)
        elif not self.min_approximation_interval:
            # Аппроксимация по всей выборке
            d_cor, r_squared, std_error = fract_dimension_finder(log_r, log_correlation_sum_r)
            begin, end = 0, len(log_r) - 1
        else:
            return None, None, None, None, None

        return d_cor, r_squared, std_error, begin, end

    def _correlation_sum(self, distances, r) -> int:
        """
        Вычисление корреляционной суммы C(r) для заданного r.

        :param distances: np.ndarray — попарные расстояния.
        :param r: float — текущий масштаб.
        :return: int — количество пар с расстоянием < r.
        """
        C_r = np.sum(distances < r)
        return C_r

    def _dimension_with_best_interval(self, x_coords, y_coords) -> tuple:
        """
        Поиск интервала с максимальной корреляционной размерностью.
        Перебор всех возможных интервалов длиной не менее min_approximation_interval.

        :param x_coords: np.ndarray — log(r).
        :param y_coords: np.ndarray — log(C(r)).
        :return: (d_cor, r_squared, std_error, begin, end)
        """
        # --- Инициализация переменных для хранения наилучшего интервала ---
        best_begin = 0          # Индекс начала наилучшего интервала
        best_end = 0            # Индекс конца наилучшего интервала
        best_d_cor = 0.0        # Лучшее значение наклона (λ)
        best_r_squared = 0.0    # Наилучшее значение R²
        best_std_error = 0.0    # Наименьшая ошибка аппроксимации

        # --- Перебор всех возможных интервалов ---
        n = len(list(x_coords))
        for begin in range(n - self.min_approximation_interval + 1):
            for end in range(begin + self.min_approximation_interval - 1, n):
                d_cor, r_squared, std_error = fract_dimension_finder(x_coords[begin:end + 1],
                                                                              y_coords[begin:end + 1])
                if d_cor is None:
                    continue

                # --- Проверка на лучший интервал ---
                if float(d_cor) > best_d_cor:
                    best_d_cor = float(d_cor)
                    best_begin = begin
                    best_end = end
                    best_r_squared = r_squared
                    best_std_error = std_error

        return best_d_cor, best_r_squared, best_std_error, best_begin, best_end