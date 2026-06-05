from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant
import pandas as pd

class PandasModel(QAbstractTableModel):
    def __init__(self, data: pd.DataFrame):
        super().__init__()
        self._data = data  # Сохраняем DataFrame для использования в модели

    def rowCount(self, parent=None):
        """Возвращает количество строк в DataFrame"""
        return self._data.shape[0]

    def columnCount(self, parent=None):
        """Возвращает количество столбцов в DataFrame"""
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        """
        Возвращает данные для отображения в ячейках QTableView.
        role=Qt.DisplayRole указывает, что данные должны быть отображены как текст.
        """
        if index.isValid():
            if role == Qt.DisplayRole:
                # Получаем значение из DataFrame и преобразуем его в строку
                return str(self._data.iloc[index.row(), index.column()])
        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        Возвращает заголовки для строк и столбцов.
        Если orientation=Qt.Horizontal, возвращаем название столбца.
        Если orientation=Qt.Vertical, возвращаем индекс строки.
        """
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._data.columns[section]
            elif orientation == Qt.Vertical:
                return self._data.index[section]
        return QVariant()

    def sort(self, column, order=Qt.AscendingOrder):
        """
        Сортировка данных по указанному столбцу.
        column - индекс столбца для сортировки
        order - порядок сортировки (по возрастанию или убыванию)
        """
        col_name = self._data.columns[column]
        self.layoutAboutToBeChanged.emit()
        self._data = self._data.sort_values(
            col_name,
            ascending=(order == Qt.AscendingOrder),
            key=lambda col: col.str.lower() if col.dtype == "object" else col
        )
        self.layoutChanged.emit()
