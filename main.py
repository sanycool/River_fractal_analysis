from PyQt5.QtWidgets import QApplication
from PyQt5 import QtGui
import sys
from gui import RiverApp

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # --- Cтиль Fusion для современного вида ---
    app.setStyle("Fusion")

    # --- Настройка палитры для более современного вида ---
    palette = app.palette()
    palette.setColor(app.palette().Window, QtGui.QColor(53, 53, 53))
    palette.setColor(app.palette().WindowText, QtGui.QColor(255, 255, 255))
    palette.setColor(app.palette().Base, QtGui.QColor(25, 25, 25))
    palette.setColor(app.palette().AlternateBase, QtGui.QColor(53, 53, 53))
    palette.setColor(app.palette().ToolTipBase, QtGui.QColor(255, 255, 255))
    palette.setColor(app.palette().ToolTipText, QtGui.QColor(255, 255, 255))
    palette.setColor(app.palette().Text, QtGui.QColor(255, 255, 255))
    palette.setColor(app.palette().Button, QtGui.QColor(53, 53, 53))
    palette.setColor(app.palette().ButtonText, QtGui.QColor(255, 255, 255))
    palette.setColor(app.palette().BrightText, QtGui.QColor(255, 0, 0))
    palette.setColor(app.palette().Link, QtGui.QColor(42, 130, 218))
    app.setPalette(palette)

    window = RiverApp()
    window.show()
    sys.exit(app.exec_())