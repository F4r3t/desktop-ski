# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'design_matplotlib_2_adaptiveyNsLSc.ui'
##
## Created by: Qt User Interface Compiler version 6.11.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
                            QMetaObject, QObject, QPoint, QRect,
                            QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
                           QCursor, QFont, QFontDatabase, QGradient,
                           QIcon, QImage, QKeySequence, QLinearGradient,
                           QPainter, QPalette, QPixmap, QRadialGradient,
                           QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
                               QMainWindow, QMenu, QMenuBar, QPushButton,
                               QSizePolicy, QSpacerItem, QStatusBar, QVBoxLayout,
                               QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1018, 600)
        MainWindow.setMinimumSize(QSize(900, 600))
        MainWindow.setStyleSheet(u"QMainWindow, QWidget {\n"
                                 "    background-color: #f6f7fb;\n"
                                 "    color: #1f2937;\n"
                                 "    font-family: \"Segoe UI\";\n"
                                 "    font-size: 10pt;\n"
                                 "}\n"
                                 "\n"
                                 "QMenuBar {\n"
                                 "    background-color: #ffffff;\n"
                                 "    border-bottom: 1px solid #d9deea;\n"
                                 "    padding: 4px 8px;\n"
                                 "}\n"
                                 "\n"
                                 "QMenuBar::item {\n"
                                 "    background: transparent;\n"
                                 "    padding: 6px 10px;\n"
                                 "    border-radius: 6px;\n"
                                 "}\n"
                                 "\n"
                                 "QMenuBar::item:selected {\n"
                                 "    background: #e9eefc;\n"
                                 "}\n"
                                 "\n"
                                 "QMenu {\n"
                                 "    background-color: #ffffff;\n"
                                 "    border: 1px solid #d9deea;\n"
                                 "    padding: 6px;\n"
                                 "}\n"
                                 "\n"
                                 "QMenu::item {\n"
                                 "    padding: 7px 24px 7px 12px;\n"
                                 "    border-radius: 6px;\n"
                                 "}\n"
                                 "\n"
                                 "QMenu::item:selected {\n"
                                 "    background-color: #e9eefc;\n"
                                 "}\n"
                                 "\n"
                                 "QFrame#chartContainer {\n"
                                 "    background-color: #ffffff;\n"
                                 "    border: 1px solid #d9deea;\n"
                                 "    border-radius: 18px;\n"
                                 "}\n"
                                 "\n"
                                 "QFrame#chartPlaceholderFrame {\n"
                                 "    background-color: #fbfcff;\n"
                                 "    border: 2px dashed #c9d3ea;\n"
                                 "    border-radius: 14px;"
                                 "\n"
                                 "}\n"
                                 "\n"
                                 "QPushButton {\n"
                                 "    background-color: #ffffff;\n"
                                 "    border: 1px solid #cfd7ea;\n"
                                 "    border-radius: 10px;\n"
                                 "    padding: 10px 16px;\n"
                                 "    font-weight: 600;\n"
                                 "}\n"
                                 "\n"
                                 "QPushButton:hover {\n"
                                 "    background-color: #eef3ff;\n"
                                 "    border: 1px solid #b8c6ea;\n"
                                 "}\n"
                                 "\n"
                                 "QPushButton:pressed {\n"
                                 "    background-color: #e1e9ff;\n"
                                 "}\n"
                                 "\n"
                                 "QStatusBar {\n"
                                 "    background-color: #ffffff;\n"
                                 "    border-top: 1px solid #d9deea;\n"
                                 "}")
        self.actionConnectUsb = QAction(MainWindow)
        self.actionConnectUsb.setObjectName(u"actionConnectUsb")
        self.actionConnectWifi = QAction(MainWindow)
        self.actionConnectWifi.setObjectName(u"actionConnectWifi")
        self.actionImportData = QAction(MainWindow)
        self.actionImportData.setObjectName(u"actionImportData")
        self.actionExportData = QAction(MainWindow)
        self.actionExportData.setObjectName(u"actionExportData")
        self.actionExportReport = QAction(MainWindow)
        self.actionExportReport.setObjectName(u"actionExportReport")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_main = QVBoxLayout(self.centralwidget)
        self.verticalLayout_main.setSpacing(14)
        self.verticalLayout_main.setObjectName(u"verticalLayout_main")
        self.verticalLayout_main.setContentsMargins(18, 18, 18, 18)
        self.chartContainer = QFrame(self.centralwidget)
        self.chartContainer.setObjectName(u"chartContainer")
        self.chartContainer.setFrameShape(QFrame.Shape.NoFrame)
        self.verticalLayout_chartContainer = QVBoxLayout(self.chartContainer)
        self.verticalLayout_chartContainer.setSpacing(12)
        self.verticalLayout_chartContainer.setObjectName(u"verticalLayout_chartContainer")
        self.verticalLayout_chartContainer.setContentsMargins(22, 20, 22, 22)
        self.titleLabel = QLabel(self.chartContainer)
        self.titleLabel.setObjectName(u"titleLabel")
        font = QFont()
        font.setFamilies([u"Segoe UI"])
        font.setPointSize(10)
        font.setBold(True)
        self.titleLabel.setFont(font)
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_chartContainer.addWidget(self.titleLabel)

        self.horizontalLayout_actions = QHBoxLayout()
        self.horizontalLayout_actions.setSpacing(10)
        self.horizontalLayout_actions.setObjectName(u"horizontalLayout_actions")
        self.pushButtonDownloadFromController = QPushButton(self.chartContainer)
        self.pushButtonDownloadFromController.setObjectName(u"pushButtonDownloadFromController")
        self.pushButtonDownloadFromController.setMinimumSize(QSize(230, 42))

        self.horizontalLayout_actions.addWidget(self.pushButtonDownloadFromController)

        self.horizontalSpacer_actions = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_actions.addItem(self.horizontalSpacer_actions)

        self.pushButtonShowGraph = QPushButton(self.chartContainer)
        self.pushButtonShowGraph.setObjectName(u"pushButtonShowGraph")
        self.pushButtonShowGraph.setMinimumSize(QSize(170, 42))

        self.horizontalLayout_actions.addWidget(self.pushButtonShowGraph)


        self.verticalLayout_chartContainer.addLayout(self.horizontalLayout_actions)

        self.chartPlaceholderFrame = QFrame(self.chartContainer)
        self.chartPlaceholderFrame.setObjectName(u"chartPlaceholderFrame")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.chartPlaceholderFrame.sizePolicy().hasHeightForWidth())
        self.chartPlaceholderFrame.setSizePolicy(sizePolicy)
        self.chartPlaceholderFrame.setMinimumSize(QSize(0, 0))
        self.chartPlaceholderFrame.setFrameShape(QFrame.Shape.NoFrame)
        self.verticalLayout_chartPlaceholder = QVBoxLayout(self.chartPlaceholderFrame)
        self.verticalLayout_chartPlaceholder.setObjectName(u"verticalLayout_chartPlaceholder")
        self.verticalLayout_chartPlaceholder.setContentsMargins(14, 14, 14, 14)
        self.matplotlibLayout = QVBoxLayout()
        self.matplotlibLayout.setSpacing(0)
        self.matplotlibLayout.setObjectName(u"matplotlibLayout")
        self.matplotlibLayout.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_chartPlaceholder.addLayout(self.matplotlibLayout)


        self.verticalLayout_chartContainer.addWidget(self.chartPlaceholderFrame)


        self.verticalLayout_main.addWidget(self.chartContainer)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1018, 39))
        self.menuConnection = QMenu(self.menubar)
        self.menuConnection.setObjectName(u"menuConnection")
        self.menuData = QMenu(self.menubar)
        self.menuData.setObjectName(u"menuData")
        self.menuReports = QMenu(self.menubar)
        self.menuReports.setObjectName(u"menuReports")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        self.statusbar.setSizeGripEnabled(True)
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuConnection.menuAction())
        self.menubar.addAction(self.menuData.menuAction())
        self.menubar.addAction(self.menuReports.menuAction())
        self.menuConnection.addAction(self.actionConnectUsb)
        self.menuConnection.addAction(self.actionConnectWifi)
        self.menuData.addAction(self.actionImportData)
        self.menuData.addAction(self.actionExportData)
        self.menuReports.addAction(self.actionExportReport)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"\u041c\u043e\u043d\u0438\u0442\u043e\u0440\u0438\u043d\u0433 \u0438 \u0432\u0438\u0437\u0443\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.actionConnectUsb.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 \u043f\u043e USB", None))
        self.actionConnectWifi.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 \u043f\u043e Wi-Fi", None))
        self.actionImportData.setText(QCoreApplication.translate("MainWindow", u"\u0418\u043c\u043f\u043e\u0440\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.actionExportData.setText(QCoreApplication.translate("MainWindow", u"\u042d\u043a\u0441\u043f\u043e\u0440\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.actionExportReport.setText(QCoreApplication.translate("MainWindow", u"\u042d\u043a\u0441\u043f\u043e\u0440\u0442 \u043e\u0442\u0447\u0451\u0442\u043e\u0432", None))
        self.titleLabel.setText(QCoreApplication.translate("MainWindow", u"\u0413\u0440\u0430\u0444\u0438\u043a \u0434\u0430\u043d\u043d\u044b\u0445", None))
        self.pushButtonDownloadFromController.setText(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0434\u0430\u043d\u043d\u044b\u0435", None))
        self.pushButtonShowGraph.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u044c \u0433\u0440\u0430\u0444\u0438\u043a", None))
        self.menuConnection.setTitle(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435", None))
        self.menuData.setTitle(QCoreApplication.translate("MainWindow", u"\u0414\u0430\u043d\u043d\u044b\u0435", None))
        self.menuReports.setTitle(QCoreApplication.translate("MainWindow", u"\u041e\u0442\u0447\u0451\u0442\u044b", None))
    # retranslateUi

