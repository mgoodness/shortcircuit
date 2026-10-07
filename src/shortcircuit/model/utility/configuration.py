from PySide6 import QtCore

from shortcircuit import __appslug__
from shortcircuit.model.utility.singleton import Singleton


class Configuration(metaclass=Singleton):
  settings = QtCore.QSettings(
    QtCore.QSettings.IniFormat,
    QtCore.QSettings.UserScope,
    __appslug__,
  )
