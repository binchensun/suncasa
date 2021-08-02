import sys, os, copy
# from PyQt5.QtWidgets import QMainWindow, QFileDialog, QApplication, QPushButton, QSlider, QLineEdit, QLabel, \
#    QTextEdit, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QStatusBar, QProgressBar

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import pyqtgraph as pg

from matplotlib.backends.backend_qt5agg import (
    FigureCanvas)
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib import patches, cm
from suncasa.io import ndfits
from astropy.time import Time
import numpy as np
import sunpy
from sunpy import map as smap
from astropy.io import fits
import astropy.units as u
import lmfit
import gstools
import roi_preset_def

# from suncasa.pyGSFIT import gsutils
# from gsutils import ff_emission
import numpy.ma as ma
import warnings

sys.path.append('./')
warnings.filterwarnings("ignore")
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
pg.setConfigOptions(imageAxisOrder='row-major')

fit_param_text = {'Bx100G': 'B [\u00d7100 G]',
                  'log_nnth': 'log(n<sub>nth</sub>) [cm<sup>-3</sup>]',
                  'delta': '\u03b4',
                  'Emin_keV': 'E<sub>min</sub> [keV]',
                  'Emax_MeV': 'E<sub>max</sub> [MeV]',
                  'theta': '\u03b8 [degree]',
                  'log_nth': 'log(n<sub>th</sub>) [cm<sup>-3</sup>]',
                  'T_MK': 'T [MK]',
                  'depth_asec': 'depth [arcsec]',
                  'area_asec2': 'area [arcsec<sup>2</sup>]'}


class App(QMainWindow):

    def __init__(self):
        super().__init__()
        self._createMenuBar()
        self.eoimg_fname = '<Select or enter a valid EOVSA image fits file name>'
        self.eodspec_fname = '<Select or enter a valid EOVSA spectrogram fits file name>'
        self.aiafname = '<Select or enter a valid AIA fits file name>'
        self.eoimg_fitsentry = QLineEdit()
        self.eodspec_fitsentry = QLineEdit()
        self.title = 'pyGSFIT'
        self.left = 0
        self.top = 0
        self.width = 1600
        self.height = 900
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self._main = QWidget()
        self.setCentralWidget(self._main)
        self.fit_method = 'nelder'
        self.fit_params = lmfit.Parameters()
        self.fit_params.add_many(('Bx100G', 2., True, 0.1, 100., None, None),
                                 ('log_nnth', 5., True, 3., 11, None, None),
                                 ('delta', 4., True, 1., 30., None, None),
                                 ('Emin_keV', 10., False, 1., 100., None, None),
                                 ('Emax_MeV', 10., False, 0.05, 100., None, None),
                                 ('theta', 45., True, 0.01, 89.9, None, None),
                                 ('log_nth', 10, True, 4., 13., None, None),
                                 ('T_MK', 1., False, 0.1, 100, None, None),
                                 ('depth_asec', 5., False, 1., 100., None, None))
        self.fit_params_nvarys = 5
        self.fit_kws = {'maxiter': 2000, 'xatol': 0.01, 'fatol': 0.01}
        self.fit_function = gstools.GSCostFunctions.SinglePowerLawMinimizerOneSrc
        self.threadpool = QThreadPool()
        self.has_eovsamap = False
        self.has_stokes = False
        self.has_aiamap = False
        self.has_bkg = False
        self.has_rois = False
        self.fbar = None
        self.data_freq_bound = [1.0, 18.0]  # Initial Frequency Bound of the instrument
        self.tb_spec_bound = [1e3, 5e9]  # Bound of brightness temperature; the lower bound is set to the fit limit
        self.flx_spec_bound = [1e-4, 1e5]  # Bound of flux density; the lower bound is set to the fit limit
        self.fit_freq_bound = [1.0, 18.0]
        self.roi_freq_bound = [1.0, 18.0]
        self.spec_frac_err = 0.1   # fractional error of the intensity (assumed to be due to flux calibration error)
        self.spec_rmsplots = []
        self.spec_dataplots = []
        self.spec_dataplots_tofit = []
        self.roi_grid_size = 2
        self.rois = [[]]
        self.roi_group_idx = 0
        self.nroi_current_group = 0
        self.current_roi_idx = 0
        self.pol_select_idx = 0
        self.plot_tb = True
        # some controls for qlookplot
        self.opencontour = True
        self.clevels = np.array([0.3, 0.7])
        self.calpha = 1.
        # initialize the window
        # self.initUI()
        self.initUItab_explorer()

    def _createMenuBar(self):
        menuBar = self.menuBar()
        fileMenu = QMenu("&File", self)
        menuBar.addMenu(fileMenu)
        # Creating menus using a title
        editMenu = menuBar.addMenu("&Edit")
        helpMenu = menuBar.addMenu("&Help")

    #    def initUI(self):
    #
    #        self.statusBar = QStatusBar()
    #        self.setStatusBar(self.statusBar)
    #        self.progressBar = QProgressBar()
    #        self.progressBar.setGeometry(10, 10, 200, 15)

    #        layout = QVBoxLayout()
    #        # Initialize tab screen
    #        self.tabs = QTabWidget()
    #        tab_explorer = QWidget()
    #        tab_fit = QWidget()
    #        tab_analyzer = QWidget()

    #        # Add tabs
    #        self.tabs.addTab(tab_explorer, "Explorer")
    #        # self.tabs.addTab(tab_fit, "Fit")
    #        self.tabs.addTab(tab_analyzer, "Analyzer")

    #        # Each tab's user interface is complex, so this splits them into separate functions.
    #        self.initUItab_explorer()
    #        # self.initUItab_fit()
    #        self.initUItab_analyzer()
    #
    #        # self.tabs.currentChanged.connect(self.tabChanged)

    #        # Add tabs to widget
    #        layout.addWidget(self.tabs)
    #        self._main.setLayout(layout)
    #
    #        self.show()

    # Explorer Tab User Interface
    #
    def initUItab_explorer(self):
        # Create main layout (a Vertical Layout)
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.progressBar = QProgressBar()
        self.progressBar.setGeometry(10, 10, 200, 15)
        main_layout = QHBoxLayout()

        # Creat Data Display and Fit Tab
        data_layout = QVBoxLayout()
        fit_layout = QVBoxLayout()

        ###### The Following is for datalayout ######
        # Upper box of the data layout has two hboxes: top box and quicklook plot box
        data_layout_upperbox = QVBoxLayout()
        # Top of the upper box of the data layout is for file selection and fits header display
        file_selection_box = QHBoxLayout()

        # EOVSA Image FITS Filename entry
        eoimg_selection_box = QHBoxLayout()
        file_selection_box.addLayout(eoimg_selection_box)
        # Create Browse button
        eoimg_selection_button = QPushButton("Load EOVSA Image")
        eoimg_selection_button.clicked.connect(self.eoimg_file_select)
        eoimg_selection_box.addWidget(eoimg_selection_button)
        # Create LineEdit widget for FITS filename
        self.eoimg_fitsentry.resize(8 * len(self.eoimg_fname), 20)
        eoimg_selection_box.addWidget(self.eoimg_fitsentry)

        # EOVSA Spectrogram FITS Filename entry
        eodspec_selection_box = QHBoxLayout()
        file_selection_box.addLayout(eodspec_selection_box)
        # Create Browse button
        eodspec_selection_button = QPushButton("Load EOVSA Spectrogram")
        eodspec_selection_button.clicked.connect(self.eodspec_file_select)
        eodspec_selection_box.addWidget(eodspec_selection_button)
        # Create LineEdit widget for FITS filename
        self.eodspec_fitsentry.resize(8 * len(self.eoimg_fname), 20)
        eodspec_selection_box.addWidget(self.eodspec_fitsentry)

        # AIA FITS Filename entry
        aia_selection_box = QHBoxLayout()
        file_selection_box.addLayout(aia_selection_box)
        # Create Browse button
        aia_selection_button = QPushButton("Load AIA")
        aia_selection_button.clicked.connect(self.aiafile_select)
        aia_selection_box.addWidget(aia_selection_button)
        # Create LineEdit widget for AIA FITS file
        self.aiaimg_fitsentry = QLineEdit()
        self.aiaimg_fitsentry.resize(8 * len(self.eoimg_fname), 20)
        aia_selection_box.addWidget(self.aiaimg_fitsentry)

        # Add top box of the upper box in data layout
        data_layout_upperbox.addLayout(file_selection_box)

        # Create label and TextEdit widget for FITS header information
        # fitsinfobox = QVBoxLayout()
        # topbox.addLayout(fitsinfobox)
        # self.infoEdit = QTextEdit()
        # self.infoEdit.setReadOnly(True)
        # self.infoEdit.setMinimumHeight(100)
        # self.infoEdit.setMaximumHeight(400)
        # self.infoEdit.setMinimumWidth(300)
        # self.infoEdit.setMaximumWidth(500)
        # fitsinfobox.addWidget(QLabel("FITS Information"))
        # fitsinfobox.addWidget(self.infoEdit)

        # Bottom of the upper box in data layout: quick look plotting area
        qlookarea = QVBoxLayout()
        self.qlookcanvas = FigureCanvas(Figure(figsize=(8, 4)))
        self.qlooktoolbar = NavigationToolbar(self.qlookcanvas, self)
        qlookarea.addWidget(self.qlooktoolbar)
        qlookarea.addWidget(self.qlookcanvas)
        # self.qlook_axs = self.qlookcanvas.figure.subplots(nrows=1, ncols=4)
        gs = gridspec.GridSpec(ncols=2, nrows=1, width_ratios=[1, 3], left=0.08, right=0.95, wspace=0.2)
        gs1 = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=gs[0], wspace=0)
        gs2 = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=gs[1], wspace=0.05)
        self.qlook_axs = []
        self.qlook_axs.append(self.qlookcanvas.figure.add_subplot(gs1[0]))
        self.qlook_axs.append(self.qlookcanvas.figure.add_subplot(gs2[0]))
        self.qlook_axs.append(self.qlookcanvas.figure.add_subplot(gs2[1], sharex=self.qlook_axs[-1],
                                                                  sharey=self.qlook_axs[-1]))
        self.qlook_axs.append(self.qlookcanvas.figure.add_subplot(gs2[2], sharex=self.qlook_axs[-1],
                                                                  sharey=self.qlook_axs[-1]))

        data_layout_upperbox.addLayout(qlookarea)
        data_layout.addLayout(data_layout_upperbox)
        # data_layout.setRowStretch(0, 1.)

        # lowerbox
        data_layout_lowerbox = QGridLayout()  # lower box has two hboxes: left for multi-panel display and right for spectrum
        pgimgbox = QVBoxLayout()  # left box of lower box for pg ImageView and associated buttons

        # Status box
        pg_img_status_box = QVBoxLayout()
        self.pg_img_mouse_pos_widget = QLabel("")
        pg_img_status_box.addWidget(self.pg_img_mouse_pos_widget)
        self.pg_img_roi_info_widget = QLabel("")
        #pg_img_status_box.addWidget(self.pg_img_roi_info_widget)
        self.pg_img_bkg_roi_info_widget = QLabel("")
        pg_img_status_box.addWidget(self.pg_img_bkg_roi_info_widget)

        # Add plotting area for multi-panel EOVSA images
        self.pg_img_canvas = pg.ImageView(name='EOVSA Explorer')

        pgimgbox.addWidget(self.pg_img_canvas)
        # pgimgbox.addLayout(pgbuttonbox)
        pgimgbox.addLayout(pg_img_status_box)
        data_layout_lowerbox.addLayout(pgimgbox, 0, 0)
        data_layout_lowerbox.setColumnStretch(0, 1.7)
        self.pg_img_canvas.sigTimeChanged.connect(self.update_fbar)

        # right box for spectral plots
        specplotarea = QVBoxLayout()
        # add a toggle between Tb and flux density
        specplotmode_box = QHBoxLayout()
        self.plot_tb_button = QRadioButton("Plot Brightness Temperature or Flux Density")
        self.plot_tb_button.setChecked(True)
        self.plot_tb_button.toggled.connect(self.tb_flx_btnstate) ## todo
        specplotmode_box.addWidget(self.plot_tb_button)
        specplotarea.addLayout(specplotmode_box)

        # self.speccanvas = FigureCanvas(Figure(figsize=(4, 6)))
        self.speccanvas = pg.PlotWidget()
        # self.spectoolbar = NavigationToolbar(self.speccanvas, self)
        # specplotarea.addWidget(self.spectoolbar)
        specplotarea.addWidget(self.speccanvas)
        # self.spec_axs = self.speccanvas.figure.subplots(nrows=1, ncols=1)
        data_layout_lowerbox.addLayout(specplotarea, 0, 1)
        data_layout_lowerbox.setColumnStretch(1, 1)

        data_layout.addLayout(data_layout_lowerbox)
        main_layout.addLayout(data_layout)

        ####### The following is for fit layout on the right of the main window ######
        # Group 1: ROI Definition Group
        roi_definition_group = QGroupBox("ROI Definition")
        roi_definition_group_box = QVBoxLayout()
        roi_definition_group.setLayout(roi_definition_group_box)
        roi_button_box = QHBoxLayout()

        # ADD ROI Region for Obtaining Spectra
        self.add_roi_button = QPushButton("Add New ROI")
        self.add_roi_button.setStyleSheet("background-color : lightgrey")
        roi_button_box.addWidget(self.add_roi_button)
        self.add_roi_button.clicked.connect(self.add_new_roi)

        self.add_to_roigroup_button = QToolButton(self)
        self.add_to_roigroup_button.setText("0")
        self.add_to_roigroup_button.setPopupMode(QToolButton.MenuButtonPopup)
        self.add_to_roigroup_button.setMenu(QMenu(self.add_to_roigroup_button))
        self.add_to_roigroup_widget = QListWidget()
        self.add_to_roigroup_widget.addItems(['0', '1', '2'])  ##todo
        self.add_to_roigroup_widget.itemClicked.connect(self.add_to_roigroup_selection)
        action = QWidgetAction(self.add_to_roigroup_button)
        action.setDefaultWidget(self.add_to_roigroup_widget)
        self.add_to_roigroup_button.menu().addAction(action)
        roi_button_box.addWidget(QLabel("to Group"))
        roi_button_box.addWidget(self.add_to_roigroup_button)



        self.roi_freq_lowbound_selector = QDoubleSpinBox()
        self.roi_freq_lowbound_selector.setDecimals(1)
        self.roi_freq_lowbound_selector.setRange(self.data_freq_bound[0], self.data_freq_bound[1])
        self.roi_freq_lowbound_selector.setSingleStep(0.1)
        self.roi_freq_lowbound_selector.setValue(self.data_freq_bound[0])
        self.roi_freq_lowbound_selector.valueChanged.connect(self.roi_freq_lowbound_valuechange)
        roi_button_box.addWidget(QLabel("Min Freq (GHz)"))
        roi_button_box.addWidget(self.roi_freq_lowbound_selector)

        self.roi_freq_hibound_selector = QDoubleSpinBox()
        self.roi_freq_hibound_selector.setDecimals(1)
        self.roi_freq_hibound_selector.setRange(self.data_freq_bound[0], self.data_freq_bound[1])
        self.roi_freq_hibound_selector.setSingleStep(0.1)
        self.roi_freq_hibound_selector.setValue(self.data_freq_bound[1])
        self.roi_freq_hibound_selector.valueChanged.connect(self.roi_freq_hibound_valuechange)
        roi_button_box.addWidget(QLabel("Max Freq (GHz)"))
        roi_button_box.addWidget(self.roi_freq_hibound_selector)

        # ADD presets selection box
        self.roi_selection_presets_widget = QComboBox()
        self.roi_selection_presets_widget.addItems(
            ["Presets","Img_Inte_ROIs"])
        self.roi_selection_presets_widget.setCurrentIndex(0)
        self.roi_selection_presets_widget.currentIndexChanged.connect(self.presets_selector)
        roi_button_box.addWidget(self.roi_selection_presets_widget)

        roi_definition_group_box.addLayout(roi_button_box)

        roi_grid_box = QHBoxLayout()
        ## todo: add this button later
        self.add_roi_grid_button = QPushButton("Add ROI Grid")
        self.add_roi_grid_button.setStyleSheet("background-color : lightgrey")
        roi_grid_box.addWidget(self.add_roi_grid_button)

        self.roi_grid_size_selector = QSpinBox()
        self.roi_grid_size_selector.setRange(1, 1000)
        self.roi_grid_size_selector.setSingleStep(1)
        self.roi_grid_size_selector.setValue(2)
        self.roi_grid_size_selector.valueChanged.connect(self.roi_grid_size_valuechange)
        roi_grid_box.addWidget(QLabel("Grid Size (pix)"))
        roi_grid_box.addWidget(self.roi_grid_size_selector)
        roi_definition_group_box.addLayout(roi_grid_box)

        fit_layout.addWidget(roi_definition_group)

        # Group 2: ROI Selection Group
        roi_selection_group = QGroupBox("ROI Selection")
        roi_selection_group_box = QVBoxLayout()
        roi_selection_group.setLayout(roi_selection_group_box)

        roi_selection_button_box = QHBoxLayout()

        # ROI GROUP Selection Button
        self.roigroup_selection_button = QToolButton(self)
        self.roigroup_selection_button.setText('0')
        self.roigroup_selection_button.setPopupMode(QToolButton.MenuButtonPopup)
        self.roigroup_selection_button.setMenu(QMenu(self.roigroup_selection_button))
        self.roigroup_selection_widget = QListWidget()
        self.roigroup_selection_widget.addItems(['0', '1', '2'])  ##todo
        self.roigroup_selection_widget.itemClicked.connect(self.roigroup_selection)
        action = QWidgetAction(self.roigroup_selection_button)
        action.setDefaultWidget(self.roigroup_selection_widget)
        self.roigroup_selection_button.menu().addAction(action)
        roi_selection_button_box.addWidget(QLabel("Select ROI Group"))
        roi_selection_button_box.addWidget(self.roigroup_selection_button)

        # ROI Selection Button
        self.roi_selection_button = QToolButton(self)
        self.roi_selection_button.setText(str(self.current_roi_idx))
        self.roi_selection_button.setPopupMode(QToolButton.MenuButtonPopup)
        self.roi_selection_button.setMenu(QMenu(self.roi_selection_button))
        self.roi_selection_widget = QListWidget()
        self.roi_selection_widget.addItems([str(i) for i in range(self.nroi_current_group)])
        self.roi_selection_widget.itemClicked.connect(self.roi_selection_action)
        action = QWidgetAction(self.roi_selection_button)
        action.setDefaultWidget(self.roi_selection_widget)
        self.roi_selection_button.menu().addAction(action)
        roi_selection_button_box.addWidget(QLabel("Select ROI"))
        roi_selection_button_box.addWidget(self.roi_selection_button)
        # Slider for ROI selection
        # self.roi_select_slider = QSlider(Qt.Horizontal)
        # self.roi_select_slider.setMinimum(0)
        # self.roi_select_slider.setMaximum(1)
        # self.roi_select_slider.setSingleStep(1)
        # self.roi_select_slider.setTickPosition(QSlider.TicksBelow)
        # self.roi_select_slider.setTickInterval(1)
        # self.roi_select_slider.valueChanged.connect(self.roi_slider_valuechange)
        # roi_select_box.addWidget(QLabel("ROI ID #"))
        # roi_select_box.addWidget(self.roi_select_slider)
        roi_selection_group_box.addLayout(roi_selection_button_box)

        # Text Box for ROI information
        self.roi_info = QTextEdit()
        self.roi_info.setReadOnly(True)
        self.roi_info.setMinimumHeight(50)
        self.roi_info.setMaximumHeight(100)
        # self.roi_info.setMinimumWidth(200)
        # self.roi_info.setMaximumWidth(200)
        # roi_group_box.addWidget(QLabel("ROI Information"))
        roi_selection_group_box.addWidget(self.roi_info)

        ## Add buttons for doing spectral fit
        fit_button_box = QHBoxLayout()
        # Background selection button
        # self.bkg_selection_button = QPushButton("Select Background")
        # self.bkg_selection_button.setStyleSheet("background-color : lightgrey")
        # self.bkg_selection_button.setCheckable(True)
        # self.bkg_selection_button.clicked.connect(self.bkg_rgn_select)
        # fit_button_box.addWidget(self.bkg_selection_button)

        # Do Fit Button
        do_spec_fit_button = QPushButton("Fit Selected ROI")
        do_spec_fit_button.clicked.connect(self.do_spec_fit)
        fit_button_box.addWidget(do_spec_fit_button)

        # Add fit button box to roi group
        roi_selection_group_box.addLayout(fit_button_box)

        fit_layout.addWidget(roi_selection_group)

        ####### Group 2: Fit Settings Group
        fit_setting_group = QGroupBox("Fit Settings")
        fit_setting_box = QVBoxLayout()
        fit_setting_group.setLayout(fit_setting_box)
        spec_adjust_box = QHBoxLayout()

        # Group 2: Lower Frequency Bounds for fit
        self.freq_lowbound_selector = QDoubleSpinBox()
        self.freq_lowbound_selector.setDecimals(1)
        self.freq_lowbound_selector.setRange(self.data_freq_bound[0], self.data_freq_bound[1])
        self.freq_lowbound_selector.setSingleStep(0.1)
        self.freq_lowbound_selector.setValue(self.data_freq_bound[0])
        self.freq_lowbound_selector.valueChanged.connect(self.freq_lowbound_valuechange)
        spec_adjust_box.addWidget(QLabel("Min Freq (GHz)"))
        spec_adjust_box.addWidget(self.freq_lowbound_selector)

        # Group 2: Upper Frequency Bounds for fit
        self.freq_hibound_selector = QDoubleSpinBox()
        self.freq_hibound_selector.setDecimals(1)
        self.freq_hibound_selector.setRange(self.data_freq_bound[0], self.data_freq_bound[1])
        self.freq_hibound_selector.setSingleStep(0.1)
        self.freq_hibound_selector.setValue(self.data_freq_bound[1])
        self.freq_hibound_selector.valueChanged.connect(self.freq_hibound_valuechange)
        spec_adjust_box.addWidget(QLabel("Max Freq (GHz)"))
        spec_adjust_box.addWidget(self.freq_hibound_selector)

        # Group 2: Fractional intensity error for fit
        self.spec_frac_err_selector = QDoubleSpinBox()
        self.spec_frac_err_selector.setDecimals(2)
        self.spec_frac_err_selector.setRange(0.0, 1.0)
        self.spec_frac_err_selector.setSingleStep(0.02)
        self.spec_frac_err_selector.setValue(self.spec_frac_err)
        self.spec_frac_err_selector.valueChanged.connect(self.spec_frac_err_valuechange)
        spec_adjust_box.addWidget(QLabel("Frac. Intensity Error"))
        spec_adjust_box.addWidget(self.spec_frac_err_selector)

        fit_setting_box.addLayout(spec_adjust_box)

        # Group 2: Fit Method
        self.fit_method_box = QHBoxLayout()
        self.fit_method_selector_widget = QComboBox()
        self.fit_method_selector_widget.addItems(["nelder", "basinhopping", "differential_evolution"])
        self.fit_method_selector_widget.currentIndexChanged.connect(self.fit_method_selector)
        self.fit_method_box.addWidget(QLabel("Fit Method"))
        self.fit_method_box.addWidget(self.fit_method_selector_widget)

        # Group 2: Fit Method Dependent Keywords
        self.fit_kws_box = QHBoxLayout()
        self.update_fit_kws_widgets()

        # Group 2: Electron Function
        ele_function_box = QHBoxLayout()
        self.ele_function_selector_widget = QComboBox()
        self.ele_function_selector_widget.addItems(
            ["powerlaw", "double_Powerlaw", "thermal f-f + gyrores", "thermal f-f"])
        self.ele_function_selector_widget.currentIndexChanged.connect(self.ele_function_selector)
        ele_function_box.addWidget(QLabel("Electron Dist. Function"))
        ele_function_box.addWidget(self.ele_function_selector_widget)

        fit_setting_box.addLayout(self.fit_method_box)
        fit_setting_box.addLayout(self.fit_kws_box)
        fit_setting_box.addLayout(ele_function_box)
        fit_layout.addWidget(fit_setting_group)

        ##### Group 3: Fit Parameters Group
        fit_param_group = QGroupBox("Fit Parameters")
        self.fit_param_box = QGridLayout()
        fit_param_group.setLayout(self.fit_param_box)
        self.update_fit_param_widgets()

        fit_layout.addWidget(fit_param_group)
        main_layout.addLayout(fit_layout)
        # data_layout.setRowStretch(1, 1.2)
        # self.tabs.widget(0).setLayout(main_layout)
        self._main.setLayout(main_layout)
        self.show()

    # Fit Tab User Interface
    #
    # def initUItab_fit(self):
    #    # Create main layout (a Vertical Layout)
    #    mainlayout = QVBoxLayout()
    #    mainlayout.addWidget(QLabel("This is the tab for analyzing fit results"))
    #    self.tabs.widget(1).setLayout(mainlayout)

    # Analyzer Tab User Interface
    #
    def initUItab_analyzer(self):
        # Create main layout (a Vertical Layout)
        mainlayout = QVBoxLayout()
        mainlayout.addWidget(QLabel("This is the tab for analyzing fit results"))
        self.tabs.widget(1).setLayout(mainlayout)

    def eoimg_file_select(self):
        """ Handle Browse button for EOVSA FITS file"""
        # self.fname = QFileDialog.getExistingDirectory(self, 'Select FITS File', './', QFileDialog.ShowDirsOnly)
        self.eoimg_fname, _file_filter = QFileDialog.getOpenFileName(self, 'Select EOVSA Spectral Image FITS File',
                                                                     './', 'FITS Images (*.fits *.fit *.ft *.fts)')
        #self.fname = 'EOVSA_20210507T190205.000000.outim.image.allbd.fits'
        self.eoimg_fitsentry.setText(self.eoimg_fname)
        self.eoimg_file_select_return()

    def eoimg_file_select_return(self):
        ''' Called when the FITS filename LineEdit widget gets a carriage-return.
            Trys to read FITS header and return header info (no data read at this time)
        '''
        self.eoimg_fname = self.eoimg_fitsentry.text()
        self.eoimg_fitsdata = None
        self.has_eovsamap = False

        # Clean up all existing plots
        for ax in self.qlook_axs:
            ax.cla()
        self.pg_img_canvas.clear()
        if self.has_bkg:
            self.pg_img_canvas.removeItem(self.bkg_roi)
            self.has_bkg = False
        if self.has_rois:
            for roi_group in self.rois:
                for roi in roi_group:
                    self.pg_img_canvas.removeItem(roi)
            self.rois = [[]]
            self.has_rois = False

        try:
            meta, data = ndfits.read(self.eoimg_fname)
            if meta['naxis'] < 3:
                print('Input fits file must have at least 3 dimensions. Abort..')
            elif meta['naxis'] == 3:
                print('Input fits file does not have stokes axis. Assume Stokes I.')
                data = np.expand_dims(data, axis=0)
                self.pol_axis = 0
                self.pol_names = ['I']
                self.has_stokes = False
            elif meta['naxis'] == 4:
                print('Input fits file has stokes axis, located at index {0:d} of the data cube'.
                      format(meta['pol_axis']))
                self.has_stokes = True
                self.pol_axis = meta['pol_axis']
                self.pol_names = meta['pol_names']
            self.meta = meta
            self.data = data
            self.cfreqs = meta['ref_cfreqs'] / 1e9  # convert to GHz
            self.freqdelts = meta['ref_freqdelts'] / 1e9  # convert to GHz
            self.freq_dist = lambda fq: (fq - self.cfreqs[0]) / (self.cfreqs[-1] - self.cfreqs[0])
            self.x0, self.x1 = (np.array([1, meta['nx']]) - meta['header']['CRPIX1']) * meta['header']['CDELT1'] + \
                               meta['header']['CRVAL1']
            self.y0, self.y1 = (np.array([1, meta['ny']]) - meta['header']['CRPIX2']) * meta['header']['CDELT2'] + \
                               meta['header']['CRVAL2']
            self.mapx, self.mapy = np.linspace(self.x0, self.x1, meta['nx']), np.linspace(self.y0, self.y1, meta['ny'])
            self.has_eovsamap = True
            # self.infoEdit.setPlainText(repr(rheader))
        except:
            self.statusBar.showMessage('Filename is not a valid FITS file', 2000)
            self.eoimg_fname = '<Select or enter a valid fits filename>'
            self.eoimg_fitsentry.setText(self.eoimg_fname)
            # self.infoEdit.setPlainText('')

        self.plot_qlookmap()
        self.init_pgspecplot()
        self.plot_pg_eovsamap()

    def eodspec_file_select(self):
        """ Handle Browse button for EOVSA FITS file"""
        # self.fname = QFileDialog.getExistingDirectory(self, 'Select FITS File', './', QFileDialog.ShowDirsOnly)
        self.eodspec_fname, _file_filter = QFileDialog.getOpenFileName(self, 'Select EOVSA Dynamic Spectrum FITS File',
                                                                     './', 'FITS Images (*.fits *.fit *.ft *.fts)')
        self.eodspec_fitsentry.setText(self.eodspec_fname)
        self.eodspec_file_select_return()

    def eodspec_file_select_return(self):
        ## todo: complete the action
        print('To be added')
        self.eodspec_fname = '<Select or enter a valid fits filename>'
        self.eodspec_fitsentry.setText(self.eodspec_fname)

    def aiafile_select(self):
        """ Handle Browse button for AIA FITS file """
        self.aiafname, _file_filter = QFileDialog.getOpenFileName(self, 'Select AIA FITS File to open', './',
                                                                  "FITS Images (*.fits *.fit *.ft)")
        self.aiaimg_fitsentry.setText(self.aiafname)
        self.aiafile_select_return()

    def aiafile_select_return(self):
        ''' Called when the FITS filename LineEdit widget gets a carriage-return.
            Trys to read FITS header and return header info (no data read at this time)
        '''
        self.aiafname = self.aiaimg_fitsentry.text()
        self.eoimg_fitsdata = None
        try:
            hdu = fits.open(self.aiafname)
            # self.infoEdit.setPlainText(repr(hdu[1].header))
        except:
            self.statusBar.showMessage('Filename is not a valid FITS file', 2000)
            self.aiafname = '<Select or enter a valid fits filename>'
            # self.aiafitsentry.setText(self.fname)
            # self.infoEdit.setPlainText('')

        self.plot_qlookmap()

    def init_pgspecplot(self):
        """ Initial Spectral Plot if no data has been loaded """
        xticksv = list(range(0, 4))
        self.xticks = []
        xticksv_minor = []
        for v in xticksv:
            vp = 10 ** v
            xticksv_minor += list(np.arange(2 * vp, 10 * vp, 1 * vp))
            self.xticks.append((v, '{:.0f}'.format(vp)))
        self.xticks_minor = []
        for v in xticksv_minor:
            self.xticks_minor.append((np.log10(v), ''))

        if self.plot_tb:
            yticksv = list(range(1, 15))
        else:
            yticksv = list(range(-3, 3))
        yticksv_minor = []
        for v in yticksv:
            vp = 10 ** v
            yticksv_minor += list(np.arange(2 * vp, 10 * vp, 1 * vp))
        self.yticks_minor = []
        for v in yticksv_minor:
            self.yticks_minor.append((np.log10(v), ''))
        self.yticks = []
        if self.plot_tb:
            for v in yticksv:
                if v >= 6:
                    self.yticks.append([v, r'{:.0f}'.format(10 ** v / 1e6)])
                if v == 1:
                    self.yticks.append([v, r'{:.5f}'.format(10 ** v / 1e6)])
                elif v == 2:
                    self.yticks.append([v, r'{:.4f}'.format(10 ** v / 1e6)])
                elif v == 3:
                    self.yticks.append([v, r'{:.3f}'.format(10 ** v / 1e6)])
                elif v == 4:
                    self.yticks.append([v, r'{:.2f}'.format(10 ** v / 1e6)])
                elif v == 5:
                    self.yticks.append([v, r'{:.1f}'.format(10 ** v / 1e6)])
                else:
                    self.yticks.append([v, r'{:.0f}'.format(10 ** v / 1e6)])
        else:
            for v in yticksv:
                if v >= 0:
                    self.yticks.append([v, r'{:.0f}'.format(10 ** v)])
                if v == -3:
                    self.yticks.append([v, r'{:.3f}'.format(10 ** v)])
                if v == -2:
                    self.yticks.append([v, r'{:.2f}'.format(10 ** v)])
                if v == -1:
                    self.yticks.append([v, r'{:.1f}'.format(10 ** v)])

        self.update_pgspec()

    def plot_qlookmap(self):
        """Quicklook plot in the upper box using matplotlib.pyplot and sunpy.map"""
        from suncasa.utils import plot_mapX as pmX
        # Plot a quicklook map
        # self.qlook_ax.clear()
        ax0 = self.qlook_axs[0]

        if self.has_eovsamap:
            nspw = self.meta['nfreq']
            bds = np.linspace(0, nspw, 5)[1:4].astype(np.int)
            eodate = Time(self.meta['refmap'].date.mjd + self.meta['refmap'].exposure_time.value / 2. / 24 / 3600,
                          format='mjd')
            eotimestr = eodate.isot[:-4]
            rsun_obs = sunpy.coordinates.sun.angular_radius(eodate).value
            solar_limb = patches.Circle((0, 0), radius=rsun_obs, fill=False, color='k', lw=1, linestyle=':')
            ax0.add_patch(solar_limb)
            rect = patches.Rectangle((self.x0, self.y0), self.x1 - self.x0, self.y1 - self.y0,
                                     color='k', alpha=0.7, lw=1, fill=False)
            ax0.add_patch(rect)
            icmap = plt.get_cmap('RdYlBu')

            # now plot 3 panels of EOVSA images
            # plot the images
            eocmap = plt.get_cmap('viridis')
            for n, bd in enumerate(bds):
                ax = self.qlook_axs[n + 1]
                cfreq = self.cfreqs[bd]
                eomap_ = smap.Map(self.data[self.pol_select_idx, bd], self.meta['header'])
                eomap = pmX.Sunmap(eomap_)
                eomap.imshow(axes=ax, cmap=eocmap)
                eomap.draw_grid(axes=ax)
                eomap.draw_limb(axes=ax)
                # ax.set_xlim()
                # ax.set_ylim()
                ax.set_xlabel('Solar X [arcsec]')
                ax.set_title('')
                if n == 0:
                    ax.tick_params(bottom=True, top=True, left=True, right=True, labelleft=True, labelbottom=True)
                    ax.set_ylabel('Solar Y [arcsec]')
                    ax.set_title('EOVSA at {}'.format(eotimestr))
                else:
                    ax.tick_params(bottom=True, top=True, left=True, right=True, labelleft=False, labelbottom=True)
                    ax.set_ylabel('')
                ax.text(0.01, 0.98, '{0:.1f} GHz'.format(cfreq), ha='left', va='top',
                        fontsize=10, color='w', transform=ax.transAxes)
                ax.set_aspect('equal')
        else:
            self.statusBar.showMessage('EOVSA FITS file does not exist', 2000)
            self.eoimg_fname = '<Select or enter a valid fits filename>'
            self.eoimg_fitsentry.setText(self.eoimg_fname)
            # self.infoEdit.setPlainText('')
            self.has_eovsamap = False

        if os.path.exists(self.aiafname):
            try:
                aiacmap = plt.get_cmap('gray_r')
                aiamap = smap.Map(self.aiafname)
                aiamap.plot(axes=ax0, cmap=aiacmap)
                self.has_aiamap = True
            except:
                self.statusBar.showMessage('Something is wrong with the provided AIA FITS file', 2000)
        else:
            self.statusBar.showMessage('AIA FITS file does not exist', 2000)
            self.aiafname = '<Select or enter a valid fits filename>'
            self.aiaimg_fitsentry.setText(self.aiafname)
            # self.infoEdit.setPlainText('')
            self.has_aiamap = False
        cts = []
        if self.has_aiamap:
            aiamap.plot(axes=ax0, cmap=aiacmap)
        if self.has_eovsamap:
            for s, sp in enumerate(self.cfreqs):
                data = self.data[self.pol_select_idx, s, ...]
                clvls = self.clevels * np.nanmax(data)
                rcmap = [icmap(self.freq_dist(self.cfreqs[s]))] * len(clvls)
                if self.opencontour:
                    cts.append(ax0.contour(self.mapx, self.mapy, data, levels=clvls,
                                           colors=rcmap,
                                           alpha=self.calpha))
                else:
                    cts.append(ax0.contourf(self.mapx, self.mapy, data, levels=clvls,
                                            colors=rcmap,
                                            alpha=self.calpha))

        ax0.set_xlim([-1200, 1200])
        ax0.set_ylim([-1200, 1200])
        ax0.set_xlabel('Solar X [arcsec]')
        ax0.set_ylabel('Solar Y [arcsec]')
        # ax0.set_title('')
        ax0.set_aspect('equal')
        # self.qlookcanvas.figure.subplots_adjust(left=0.05, right=0.95,
        #                                        bottom=0.06, top=0.95,
        #                                        hspace=0.1, wspace=0.1)
        self.qlookcanvas.draw()

    def plot_pg_eovsamap(self, cmap='viridis', ncolorstop=6):
        """This is to plot the eovsamap with the pyqtgraph's ImageView Widget"""
        from matplotlib import cm
        if self.has_eovsamap:
            # plot the images
            # need to invert the y axis to put the origin to the lower left (tried invertY but labels are screwed up)
            self.pgdata = self.data[self.pol_select_idx, :, ::-1, :].reshape(
                (self.meta['nfreq'], self.meta['ny'], self.meta['nx']))
            self.pg_img_canvas.setImage(self.pgdata, xvals=self.cfreqs)
            # self.pg_img_canvas.setImage(self.data[self.pol_select_idx], xvals=self.cfreqs)
            vbox = self.pg_img_canvas.getView()
            vbox.invertY(True)
            mpl_cmap = cm.get_cmap(cmap, ncolorstop)
            mpl_colors = mpl_cmap(np.linspace(0, 1, ncolorstop)) * 255
            colors = []
            for s in range(ncolorstop):
                colors.append((int(mpl_colors[s, 0]), int(mpl_colors[s, 1]), int(mpl_colors[s, 2])))

            cmap = pg.ColorMap(pos=np.linspace(0.0, 1.0, ncolorstop), color=colors)
            self.pg_img_canvas.setColorMap(cmap)
            self.pg_freq_current = self.pg_img_canvas.timeLine.getXPos()
            self.pg_freq_idx = np.argmin(np.abs(self.cfreqs - self.pg_freq_current))
            self.pg_img_canvas.getImageItem().hoverEvent = self.pg_map_hover_event

            # define the initial background ROI region
            if not self.has_bkg:
                self.bkg_roi = pg.RectROI([0, self.meta['ny'] - 40], [40, 40], pen='w')
                self.pg_img_canvas.addItem(self.bkg_roi)
                self.has_bkg = True
                bkg_roi_label = pg.TextItem("Background", anchor=(0, 0), color='w')
                bkg_roi_label.setParentItem(self.bkg_roi)
                self.bkg_rgn_update()
                self.bkg_roi.sigRegionChanged.connect(self.bkg_rgn_update)

    def pg_map_hover_event(self, event):
        """Show the position, pixel, and value under the mouse cursor.
        """
        vbox = self.pg_img_canvas.getView()
        if event.isExit():
            # self.pg_img_hover_label.setText("")
            self.pg_img_mouse_pos_widget.setText("")
            return

        pos = event.pos()
        i, j = pos.y(), pos.x()
        i = int(np.clip(i, 0, self.meta['ny'] - 1))
        j = int(np.clip(j, 0, self.meta['nx'] - 1))
        self.pg_freq_current = self.pg_img_canvas.timeLine.getXPos()
        self.pg_freq_idx = np.argmin(np.abs(self.cfreqs - self.pg_freq_current))
        val = self.pgdata[self.pg_freq_idx, i, j]
        # ppos = self.pg_img_canvas.getImageItem().mapToParent(pos)
        solx, soly = self.mapx[j], self.mapy[::-1][i]
        text_to_display = '[Cursor] x: {0:6.1f}", y: {1:6.1f}", freq: {3:4.1f} GHz, ' \
                          'T<sub>B</sub>={4:6.2f} MK'.format(solx, soly, self.pg_freq_idx,
                                                            self.pg_freq_current, val / 1e6)
        self.pg_img_mouse_pos_widget.setText(text_to_display)
        # print(text_to_display)
        # self.pg_img_hover_label.setText(text_to_display, color='w')

    def update_fitmask(self):
        # update fit mask and the values for currently selected roi group
        if self.has_rois:
            for roi in self.rois[self.roi_group_idx]:
                # define error in spectrum
                if self.plot_tb:
                    spec = roi.tb_max
                    spec_bound = self.tb_spec_bound
                    spec_rms = self.bkg_roi.tb_rms
                else:
                    spec = roi.total_flux
                    spec_bound = self.flx_spec_bound
                    spec_rms = gstools.sfu2tb(roi.freqghz * 1e9 * u.Hz, self.bkg_roi.tb_rms * u.K,
                                              area=roi.total_area * u.arcsec ** 2, reverse=True).value
                # add fractional err in quadrature
                spec_err = np.sqrt(spec_rms ** 2. + (self.spec_frac_err * spec) ** 2.)

                spec_tofit0 = ma.masked_less_equal(spec, spec_bound[0])
                freqghz_tofit0 = ma.masked_outside(self.cfreqs, self.fit_freq_bound[0], self.fit_freq_bound[1])
                roi.mask_tofit = mask_tofit = np.logical_or(np.logical_or(freqghz_tofit0.mask, spec_tofit0.mask),
                                                            roi.freq_mask)
                roi.freqghz_tofit = ma.masked_array(self.cfreqs, mask_tofit)
                roi.spec_tofit = ma.masked_array(spec, mask_tofit)
                roi.tb_max_tofit = ma.masked_array(roi.tb_max, mask_tofit)
                roi.total_flux_tofit = ma.masked_array(roi.total_flux, mask_tofit)

                if self.has_bkg:
                    roi.spec_err_tofit = ma.masked_array(spec_err, roi.mask_tofit)
                    roi.tb_rms_tofit = ma.masked_array(self.bkg_roi.tb_rms, roi.mask_tofit)


    def update_pgspec(self):
        """Use Pyqtgraph's PlotWidget for the spectral plot"""
        self.speccanvas.clear()
        if self.plot_tb:
            spec_bound = self.tb_spec_bound
        else:
            spec_bound = self.flx_spec_bound
        self.speccanvas.setLimits(yMin=np.log10(spec_bound[0]), yMax=np.log10(spec_bound[1]))
        self.plot_pgspec()
        self.pgspec_add_boundbox()

    def plot_pgspec(self):
        self.update_fitmask()
        if self.plot_tb:
            spec_bound = self.tb_spec_bound
        else:
            spec_bound = self.flx_spec_bound

        self.spec_dataplots = []
        self.spec_dataplots_tofit = []
        self.spec_rmsplots = []
        current_roi_group = self.rois[self.roi_group_idx]
        for n, roi in enumerate(current_roi_group):
            if n == self.current_roi_idx or (n == len(current_roi_group) + self.current_roi_idx):
                symbolfill = (n, 9)
            else:
                symbolfill = None
            if self.plot_tb:
                spec = roi.tb_max
                spec_bound = self.tb_spec_bound
            else:
                spec = roi.total_flux
                spec_bound = self.flx_spec_bound
            if ma.is_masked(roi.freqghz):
                log_freqghz = np.log10(roi.freqghz.compressed())
                log_spec = np.log10(spec.compressed())
            else:
                log_freqghz = np.log10(roi.freqghz)
                log_spec = np.log10(spec)
            spec_dataplot = self.speccanvas.plot(x=log_freqghz, y=log_spec, pen=None,
                                                 symbol='o', symbolPen=(n, 9), symbolBrush=None)
            spec_dataplot_tofit = self.speccanvas.plot(x=np.log10(roi.freqghz_tofit.compressed()),
                                                       y=np.log10(roi.spec_tofit.compressed()),
                                                       pen=None,
                                                       symbol='o', symbolPen=(n, 9), symbolBrush=symbolfill)

            self.speccanvas.addItem(spec_dataplot)
            self.speccanvas.addItem(spec_dataplot_tofit)
            self.spec_dataplots.append(spec_dataplot)
            self.spec_dataplots_tofit.append(spec_dataplot_tofit)
            #print('ROI', n)
            #print(roi.freqghz_tofit.compressed())
            #print(roi.spec_tofit.compressed())

            # Add errorbar if rms is defined
            if self.has_bkg:
                # define error in spectrum
                if self.plot_tb:
                    spec_rms = self.bkg_roi.tb_rms
                else:
                    spec_rms = gstools.sfu2tb(roi.freqghz * 1e9 * u.Hz, self.bkg_roi.tb_rms * u.K,
                                              area=roi.total_area * u.arcsec ** 2, reverse=True).value
                # add fractional err in quadrature
                spec_err = np.sqrt(spec_rms ** 2. + (self.spec_frac_err * spec) ** 2.)
                spec_rmsplot = self.speccanvas.plot(x=np.log10(self.cfreqs), y=np.log10(spec_rms), pen='k',
                                                    symbol='d', symbolPen='k', symbolBrush=None)
                self.speccanvas.addItem(spec_rmsplot)
                self.spec_rmsplots.append(spec_rmsplot)
            else:
                spec_err = (self.spec_frac_err * spec) ** 2.
            err_bounds_min = np.maximum(spec - spec_err, np.ones_like(spec) * spec_bound[0])
            err_bounds_max = spec + spec_err
            errplot = pg.ErrorBarItem(x=np.log10(roi.freqghz), y=np.log10(spec),
                                      top=np.log10(err_bounds_max) - np.log10(spec),
                                      bottom=np.log10(spec) - np.log10(err_bounds_min), beam=0.025, pen=(n, 9))

            self.speccanvas.addItem(errplot)


        self.fbar = self.speccanvas.plot(x=np.log10([self.pg_img_canvas.timeLine.getXPos()] * 2),
                                         y=[np.log10(spec_bound[0]), np.log10(spec_bound[1])], pen='k')
        self.speccanvas.addItem(self.fbar)
        self.speccanvas.setLimits(yMin=np.log10(spec_bound[0]), yMax=np.log10(spec_bound[1]))
        xax = self.speccanvas.getAxis('bottom')
        yax = self.speccanvas.getAxis('left')
        xax.setLabel("Frequency [GHz]")
        if self.plot_tb:
            yax.setLabel("Brightness Temperature [MK]")
        else:
            yax.setLabel("Flux Density [sfu]")
        xax.setTicks([self.xticks, self.xticks_minor])
        yax.setTicks([self.yticks, self.yticks_minor])

    def pgspec_add_boundbox(self):
        # add frequency bound
        self.rgn_freq_bound = pg.LinearRegionItem(brush=(20, 50, 200, 20))
        self.rgn_freq_bound.setZValue(10)
        self.rgn_freq_bound.setRegion([np.log10(self.fit_freq_bound[0]), np.log10(self.fit_freq_bound[1])])
        self.speccanvas.addItem(self.rgn_freq_bound)
        self.rgn_freq_bound.sigRegionChangeFinished.connect(self.update_freq_bound_rgn)

    def update_fbar(self):
        if self.fbar is not None:
            try:
                self.speccanvas.removeItem(self.fbar)
                self.fbar = self.speccanvas.plot(x=np.log10([self.pg_img_canvas.timeLine.getXPos()] * 2), y=[1, 15],
                                                 pen='k')
                self.speccanvas.addItem(self.fbar)
            except:
                pass

    #    def bkg_rgn_select(self):
    #        """Select a region to calculate rms on spectra"""
    #        if self.bkg_selection_button.isChecked():
    #            self.bkg_selection_button.setStyleSheet("background-color : lightblue")
    #            #self.bkg_roi = pg.RectROI([0, 0], [40, 40], pen='w')
    #            #self.pg_img_canvas.addItem(self.bkg_roi)
    #            #self.bkg_rgn_update()
    #            self.bkg_roi.sigRegionChanged.connect(self.bkg_rgn_update)
    #        else:
    #            # if unChecked remove the ROI box from the plot
    #            self.bkg_selection_button.setStyleSheet("background-color : lightgrey")
    #            self.pg_img_canvas.removeItem(self.bkg_roi)

    def bkg_rgn_update(self):
        """Select a region to calculate rms on spectra"""
        ## todo something is wrong with the bkg roi values
        bkg_subim = self.bkg_roi.getArrayRegion(self.pgdata, self.pg_img_canvas.getImageItem(), axes=(1, 2))
        nf_bkg, ny_bkg, nx_bkg = bkg_subim.shape
        self.bkg_roi.freqghz = self.cfreqs
        self.bkg_roi.tb_mean = np.nanmean(bkg_subim, axis=(1, 2))
        self.bkg_roi.tb_rms = np.std(bkg_subim, axis=(1, 2))
        self.bkg_roi.tb_max = np.nanmax(bkg_subim, axis=(1, 2))
        self.bkg_roi.total_pix = ny_bkg * nx_bkg
        # Total area of the ROI in arcsec^2
        self.bkg_roi.total_area = self.bkg_roi.total_pix * self.meta['header']['CDELT1'] * self.meta['header']['CDELT2']
        # Total flux of the ROI in sfu
        self.bkg_roi.total_flux = gstools.sfu2tb(self.bkg_roi.freqghz * 1e9 * u.Hz, self.bkg_roi.tb_mean * u.K,
                                        area=self.bkg_roi.total_area * u.arcsec ** 2, reverse=True).value
        self.pg_img_bkg_roi_info_widget.setText('[Background] freq: {0:.2f} GHz, '
                                            'T<sub>B</sub><sup>rms</sup>: {1:.2f} MK, '
                                            'T<sub>B</sub><sup>mean</sup>: {2:.2f} MK, Flux: {3:.2f} sfu'.
                                            format(self.pg_freq_current,
                                                   self.bkg_roi.tb_rms[self.pg_freq_idx] / 1e6,
                                                   self.bkg_roi.tb_mean[self.pg_freq_idx] / 1e6,
                                                   self.bkg_roi.total_flux[self.pg_freq_idx]))
        # bkg_roi_label = pg.TextItem("Background", anchor=(0, 0), color='w')
        # bkg_roi_label.setParentItem(self.bkg_roi)
        self.update_pgspec()

    def add_new_roi(self):
        """Add a ROI region to the selection"""
        self.new_roi = pg.RectROI([self.meta['nx'] / 2 - 10,
                                  self.meta['ny'] / 2 - 10], [5, 5], pen=(len(self.rois[self.roi_group_idx]), 9))
        self.pg_img_canvas.addItem(self.new_roi)
        self.new_roi.freq_mask = np.ones_like(self.cfreqs) * False
        self.new_roi.sigRegionChanged.connect(self.calc_roi_spec)
        # choose which group to add
        self.add_to_roigroup_selection()
        self.rois[self.roi_group_idx].append(self.new_roi)
        self.nroi_current_group = len(self.rois[self.roi_group_idx])
        self.roi_selection_widget.clear()
        self.roi_selection_widget.addItems([str(i) for i in range(self.nroi_current_group)])
        self.current_roi_idx = self.nroi_current_group - 1
        self.has_rois = True
        #self.roi_freq_lowbound_selector.setValue(self.data_freq_bound[0])
        #self.roi_freq_hibound_selector.setValue(self.data_freq_bound[1])
        self.calc_roi_spec()

        # self.roi_slider_rangechange()

    def add_to_roigroup_selection(self):
        items = self.add_to_roigroup_widget.selectedItems()
        if len(items) > 0:
            self.add_to_roigroup_button.setText(items[0].text())
            self.roi_group_idx = int(items[0].text())
        else:
            self.roi_group_idx = 0

    def roigroup_selection(self):
        items = self.roigroup_selection_widget.selectedItems()
        if len(items) > 0:
            self.roigroup_selection_button.setText(items[0].text()) ## todo
            self.roi_group_idx = int(items[0].text())
        else:
            self.roi_group_idx = 0

    def roi_selection_action(self):
        ## todo
        items = self.roi_selection_widget.selectedItems()
        if len(items) > 0:
            self.roi_selection_button.setText(items[0].text())
            self.current_roi_idx = int(items[0].text())
        else:
            self.current_roi_idx = len(self.rois[self.roi_group_idx]) - 1
        self.update_pgspec()
        #print(self.current_roi_idx)

    def presets_selector(self):
        print("Seleting ROI(s) with preset: '{}'".format(self.roi_selection_presets_widget.currentText()))
        #self.add_customized_roi = roi_preset_def.add_customized_roi
        self.add_preset = roi_preset_def.add_preset_roi_selection(self, preset=self.roi_selection_presets_widget.currentText())
        #self.add_customized_roi()
        #self.ele_dist = self.ele_function_selector_widget.currentText()
        #self.init_params()

    def fit_method_selector(self):
        print("Selected Fit Method is: {}".format(self.fit_method_selector_widget.currentText()))
        self.fit_method = self.fit_method_selector_widget.currentText()
        self.init_fit_kws()
        self.update_fit_kws_widgets()

    def calc_roi_spec(self):
        #print('=================Update ROI SPEC===============')
        #roi = self.rois[self.roi_group_idx][self.current_roi_idx]
        #roi = self.new_roi
        for roi in self.rois[self.roi_group_idx]:
            ## todo: investigate why using axes = (2, 1) returns entirely different (wrong!) results
            (subim, subim_coords) = roi.getArrayRegion(self.pgdata,
                                                       self.pg_img_canvas.getImageItem(), axes=(1, 2),
                                                       returnMappedCoords=True)
            # subim_coords contain a nested list of the (interpolated) x y pix coordinates in the following form
            # [[y of (pix ij)], [x of (pix ij)]
            nf_sub, ny_sub, nx_sub = subim.shape
            #print('ROI pixel position', roi.pos())
            #print('ROI pixel size', roi.size())
            roi.pos_sol_tlc = [self.mapx[int(round(roi.pos()[0]))], self.mapy[::-1][int(round(roi.pos()[1]))]]
            roi.size_sol = [self.meta['header']['CDELT1'] * roi.size()[0],
                            self.meta['header']['CDELT2'] * roi.size()[1]]
            roi.pos_sol_cen = [roi.pos_sol_tlc[0] + roi.size_sol[0] / 2.,
                               roi.pos_sol_tlc[1] - roi.size_sol[1] / 2.]

            #print('ROI top-left-corner position in solar coords', roi.pos_sol_tlc)
            #print('ROI size in arcsec', roi.size_sol)
            roi.freqghz = self.cfreqs
            roi.freq_bound = copy.copy(self.roi_freq_bound)
            roi.tb_max = np.nanmax(subim, axis=(1, 2))
            roi.tb_mean = np.nanmean(subim, axis=(1, 2))
            roi.total_pix = ny_sub * nx_sub
            # Total area of the ROI in arcsec^2
            roi.total_area = roi.total_pix * self.meta['header']['CDELT1'] * self.meta['header']['CDELT2']
            # Total flux of the ROI in sfu
            roi.total_flux = gstools.sfu2tb(roi.freqghz * 1e9 * u.Hz, roi.tb_mean * u.K,
                                                            area=roi.total_area * u.arcsec ** 2, reverse=True).value
            if np.sum(roi.freq_mask) > 0:
                roi.freqghz = ma.masked_array(roi.freqghz, roi.freq_mask)
                roi.tb_max = ma.masked_array(roi.tb_max, roi.freq_mask)
                roi.tb_mean = ma.masked_array(roi.tb_mean, roi.freq_mask)
                roi.total_flux = ma.masked_array(roi.total_flux, roi.freq_mask)

            #self.update_freq_mask(self.new_roi)

        # print('Shape of the ROI selection', subim.shape)
        # print('Coordinates of the ROI selection', subim_coords)
        #self.pg_img_roi_info_widget.setText('[Current ROI] x: {0:6.1f}", y: {1:6.1f}", freq: {2:4.1f} GHz, '
        #                                    'T<sub>B</sub><sup>max</sup>: {3:5.1f} MK, '
        #                                    'T<sub>B</sub><sup>mean</sup>: {4:5.1f} MK, Flux: {5:5.1f} sfu'.
        #                                    format(roi.pos_sol_cen[0], roi.pos_sol_cen[1], self.pg_freq_current,
        #                                           roi.tb_max[self.pg_freq_idx] / 1e6,
        #                                           roi.tb_mean[self.pg_freq_idx] / 1e6,
        #                                           roi.total_flux[self.pg_freq_idx]))

        #self.update_fitmask()
        self.update_pgspec()

    #def roi_slider_rangechange(self):
    #    self.roi_select_slider.setMaximum(self.nroi - 1)

    #def roi_slider_valuechange(self):
    #    self.current_roi_idx = self.roi_select_slider.value()
    #    self.roi_info.setPlainText('Selected ROI {}'.format(self.current_roi_idx))
    #    self.update_pgspec()

    def roi_freq_lowbound_valuechange(self):
        self.roi_freq_bound[0] = self.roi_freq_lowbound_selector.value()  ##todo
        self.statusBar.showMessage('Selected Lower Frequency Bound for ROI is {0:.1f} GHz'.
                                   format(self.roi_freq_bound[0]))
        self.update_freq_mask(self.new_roi)
        self.update_pgspec()

    def roi_freq_hibound_valuechange(self):
        self.roi_freq_bound[1] = self.roi_freq_hibound_selector.value()  ##todo
        self.statusBar.showMessage('Selected Higher Frequency Bound for ROI is {0:.1f} GHz'.
                                   format(self.roi_freq_bound[1]))
        self.update_freq_mask(self.new_roi)
        self.update_pgspec()

    def update_freq_mask(self, roi):
        # unmask everything first
        if ma.is_masked(roi.freqghz):
            roi.freqghz.mask = ma.nomask
            roi.tb_max.mask = ma.nomask
            roi.tb_mean.mask = ma.nomask
            roi.total_flux.mask = ma.nomask

        # update the masks
        roi.freq_bound = self.roi_freq_bound
        roi.freqghz = ma.masked_outside(self.cfreqs, self.roi_freq_bound[0], self.roi_freq_bound[1])
        roi.freq_mask = roi.freqghz.mask
        roi.tb_max = ma.masked_array(roi.tb_max, roi.freq_mask)
        roi.tb_mean = ma.masked_array(roi.tb_mean, roi.freq_mask)
        roi.total_flux = ma.masked_array(roi.total_flux, roi.freq_mask)

    def roi_grid_size_valuechange(self):
        self.roi_grid_size = self.roi_grid_size_selector.value()

    def freq_lowbound_valuechange(self):
        self.fit_freq_bound[0] = self.freq_lowbound_selector.value()
        self.update_pgspec()

    def freq_hibound_valuechange(self):
        self.fit_freq_bound[1] = self.freq_hibound_selector.value()
        self.update_pgspec()

    def spec_frac_err_valuechange(self):
        self.spec_frac_err = self.spec_frac_err_selector.value()
        self.update_pgspec()

    def update_freq_bound_rgn(self):
        self.rgn_freq_bound.setZValue(10)
        min_logfreq, max_logfreq = self.rgn_freq_bound.getRegion()
        self.fit_freq_bound = [10. ** min_logfreq, 10. ** max_logfreq]
        self.update_fitmask()
        self.freq_lowbound_selector.setValue(self.fit_freq_bound[0])
        self.freq_hibound_selector.setValue(self.fit_freq_bound[1])
        for spec_dataplot, spec_dataplot_tofit, spec_rmsplot in \
                zip(self.spec_dataplots, self.spec_dataplots_tofit, self.spec_rmsplots):
            self.speccanvas.removeItem(spec_dataplot)
            self.speccanvas.removeItem(spec_dataplot_tofit)
            self.speccanvas.removeItem(spec_rmsplot)
        self.plot_pgspec()

    def fit_method_selector(self):
        print("Selected Fit Method is: {}".format(self.fit_method_selector_widget.currentText()))
        self.fit_method = self.fit_method_selector_widget.currentText()
        self.init_fit_kws()
        self.update_fit_kws_widgets()

    def ele_function_selector(self):
        print("Selected Electron Distribution Function is: {}".format(self.ele_function_selector_widget.currentText()))
        self.ele_dist = self.ele_function_selector_widget.currentText()
        self.init_params()

    def init_params(self):
        if self.ele_dist == 'powerlaw':
            self.fit_params = lmfit.Parameters()
            self.fit_params.add_many(('Bx100G', 2., True, 0.1, 100., None, None),
                                     ('log_nnth', 5., True, 3., 11, None, None),
                                     ('delta', 4., True, 1., 30., None, None),
                                     ('Emin_keV', 10., False, 1., 100., None, None),
                                     ('Emax_MeV', 10., False, 0.05, 100., None, None),
                                     ('theta', 45., True, 0.01, 89.9, None, None),
                                     ('log_nth', 10, True, 4., 13., None, None),
                                     ('T_MK', 1., False, 0.1, 100, None, None),
                                     ('depth_asec', 5., False, 1., 100., None, None))
            self.fit_params_nvarys = 0
            for key, par in self.fit_params.items():
                if par.vary:
                    self.fit_params_nvarys += 1

            self.fit_function = gstools.GSCostFunctions.SinglePowerLawMinimizerOneSrc
            self.update_fit_param_widgets()

        if self.ele_dist == 'thermal f-f':
            self.fit_params = lmfit.Parameters()
            self.fit_params.add_many(('theta', 45., True, 0.01, 89.9, None, None),
                                     ('log_nth', 10, True, 4., 13., None, None),
                                     ('T_MK', 1., False, 0.1, 100, None, None),
                                     ('depth_asec', 5., False, 1., 100., None, None),
                                     ('area_asec2', 25., False, 1., 10000., None, None))
            self.fit_params_nvarys = 0
            for key, par in self.fit_params.items():
                if par.vary:
                    self.fit_params_nvarys += 1

            self.update_fit_param_widgets()
            self.fit_function = gstools.GSCostFunctions.SinglePowerLawMinimizerOneSrc ## todo: to be added
            self.update_fit_param_widgets()
        # print(self.fit_params)

    def init_fit_kws(self):
        # first refresh the widgets
        if self.fit_method == 'nelder':
            self.fit_kws = {'maxiter': 2000, 'xatol': 0.01, 'fatol': 0.01}
        if self.fit_method == 'basinhopping':
            self.fit_kws = {'niter': 50, 'T': 90., 'stepsize': 0.8,
                            'interval': 25}

    def update_fit_kws_widgets(self):
        # first delete every widget for the fit keywords
        if self.fit_kws_box.count() > 0:
            for n in reversed(range(self.fit_kws_box.count())):
                self.fit_kws_box.itemAt(n).widget().deleteLater()

        self.fit_kws_key_widgets = []
        self.fit_kws_value_widgets = []
        for n, key in enumerate(self.fit_kws):
            fit_kws_key_widget = QLabel(key)
            self.fit_kws_box.addWidget(fit_kws_key_widget)
            if type(self.fit_kws[key]) == int:
                fit_kws_value_widget = QSpinBox()
                fit_kws_value_widget.setRange(0, 10000)
                fit_kws_value_widget.setValue(self.fit_kws[key])
                fit_kws_value_widget.valueChanged.connect(self.update_fit_kws)
            if type(self.fit_kws[key]) == float:
                fit_kws_value_widget = QDoubleSpinBox()
                fit_kws_value_widget.setRange(0, 10000)
                fit_kws_value_widget.setValue(self.fit_kws[key])
                fit_kws_value_widget.setDecimals(2)
                fit_kws_value_widget.valueChanged.connect(self.update_fit_kws)
            if type(self.fit_kws[key]) == str:
                fit_kws_value_widget = QTextEdit()
                fit_kws_value_widget.setText(self.fit_kws[key])
                fit_kws_value_widget.valueChanged.connect(self.update_fit_kws)
            self.fit_kws_key_widgets.append(fit_kws_key_widget)
            self.fit_kws_value_widgets.append(fit_kws_value_widget)
            self.fit_kws_box.addWidget(fit_kws_value_widget)

    def update_fit_param_widgets(self):
        # first delete every widget for the fit parameters
        if self.fit_param_box.count() > 0:
            for n in reversed(range(self.fit_param_box.count())):
                self.fit_param_box.itemAt(n).widget().deleteLater()

        self.param_init_value_widgets = []
        self.param_vary_widgets = []
        self.param_min_widgets = []
        self.param_max_widgets = []
        self.param_fit_value_widgets = []
        self.fit_param_box.addWidget(QLabel('Name'), 0, 0)
        self.fit_param_box.addWidget(QLabel('Initial Guess'), 0, 1)
        self.fit_param_box.addWidget(QLabel('Vary'), 0, 2)
        self.fit_param_box.addWidget(QLabel('Minimum'), 0, 3)
        self.fit_param_box.addWidget(QLabel('Maximum'), 0, 4)
        self.fit_param_box.addWidget(QLabel('Fit Results'), 0, 5)
        for n, key in enumerate(self.fit_params):
            # param_layout = QHBoxLayout()
            # param_layout.addWidget(QLabel(key))
            param_init_value_widget = QDoubleSpinBox()
            param_init_value_widget.setDecimals(1)
            param_init_value_widget.setValue(self.fit_params[key].init_value)
            param_init_value_widget.valueChanged.connect(self.update_params)

            param_vary_widget = QCheckBox()
            param_vary_widget.setChecked(self.fit_params[key].vary)
            param_vary_widget.toggled.connect(self.update_params)

            param_min_widget = QDoubleSpinBox()
            param_min_widget.setDecimals(1)
            param_min_widget.setValue(self.fit_params[key].min)
            param_min_widget.valueChanged.connect(self.update_params)

            param_max_widget = QDoubleSpinBox()
            param_max_widget.setDecimals(1)
            param_max_widget.setValue(self.fit_params[key].max)
            param_max_widget.valueChanged.connect(self.update_params)

            param_fit_value_widget = QDoubleSpinBox()
            param_fit_value_widget.setDecimals(1)
            param_fit_value_widget.setValue(self.fit_params[key].value)
            param_fit_value_widget.valueChanged.connect(self.update_params)

            self.fit_param_box.addWidget(QLabel(fit_param_text[key]), n + 1, 0)
            self.fit_param_box.addWidget(param_init_value_widget, n + 1, 1)
            self.fit_param_box.addWidget(param_vary_widget, n + 1, 2)
            self.fit_param_box.addWidget(param_min_widget, n + 1, 3)
            self.fit_param_box.addWidget(param_max_widget, n + 1, 4)
            self.fit_param_box.addWidget(param_fit_value_widget, n + 1, 5)

            self.param_init_value_widgets.append(param_init_value_widget)
            self.param_vary_widgets.append(param_vary_widget)
            self.param_min_widgets.append(param_min_widget)
            self.param_max_widgets.append(param_max_widget)
            self.param_fit_value_widgets.append(param_fit_value_widget)

    def update_fit_kws(self):
        # print('==========Parameters Updated To the Following=======')
        for n, key in enumerate(self.fit_kws):
            if (isinstance(self.fit_kws_value_widgets[n], QSpinBox)
                    or isinstance(self.fit_kws_value_widgets[n], QDoubleSpinBox)):
                self.fit_kws[key] = self.fit_kws_value_widgets[n].value()
            if isinstance(self.fit_kws_value_widgets[n], QLineEdit):
                self.fit_kws[key] = self.fit_kws_value_widgets[n].toPlainText()
        # print(self.fit_kws)

    def update_params(self):
        # print('==========Parameters Updated To the Following=======')
        self.fit_params_nvarys = 0
        for n, key in enumerate(self.fit_params):
            self.fit_params[key].init_value = self.param_init_value_widgets[n].value()
            self.fit_params[key].vary = self.param_vary_widgets[n].isChecked()
            self.fit_params[key].min = self.param_min_widgets[n].value()
            self.fit_params[key].max = self.param_max_widgets[n].value()
            self.fit_params[key].value = self.param_init_value_widgets[n].value()
            if self.fit_params[key].vary:
                self.fit_params_nvarys += 1

    def tb_flx_btnstate(self):
        if self.plot_tb_button.isChecked() == True:
            self.statusBar.showMessage('Plot Brightness Temperature')
            self.plot_tb = True
            if 'area_asec2' in self.fit_params.keys():
                del self.fit_params['area_asec2']
                self.update_fit_param_widgets()
        else:
            self.statusBar.showMessage('Plot Flux Density')
            self.plot_tb = False
            if not 'area_asec2' in self.fit_params.keys():
                self.fit_params.add_many(('area_asec2', 25., False, 1., 10000., None, None))
                self.update_fit_param_widgets()
        self.init_pgspecplot()
        self.update_pgspec()


    def do_spec_fit(self):
        roi = self.rois[self.roi_group_idx][self.current_roi_idx]
        freqghz_tofit = roi.freqghz_tofit.compressed()
        spec_tofit = roi.spec_tofit.compressed()
        spec_err_tofit = roi.spec_err_tofit.compressed()
        max_nfev = 1000
        ## Set up fit keywords
        fit_kws = self.fit_kws
        if self.fit_method == 'basinhopping':
            fit_kws['minimizer_kwargs'] = {'method': 'Nelder-Mead'}
            max_nfev *= self.fit_kws['niter'] * (self.fit_params_nvarys + 1)
        if self.fit_method == 'nelder':
            fit_kws = {'options': self.fit_kws}
        print(fit_kws)

        if hasattr(self, 'spec_fitplot'):
            self.speccanvas.removeItem(self.spec_fitplot)

        mini = lmfit.Minimizer(gstools.GSCostFunctions.SinglePowerLawMinimizerOneSrc, self.fit_params,
                               fcn_args=(freqghz_tofit,),
                               fcn_kws={'spec': spec_tofit, 'spec_err': spec_err_tofit, 'spec_in_tb': self.plot_tb},
                               max_nfev=max_nfev, nan_policy='omit')
        method = self.fit_method
        mi = mini.minimize(method=method, **fit_kws)
        print(method + ' minimization results')
        print(lmfit.fit_report(mi, show_correl=True))
        self.fit_params_res = mi.params
        print('==========Fit Parameters Updated=======')
        for n, key in enumerate(self.fit_params_res):
            self.param_fit_value_widgets[n].setValue(self.fit_params_res[key].value)

        freqghz_toplot = np.logspace(0, np.log10(20.), 100)
        spec_fit_res = self.fit_function(mi.params, freqghz_toplot, spec_in_tb=self.plot_tb)
        self.spec_fitplot = self.speccanvas.plot(x=np.log10(freqghz_toplot), y=np.log10(spec_fit_res),
                                                 pen=dict(color=pg.mkColor(self.current_roi_idx), width=4),
                                                 symbol=None, symbolBrush=None)
        self.speccanvas.addItem(self.spec_fitplot)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
