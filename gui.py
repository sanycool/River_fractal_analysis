from PyQt5.QtWidgets import (
    QMainWindow, QMenu, QMenuBar, QAction, QTabWidget, QWidget, QVBoxLayout, QTableView, QLabel,
    QApplication, QFileDialog, QMessageBox, QTextBrowser)
from PyQt5.QtGui import QIcon, QStandardItemModel
from PyQt5.QtCore import Qt

import sys
import pandas as pd
from pathlib import Path

from visualization.table_widget import PandasModel
from dialogs.riv_connect_dialog import DialogRivConnect
from dialogs.calc_dps_dialog import DialogCalcDps
from dialogs.calc_lambda_dialog import DialogCalcLambda
from dialogs.calc_dsum_av_dialog import DialogCalcDsumAv
from dialogs.calc_dcor_dialog import DialogCalcDcor


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        """Настройка всего интерфейса главного окна"""
        self._setup_my_window(MainWindow)           # Настройка вида окна
        self._setup_menu_bar(MainWindow)            # Создание меню-бара
        self._setup_file_menu(MainWindow)           # Создание меню "Файл" с действиями
        self._setup_calculation_menu(MainWindow)    # Создание меню "Расчёт" с методами анализа
        self._setup_central_widget(MainWindow)      # Создание центральная зона для таблицы или справки

    def _setup_my_window(self, window):
        """Установка заголовка, размера и иконки окна"""
        window.setWindowTitle("River Fractal Analysis")
        window.setWindowState(Qt.WindowMaximized)
        self.setWindowIcon(QIcon("icons/main.png"))

    def _setup_menu_bar(self, window):
        """Создание и добавление меню-бара в главное окно"""
        self.menu_bar = QMenuBar(window)
        window.setMenuBar(self.menu_bar)

        # --- Меню "Файл" ---
        self.file_menu = QMenu("Файл", window)
        self.menu_bar.addMenu(self.file_menu)

        # --- Меню "Расчёт" ---
        self.calculation_menu = QMenu("Расчёт", window)
        self.menu_bar.addMenu(self.calculation_menu)

    def _setup_file_menu(self, window):
        """Добавление пунктов в меню "Файл" """
        self.open_file_action = QAction("Открыть файл", window)
        self.save_as_action = QAction("Сохранить как", window)
        self.close_file_action = QAction("Закрыть файл", window)
        self.exit_action = QAction("Выход", window)

        self.file_menu.addAction(self.open_file_action)
        self.file_menu.addAction(self.save_as_action)
        self.file_menu.addAction(self.close_file_action)
        self.file_menu.addSeparator()  # Разделитель
        self.file_menu.addAction(self.exit_action)

    def _setup_calculation_menu(self, window):
        """Добавление методов анализа в меню "Расчёт" """
        self.connect_segments_action = QAction("Соединить фрагменты водотоков", window)
        self.calculate_dps_action = QAction("Расчёт D", window)
        self.calculate_dh_action = QAction("Расчёт D_Hav и D_Hsum", window)
        self.calculate_lambda_action = QAction("Расчёт λ (лямбда)", window)
        self.calculate_dcor_action = QAction("Расчёт D_cor", window)

        self.calculation_menu.addAction(self.connect_segments_action)
        self.calculation_menu.addSeparator()  # Разделитель
        self.calculation_menu.addAction(self.calculate_dps_action)
        self.calculation_menu.addAction(self.calculate_dh_action)
        self.calculation_menu.addAction(self.calculate_lambda_action)
        self.calculation_menu.addAction(self.calculate_dcor_action)

    def _setup_central_widget(self, window):
        """
            Настройка центрального виджета:
            включает вертикальный layout с таблицей (QTableView),
            которая будет использоваться для отображения CSV-файла.
        """
        self.central_widget = QWidget(window)
        window.setCentralWidget(self.central_widget)

        self.table_layout = QVBoxLayout(self.central_widget)
        self.table_view = QTableView(parent=None)  # Виджет для отображения таблицы CSV
        self.table_view.setSortingEnabled(True)  # Включение сортировки
        self.table_layout.addWidget(self.table_view)


class RiverApp(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.data = None        # Исходный DataFrame
        self.column_names = []  # Хранение названий колонок

        # --- Подключение действий из меню "Файл" ---
        self.open_file_action.triggered.connect(self.open_file)
        self.save_as_action.triggered.connect(self.save_as)
        self.close_file_action.triggered.connect(self.close_file)
        self.exit_action.triggered.connect(self.close_application)

        # --- Подключение действий из меню "Расчет" ---
        self.connect_segments_action.triggered.connect(self.open_connect_segments_dialog)
        self.calculate_dps_action.triggered.connect(self.open_calculate_dps_dialog)
        self.calculate_dh_action.triggered.connect(self.open_calculate_dh_dialog)
        self.calculate_lambda_action.triggered.connect(self.open_calculate_lambda_dialog)
        self.calculate_dcor_action.triggered.connect(self.open_calculate_dcor_dialog)

        self.load_data_into_table()

    # --- Методы для пунктов меню "Файл" ---
    def open_file(self):
        """Открытие csv файла"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Открыть CSV файл", "", "CSV Files (*.csv)")
        if file_path:
            try:
                # --- Загрузка данных из CSV файла в DataFrame ---
                self.data = pd.read_csv(file_path, sep=";")

                # --- Отображение данных в QTableView ---
                self.load_data_into_table()
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить файл: {e}")

    def load_data_into_table(self):
        """Отображение данных из self.data в QTableView или справки, если данных нет"""
        if self.data is not None:
            if hasattr(self, 'help_tabs'):
                self.table_layout.removeWidget(self.help_tabs)
                self.help_tabs.deleteLater()
                del self.help_tabs

            model = PandasModel(self.data)
            self.table_view.setModel(model)
            self.table_view.show()
        else:
            self.table_view.hide()
            self.show_help_tabs()

    def show_help_tabs(self):
        """Показывает справку по программе во вкладках"""
        self.help_tabs = QTabWidget(self)
        self.table_layout.addWidget(self.help_tabs)

        # --- Вкладка 1: Общая информация ---
        self._add_help_tab("Приветствие", "help_docs/intro.html")
        self._add_help_tab("Соединение фрагментов водотоков", "help_docs/connect_segments.html")
        self._add_help_tab("Расчёт D", "help_docs/dps.html")
        self._add_help_tab("Расчёт D_Hav", "help_docs/dsum_av.html")
        self._add_help_tab("Расчёт λ (лямбда)", "help_docs/lambda.html")
        self._add_help_tab("Расчёт D_cor", "help_docs/dcor.html")

    def _add_help_tab(self, title: str, file_path: str):
        """Добавляет вкладку с HTML содержимым из внешнего файла"""
        browser = QTextBrowser(self)
        try:
            with open(file_path, encoding="utf-8") as f:
                html = f.read()
                browser.setHtml(html)
        except Exception as e:
            browser.setHtml(f"<p style='color:red;'>Ошибка загрузки файла {file_path}: {e}</p>")

        browser.setOpenExternalLinks(True)
        browser.setStyleSheet("background-color: #2e2e2e; color: white; padding: 10px;")
        self.help_tabs.addTab(browser, title)

    def save_as(self):
        """Открытие диалогового окна для сохранения файла"""
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить как", "", "CSV Files (*.csv)")
        if file_path:
            try:
                self.data.to_csv(file_path, sep=";", index=False)
                QMessageBox.information(self, "Файл сохранён", f"Файл успешно сохранён в {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")

    def close_file(self):
        """Действие для закрытия текущего файла"""
        self.data = None
        self.load_data_into_table()
        QMessageBox.information(self, "Закрытие файла", "Текущий файл закрыт")

    def close_application(self):
        """Закрытие приложения"""
        reply = QMessageBox.question(self, "Выход", "Вы действительно хотите выйти?", QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()

    # --- Методы для расчётов из меню "Расчет" ---
    def open_connect_segments_dialog(self):
        """Диалог для соединения отрезков рек"""
        if self.data is None:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите CSV файл.")
            return

        dialog = DialogRivConnect(self.data, self)

        if dialog.exec_():
            self.load_data_into_table()  # Отображение данных в QTableView

    def open_calculate_dps_dialog(self):
        """Диалог для расчёта D"""
        if self.data is None:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите CSV файл.")
            return

        dialog = DialogCalcDps(self.data, self)

        if dialog.exec_():
            pass

    def open_calculate_dh_dialog(self):
        """Диалог для расчёта D_Hav"""
        if self.data is None:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите CSV файл.")
            return

        dialog = DialogCalcDsumAv(self.data, self)

        if dialog.exec_():
            pass

    def open_calculate_lambda_dialog(self):
        """Диалог для расчёта lambda"""
        if self.data is None:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите CSV файл.")
            return

        dialog = DialogCalcLambda(self.data, self)

        if dialog.exec_():
            pass

    def open_calculate_dcor_dialog(self):
        """Диалог для расчёта D_cor"""
        if self.data is None:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите CSV файл.")
            return

        dialog = DialogCalcDcor(self.data, self)

        if dialog.exec_():
            pass
