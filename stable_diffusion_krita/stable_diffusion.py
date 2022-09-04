from PyQt5.QtWidgets import *
from krita import *
from . import sd_main
class SDDocker(DockWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stable Diffusion")
        mainWidget = QWidget(self)
        self.setWidget(mainWidget)
        mainWidget.setLayout(QVBoxLayout())
        btnFromText = QPushButton("From Text", mainWidget)
        btnFromImage = QPushButton("From Image", mainWidget)
        btnInpaint = QPushButton("Inpaint", mainWidget)
        btnConfig = QPushButton("", mainWidget)
        btnSelection = QPushButton("", mainWidget)

        mainWidget.layout().addWidget(btnFromText)        
        mainWidget.layout().addWidget(btnFromImage)        
        mainWidget.layout().addWidget(btnInpaint)


        h_layout=QHBoxLayout()
        btnConfig.setIcon( Krita.instance().icon('configure'))        
        btnSelection.setIcon( Krita.instance().icon('tool_rect_selection'))        
        h_layout.addWidget(btnConfig)        
        h_layout.addWidget(btnSelection)        
        mainWidget.layout().addLayout(h_layout)

        btnFromText.clicked.connect(sd_main.TxtToImage)
        btnFromImage.clicked.connect(sd_main.ImageToImage)
        btnInpaint.clicked.connect(sd_main.Inpainting)
        btnConfig.clicked.connect(sd_main.Config)
        btnSelection.clicked.connect(sd_main.expandSelection)


    def canvasChanged(self, canvas):
        pass

Krita.instance().addDockWidgetFactory(DockWidgetFactory("Stable Diffusion", DockWidgetFactoryBase.DockRight, SDDocker))
