from components.loginScreenUI import Ui_loginScreen
from PyQt5 import QtWidgets
import sys

class LoginScreen(QtWidgets.QMainWindow):
    def __init__(self):
        super(LoginScreen, self).__init__()
        self.ui = Ui_loginScreen()
        self.ui.setupUi(self)

def start():
    app = QtWidgets.QApplication(sys.argv)
    window = LoginScreen()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    start()