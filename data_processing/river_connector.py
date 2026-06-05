import pandas as pd
from PyQt5.QtCore import QObject, pyqtSignal


class RiverConnectorWorker(QObject):
    error_occurred = pyqtSignal(str)            # Сигнал для передачи сообщений об ошибках
    progress_changed = pyqtSignal(int, str)     # Сигнал для обновления прогресса и логов

    def __init__(self):
        super().__init__(parent=None)

        # --- Названия колонок ---
        self.from_node_column: str or None = None
        self.to_node_column: str or None = None
        self.grid_code_column: str or None = None
        self.segments_length_column: str or None = None
        self.river_id_column:str = "ID_RIVER"
        self.river_length_column:str = "R_LENGTH"

        # --- Флаг включения расчета длин соединенных фрагментов ---
        self.calculate_length: bool = False

    def set_from_node_column(self, column:str): self.from_node_column = column
    def set_to_node_column(self, column:str): self.to_node_column = column
    def set_grid_code_column(self, column:str): self.grid_code_column = column
    def set_segments_length_column(self, column:str): self.segments_length_column = column
    def do_calculate_length(self, flag:bool): self.calculate_length = flag

    def river_data_reorganization(self, data: pd.DataFrame):
        """
        Выполняет полную переработку данных о сегментах рек:
        - очищает данные от пропущенных значений,
        - приводит числовые поля к корректному формату,
        - запускает алгоритм объединения отрезков рек по ID узлов,
        - при необходимости рассчитывает суммарную длину объединённых рек.

        Параметры:
        ----------
        data : pd.DataFrame
            Таблица с исходными данными, содержащая:
            - идентификаторы начала и конца отрезков (узлы),
            - порядки водотоков (grid_code),
            - (опционально) длины сегментов.

        Требования:
        -----------
        Перед вызовом метода должны быть заданы:
        - self.grid_code_column, self.from_node_column, self.to_node_column
        - self.segments_length_column — если включён режим расчёта длин
        - self.calculate_length = True — для запуска длинового расчёта

        Исключения:
        -----------
        При возникновении ошибок вызывает:
        - self.error_occurred(str)
        """
        try:
            # --- Удаляем строки с пустыми значениями ---
            data.dropna(subset=[self.grid_code_column, self.from_node_column, self.to_node_column], inplace=True)

            # --- Замена десятичных разделителей на точку ---
            for column in [self.grid_code_column, self.from_node_column, self.to_node_column]:
                data[column] = pd.to_numeric(
                    data[column].astype(str).str.replace(',', '.', regex=False),
                    errors='coerce'
                )
        except ValueError as e:
            self.error_occurred.emit(f"Ошибка преобразования данных:\n{e}")
            return

        self._assign_river_ids(data)

        if not self.calculate_length:
            return

        try:
            # --- Удаляем строки с пустыми значениями ---
            data.dropna(subset=[self.segments_length_column], inplace=True)

            # --- Замена десятичных разделителей на точку ---
            data[self.segments_length_column] = pd.to_numeric(
                data[self.segments_length_column].astype(str).str.replace(',', '.', regex=False),
                errors='coerce'
            )
        except ValueError as e:
            self.error_occurred.emit(f"Ошибка преобразования данных:\n{e}")
            return

        self._length_calculation(data)


    def _assign_river_ids(self, data: pd.DataFrame):
        """
        Объединяет отрезки рек в связные компоненты на основе идентификаторов узлов,
        присваивая каждой компоненте уникальный идентификатор river_id.

        Логика:
        -------
        1. Для каждой группы отрезков с одинаковым порядком (grid_code) строится граф связей.
        2. В графе объединяются отрезки, соединённые общими узлами.
        3. Каждой компоненте графа назначается уникальный river_id.
        4. Итоговая таблица объединяется с исходной, формируя новую колонку.

        Параметры:
        ----------
        data : pd.DataFrame
            Таблица с колонками:
            - self.grid_code_column
            - self.from_node_column
            - self.to_node_column

        Результат:
        ----------
        Добавляется колонка self.river_id_column с идентификаторами объединённых рек.

        Исключения:
        -----------
        При ошибках передаёт сообщение через self.error_occurred(str)
        и останавливает выполнение.
        """
        try:
            data[self.river_id_column] = -1     # Создание колонки для результата
            current_river_id = 1    # Начальный идентификатор для каждой группы
            river_data = []         # Список для хранения данных о компонентах связности

            # --- Группируем данные по bass_id_col ---
            gridcode_groups = data.groupby(self.grid_code_column)

            total_steps = len(gridcode_groups)  # Общее количество шагов для прогресс-бара
            step = 0  # Шаг для прогресса

            # --- Обработка порядков водотоков ---
            for gridcode, group in gridcode_groups:
                step += 1
                progress = int((step / total_steps) * 100)  # Рассчитываем процент выполнения
                if progress == 100: progress = 99
                self.progress_changed.emit(progress, f"Обработка gridcode: {gridcode}")  # Отправляем сигнал с текущим прогрессом

                node_graph = {}  # Граф для объединения всех узлов

                for _, row in group.iterrows():
                    from_node = row[self.from_node_column]
                    to_node = row[self.to_node_column]

                    if from_node not in node_graph:
                        node_graph[from_node] = {from_node}
                    if to_node not in node_graph:
                        node_graph[to_node] = {to_node}

                    union_set = node_graph[from_node] | node_graph[to_node]
                    for node in union_set:
                        node_graph[node] = union_set

                for component in set(map(frozenset, node_graph.values())):
                    for node in component:
                        river_data.append((gridcode, node, current_river_id))
                    current_river_id += 1

            self.progress_changed.emit(99, "Обновление таблицы...")

            river_df = pd.DataFrame(river_data, columns=[self.grid_code_column, 'node', 'river_id'])

            df_from = data[[self.grid_code_column, self.from_node_column]].rename(columns={self.from_node_column: 'node'})
            df_to = data[[self.grid_code_column, self.to_node_column]].rename(columns={self.to_node_column: 'node'})

            df_long = pd.concat([df_from, df_to])
            df_merged = pd.merge(df_long, river_df, on=[self.grid_code_column, 'node'], how='left')

            data[self.river_id_column] = df_merged['river_id'].groupby(df_merged.index).first()

            self.progress_changed.emit(100, f"Таблица обновлена: добавлена колонка '{self.river_id_column}' с "
                                            "индентификаторами объединенных водотоков")

        except Exception as e:
            self.error_occurred.emit(f"Произошла ошибка во время объединения сегментов водотоков:\n{e}")
            return

    def _length_calculation(self, data: pd.DataFrame):
        """
        Выполняет расчёт суммарной длины объединённых рек на основе их идентификаторов (river_id).

        Логика:
        -------
        1. Группирует таблицу по колонке self.river_id_column.
        2. Внутри каждой группы выбирает уникальные сегменты (по from_node).
        3. Суммирует длины этих уникальных сегментов.
        4. Результат записывается в новую колонку self.river_length_column.

        Параметры:
        ----------
        data : pd.DataFrame
            Исходная таблица с:
            - self.river_id_column
            - self.segments_length_column

        Результат:
        ----------
        Добавляется колонка self.river_length_column с длинами объединённых рек.

        Исключения:
        -----------
        При ошибках передаёт сообщение через self.error_occurred(str)
        и завершает выполнение.
        """
        try:
            # Группируем данные по river
            grouped = data.groupby(self.river_id_column)

            self.total_steps = len(grouped)  # Общее количество шагов
            self.current_step = 0  # Счетчик текущего прогресса

            # Применяем функцию unique_sum к каждой группе
            # sums - DataFrame, в котором каждая группа имеет столбец 'r_length' с суммой длин узлов
            sums = grouped.apply(
                lambda group: self._unique_sum(group)).reset_index(name=self.river_length_column)
            data[self.river_length_column] = data[self.river_id_column].map(
                sums.set_index(self.river_id_column)[self.river_length_column])
            self.progress_changed.emit(100, f"Таблица обновлена: добавлена колонка '{self.river_length_column}' с "
                                            "длинами объединенных водотоков")
        except Exception as e:
            self.error_occurred.emit(f"Произошла ошибка во время расчета длин:\n{e}")
            return

    def _unique_sum(self, group) -> float:
        """
        Считает сумму длин уникальных сегментов в группе (на основе from_node).
        Применяется внутри группировки по river_id для избежания двойного учёта.
        Также обновляет прогресс выполнения через self.progress_changed(int, str)

        Параметры:
        ----------
        group : pd.DataFrame
            Группа сегментов, объединённых одним river_id.

        Возвращает:
        -----------
        float — сумма длин уникальных сегментов.
        """
        unique_group = group.drop_duplicates(subset=self.from_node_column)

        # Обновляем счетчик и прогресс
        self.current_step += 1
        progress = int((self.current_step / self.total_steps) * 100)
        self.progress_changed.emit(progress, f"Обработка группы {self.current_step} из {self.total_steps}")

        return unique_group[self.segments_length_column].sum()
