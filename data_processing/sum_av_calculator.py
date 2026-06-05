import pandas as pd
from PyQt5.QtCore import QObject, pyqtSignal
from data_processing.fract_dimension_calc import fract_dimension_finder, coords_to_log

class DsumAvCalculatorWorker(QObject):
    error_occurred = pyqtSignal(str)                 # Сигнал для передачи сообщений об ошибках
    progress_changed = pyqtSignal(int, str)    # Сигнал для обновления прогресса и логов
    log_changed = pyqtSignal(str)                    # Сигнал для обновления логов

    def __init__(self):
        super().__init__(parent=None)

        # --- Названия колонок ---
        self.bass_id_col: str | None = None       # Колонка с ID бассейна
        self.lat_col: str | None = None           # Колонка с широтой центроида
        self.long_col: str | None = None          # Колонка с долготой центроида
        self.perimeter_col: str | None = None     # Колонка с периметром бассейна
        self.area_col: str | None = None          # Колонка с площадью бассейна
        self.gridcode_col: str | None = None      # Колонка с порядком (gridcode)
        self.river_id_col: str | None = None      # Колонка с ID реки
        self.river_length_col: str | None = None  # Колонка с длиной реки

        # --- Ограничения (на площадь/периметр) ---
        self.bass_area_limits: list | None = None        # [min, max] по площади
        self.bass_perimeter_limits: list | None = None   # [min, max] по периметру

        # --- Настройки фильтрации и анализа ---
        self.selected_grid_codes: list[int] = []         # Список выбранных gridcode'ов
        self.gridcode_ranges: dict[int, tuple] = {}      # Диапазоны длин по gridcode: {gridcode: (min, max)}
        self.min_gridcode_num: int | None = None         # Минимальное количество точек для аппроксимации

        # --- Внутренние структуры данных ---
        self.length_for_basins: list[list[float]] = []      # Списки длин русел для каждого бассейна
        self.result_dict: dict = {                          # Хранилище результатов
            'bass_id': [],
            'longitude': [],
            'latitude': [],
            'perimeter': [],
            'area': [],
            'gridcode_value': [],
            'Dh_sum': [],
            'r_squared_sum': [],
            'std_error_sum': [],
            'Dh_ave': [],
            'r_squared_ave': [],
            'std_error_ave': [],
        }
        self.result: pd.DataFrame | None = None             # Финальный DataFrame-результат

    def set_bass_id_col(self, column_name: str): self.bass_id_col = column_name
    def set_lat_col(self, column_name: str): self.lat_col = column_name
    def set_long_col(self, column_name: str): self.long_col = column_name
    def set_perimeter_col(self, column_name: str): self.perimeter_col = column_name
    def set_area_col(self, column_name: str): self.area_col = column_name
    def set_area_limits(self, limits_list): self.bass_area_limits = limits_list
    def set_perimeter_limits(self, limits_list): self.bass_perimeter_limits = limits_list
    def set_gridcode_col(self, column_name: str): self.gridcode_col = column_name
    def set_min_gridcode_num(self, value: int): self.min_gridcode_num = value
    def set_river_id_col(self, column_name: str): self.river_id_col = column_name
    def set_river_length_col(self, column_name: str): self.river_length_col = column_name
    def set_selected_gridcodes(self, gridcodes_list: list): self.selected_grid_codes = gridcodes_list
    def set_gridcode_ranges(self, ranges_dict): self.gridcode_ranges = ranges_dict

    def calculate_dsum_av(self, data: pd.DataFrame):
        """
        Выполняет расчёт двух оценок фрактальной размерности Dh (по сумме и среднему длин русел)
        для каждого бассейна на основе иерархии порядков русел (gridcode).

        Метод проходит по каждому старшему бассейну, фильтрует его по заданным лимитам
        площади и периметра, затем группирует данные по порядкам русел (gridcode),
        применяет фильтрацию по длинам и формирует два набора координат:
            - сумма длин водотоков данного порядка (Dh_sum)
            - средняя длина водотоков данного порядка (Dh_ave)

        На основе логарифмической аппроксимации координат (log-сумма/среднее — log(N))
        рассчитываются:
            - наклон регрессии (Dh)
            - коэффициент детерминации (R²)
            - стандартная ошибка (std_error)

        Все промежуточные и итоговые данные сохраняются в self.result_dict
        и формируют выходной DataFrame self.result.

        Параметры:
        ----------
        data : pd.DataFrame
            Входной DataFrame, содержащий:
            - информацию о бассейнах и отрезках рек,
            - координаты (широта, долгота),
            - площадь, периметр, ID и длины рек, gridcode.

        Требования:
        -----------
        Перед запуском метода необходимо установить:
        - имена всех колонок (set_bass_id_col и др.)
        - список допустимых gridcode'ов (set_selected_gridcodes)
        - словарь ограничений длин по gridcode (set_gridcode_ranges)
        - минимальное количество gridcode для включения бассейна в расчёт (set_min_gridcode_num)
        - (опционально) ограничения по площади и периметру (set_area_limits, set_perimeter_limits)

        Результат:
        ----------
        Заполняет self.result — DataFrame с колонками:
            - bass_id, longitude, latitude, perimeter, area,
            - Dh_sum, r_squared_sum, std_error_sum,
            - Dh_ave, r_squared_ave, std_error_ave

        Исключения:
        -----------
        При возникновении ошибок:
        - вызывается error_occurred(str) или log_changed(str)
        - прогресс обновляется через progress_changed(int, str)
        """
        # --- Удаляем строки с пустыми значениями, группируем данные по bass_id_col ---
        grouped_data = data.dropna(subset=[self.bass_id_col]).groupby(self.bass_id_col)

        # --- Замена десятичных разделителей на точку ---
        for column in [self.perimeter_col, self.area_col, self.river_length_col, self.long_col, self.lat_col]:
            data[column] = data[column].apply(
                lambda x: float(str(x).replace(',', '.')) if isinstance(x, str) else x)

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
            self.result_dict['longitude'].append(float(bass_group[self.long_col].iloc[0]))
            self.result_dict['latitude'].append(float(bass_group[self.lat_col].iloc[0]))
            self.result_dict['perimeter'].append(float(current_bass_area))
            self.result_dict['area'].append(float(current_bass_perimeter))

            # --- Обновляем список для каждого бассейна ---
            self.length_for_basins = []

            # --- Отфильтровываем строки только для тех порядков, которые есть в selected_grid_codes ---
            orders_group = bass_group[bass_group[self.gridcode_col].isin(self.selected_grid_codes)].groupby(
                self.gridcode_col)

            valid_grid_codes = []  # Список для порядков русел, находящихся в данном бассейне

            for gridcode_value in self.selected_grid_codes:
                if gridcode_value in orders_group.groups:
                    grid_group = orders_group.get_group(gridcode_value)
                    unique_rivers = grid_group.drop_duplicates(subset=[self.river_id_col])

                    # Фильтрация по диапазонам длин
                    mask_length = unique_rivers.apply(
                        lambda row: self._is_within_limits(row[self.river_length_col],
                                                           self.gridcode_ranges.get(row[self.gridcode_col],
                                                                                    (None, None))),
                        axis=1
                    )
                    filtered_group = unique_rivers.loc[mask_length]

                    # Извлекаем длины и создаем список
                    length_list = filtered_group[self.river_length_col].tolist()

                    # Если после фильтрации остались водотоки, то порядок валиден
                    if length_list:
                        valid_grid_codes.append(gridcode_value)

                    self.length_for_basins.append(length_list)
                else:
                    # Если нет значений для данного gridcode, добавляем пустой список
                    self.length_for_basins.append([])

            grid_codes_str = '_'.join(map(str, valid_grid_codes))

            if len(valid_grid_codes) < self.min_gridcode_num:
                self.log_changed.emit(f"<span style='color:red;'>Пропускаем бассейн {self.result_dict['bass_id'][-1]}"
                                      f" с порядками русел: {grid_codes_str}</span>")

                self.result_dict['gridcode_value'].append(grid_codes_str)
                self.result_dict['Dh_sum'].append('')
                self.result_dict['r_squared_sum'].append('')
                self.result_dict['std_error_sum'].append('')
                self.result_dict['Dh_ave'].append('')
                self.result_dict['r_squared_ave'].append('')
                self.result_dict['std_error_ave'].append('')
                continue

            try:
                log_sum, lod_average, log_n = self._calculate_river_length_stats()
                dh_sum1, r_squared1, std_error1 = fract_dimension_finder(log_sum, log_n)
                dh_ave, r_squared2, std_error2 = fract_dimension_finder(lod_average, log_n)
            except Exception as e:
                self.log_changed.emit(f"<span style='color:red;'>Пропускаем бассейн {self.result_dict['bass_id'][-1]}"
                                      f" с порядками русел: {grid_codes_str}</span>")

                self.result_dict['gridcode_value'].append(grid_codes_str)
                self.result_dict['Dh_sum'].append('')
                self.result_dict['r_squared_sum'].append('')
                self.result_dict['std_error_sum'].append('')
                self.result_dict['Dh_ave'].append('')
                self.result_dict['r_squared_ave'].append('')
                self.result_dict['std_error_ave'].append('')
                continue

            self.result_dict['gridcode_value'].append(grid_codes_str)
            self.result_dict['Dh_sum'].append(dh_sum1)
            self.result_dict['r_squared_sum'].append(r_squared1)
            self.result_dict['std_error_sum'].append(std_error1)
            self.result_dict['Dh_ave'].append(-dh_ave)
            self.result_dict['r_squared_ave'].append(r_squared2)
            self.result_dict['std_error_ave'].append(std_error2)

        self.result = pd.DataFrame(self.result_dict)
        self.progress_changed.emit(100, "Выходной файл создан и ожидает сохранения")

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

    def _calculate_river_length_stats(self):
        """
        Рассчитывает логарифмы суммарной и средней длины русел по каждому gridcode.

        Используется при построении логарифмических зависимостей Dh_sum и Dh_ave
        от числа русел заданного порядка.

        :return: tuple — log_sum, log_average, log_n
        """
        sum_list = []
        average_list = []
        riv_counts = []

        for i in range(len(self.selected_grid_codes)):
            if self.length_for_basins[i]:  # Проверяем, есть ли данные для текущего gridcode
                gridcode_sum = sum(self.length_for_basins[i])
                sum_list.append(gridcode_sum)

                gridcode_average = gridcode_sum / len(self.length_for_basins[i])
                average_list.append(gridcode_average)

                riv_counts.append(len(self.length_for_basins[i]))

        log_sum, log_n = coords_to_log(sum_list, riv_counts)
        log_average, _ = coords_to_log(average_list, riv_counts)

        return log_sum, log_average, log_n
