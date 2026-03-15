from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QFileDialog, QVBoxLayout, QWidget, QListWidget, QLineEdit, QLabel, QPushButton, QSplitter, QTabWidget, QColorDialog, 
QInputDialog, QGraphicsTextItem, QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem, QGraphicsSimpleTextItem)

from PyQt5.QtGui import (QPixmap, QPainter, QPainterPath, QPen, QColor, QBrush, QFont, QRadialGradient, QPalette)
from PyQt5.QtCore import Qt, QRectF, QPoint, QPointF, QLineF, QTimer

from PyQt5.QtMultimediaWidgets import QVideoWidget

import sys, json, math, os, shutil

import vlc

if sys.platform == "win32":
    os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(__file__)

SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

class MapGraphicView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self._zoom = 0
        self.mainWindow = None
        self.rulerStart = None
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHints(
            QPainter.Antialiasing |
            QPainter.SmoothPixmapTransform
        )

    def wheelEvent(self, event):
        zoomInFactor = 1.25
        zoomOutFactor = 1 / zoomInFactor
        if event.angleDelta().y() > 0:
            zoomFactor = zoomInFactor
            self._zoom += 1
        else:
            zoomFactor = zoomOutFactor
            self._zoom -= 1

        if self._zoom < -10:
            self._zoom = -10
            return
        if self._zoom > 10:
            self._zoom = 10
            return
        
        self.scale(zoomFactor, zoomFactor)

    def mousePressEvent(self, event):
        if self.mainWindow and self.mainWindow.rulerMode:
            scenePos = self.mapToScene(event.pos())
            
            if event.button() == Qt.RightButton:
                items = self.scene().items(scenePos)
                for it in items:
                    if isinstance(it, QGraphicsLineItem):
                        self.scene().removeItem(it)
                        if it is self.mainWindow.currentRuler:
                            self.mainWindow.currentRuler = None
                            self.rulerStart = None
                        return
                return
    
            if event.button() == Qt.LeftButton:
                if self.mainWindow.currentRuler is None or self.rulerStart is None:
                    self.rulerStart = scenePos
                    line = QGraphicsLineItem(QLineF(scenePos, scenePos))
                    line.setPen(QPen(Qt.yellow, 2))
                    textItem = QGraphicsSimpleTextItem("0", line)
                    textItem.setBrush(QBrush(Qt.white))
                    textItem.setPos(scenePos)
                    line.setZValue(5)
                    self.scene().addItem(line)
                    self.mainWindow.currentRuler = line

                else:
                    newLine = QLineF(self.rulerStart, scenePos)
                    line = self.mainWindow.currentRuler
                    line.setLine(newLine)
                    dist = newLine.length()
                    for child in line.childItems():
                        if isinstance(child, QGraphicsSimpleTextItem):
                            child.setText(f"{dist:.1f}")
                            mid = (newLine.p1() + newLine.p2()) / 2
                            child.setPos(mid)
                    self.rulerStart = None
                return
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self.mainWindow and self.mainWindow.rulerMode and 
        self.rulerStart is not None and self.mainWindow.currentRuler is not None):

            scenePos = self.mapToScene(event.pos())
            line = self.mainWindow.currentRuler
            newLine = QLineF(self.rulerStart, scenePos)
            line.setLine(newLine)
            dist = newLine.length()
            for child in line.childItems():
                if isinstance(child, QGraphicsSimpleTextItem):
                    child.setText(f"{dist:.1f}")
                    mid = (newLine.p1() + newLine.p2()) / 2
                    child.setPos(mid)    
            return
        super().mouseMoveEvent(event)

class FogItem(QGraphicsRectItem):
    def __init__(self, rect):
        super().__init__(rect)
        self.setBrush(QBrush(QColor(0, 0, 0, 180)))
        self.setZValue(1)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, False)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, False)
        self.setAcceptedMouseButtons(Qt.NoButton)

    def setDensity(self, alpha):
        color = self.brush().color()
        self.setBrush(QColor(color.red(), color.green(), color.blue(), alpha))

class LightItem(QGraphicsEllipseItem):
    def __init__(self, radius, center):
        super().__init__(-radius, -radius, radius*2, radius*2)
        self.radius = radius

        gradient = QRadialGradient(0, 0, radius)
        gradient.setColorAt(0, QColor(255, 255, 200, 80))
        gradient.setColorAt(1, QColor(0, 0, 0, 0))

        self.setBrush(QBrush(gradient))
        self.setPos(center)
        self.setZValue(-1)
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, False)
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable, False)

class LightCone(QGraphicsItem):
    def __init__(self, radius, center, angle=90):
        super().__init__()
        self.radius = radius
        self.angle = angle
        self.rotation_angle = 0

        self._rect = QRectF(-radius, -radius, radius*2, radius*2)
        self.setPos(center)
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def boundingRect(self):
        return self._rect

    def setRotationAngle(self, angle):
        self.rotation_angle = angle % 360
        self.update()

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)

        center = QPointF(0, 0)
        half_angle = (self.angle / 2.0) * math.pi / 180.0
        dir_rad = self.rotation_angle * math.pi / 180.0

        path = QPainterPath()
        path.moveTo(center)

        #Ponto 1 (Esquerda)
        p1 = QPointF(
            self.radius * math.cos(dir_rad - half_angle),
            self.radius * math.sin(dir_rad - half_angle)
        )
        path.lineTo(p1)

        #Arco do Cone
        arc_rect = QRectF(-self.radius, -self.radius, self.radius * 2, self.radius * 2)
        start_deg = -math.degrees(dir_rad - half_angle)
        span_deg = -self.angle
        path.arcTo(arc_rect, start_deg, span_deg)

        #Ponto 2 (Direita)
        p2 = QPointF(
            self.radius * math.cos(dir_rad + half_angle),
            self.radius * math.sin(dir_rad + half_angle)
        )
        path.lineTo(p2)
        path.closeSubpath()

        #Gradiente
        gradient = QRadialGradient(center, self.radius)
        gradient.setColorAt(0, QColor(255, 255, 220, 200))
        gradient.setColorAt(0.7, QColor(200, 180, 100, 80))
        gradient.setColorAt(1, QColor(0, 0, 0, 0))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            parent = self.parentItem()
            if isinstance(parent, TokenItem):
                parent.setSelected(False)
            self.setSelected(True)
            self._dragStartPos = event.pos()
            self._dragStartAngle = self.rotation_angle
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            p = event.pos()
            angle = math.degrees(math.atan2(p.y(), p.x()))
            self.setRotationAngle(angle)
            event.accept()
        else:
            super().mouseMoveEvent(event)

class RulerItem(QGraphicsLineItem):
    def __init__(self, start, end, text):
        super().__init__(start.x(), start.y(), end.x(), end.y())
        self.setPen(QPen(Qt.yellow, 2))
        self.textItem = QGraphicsSimpleTextItem(text, self)
        self.textItem.setBrush(QBrush(Qt.white))
        mid = QPointF((start.x() + end.x()) / 2, (start.y() + end.y()) / 2)
        self.textItem.setPos(mid)
        self.setZValue(2)

class HealthBar(QGraphicsRectItem):
    def __init__(self, max_health, current_health, parent=None):
        super().__init__(-50, -25, 100, 8, parent)
        self.max_health = max_health
        self.current_health = current_health
        self.setZValue(10)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, False)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, False)

    def setHealth(self, health):
        self.current_health = min(max(health, 0), self.max_health)
        self.update()

    def paint (self, painter, option, widget):
        rect = self.boundingRect()
        
        painter.setBrush(QBrush(QColor(60, 60, 60)))
        painter.setPen(QPen(QColor(100, 100,100), 1))
        painter.drawRect(rect)

        ratio = self.current_health / self.max_health
        fill_width = rect.width() * ratio

        if ratio > 0.6:
            color = QColor(0, 200, 0)
        elif ratio > 0.3:
            color = QColor(255, 255, 0)
        else:
            color = QColor(255, 50, 50)
        
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect.x(), rect.y(), fill_width, rect.height())

        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(rect)

class PlayerCard(QGraphicsRectItem):
    def __init__(self, pixmap, name, max_health, current_health, is_boss=False, parent=None):
        super().__init__(-100, -125, 200, 250, parent)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        self.setZValue(15)

        self.name = name
        self.is_boss = is_boss
        self.max_health = max_health
        self.current_health = current_health

        self.bg_rect = QGraphicsRectItem(self.rect(), self)
        self.bg_rect.setBrush(QBrush(QColor(40, 40, 60) if is_boss else QColor(20, 40, 80)))
        self.bg_rect.setPen(QPen(QColor(80, 80, 120), 2))

        self.image_item = QGraphicsPixmapItem(pixmap.scaled(80, 80, Qt.KeepAspectRatio, 
        Qt.ScreenTransformation), self)
        self.image_item.setPos(-40, 10)

        self.name_text = QGraphicsTextItem(name, self)
        self.name_text.setDefaultTextColor(Qt.white)
        font = QFont()
        font.setPointSize(12 if is_boss else 10)
        self.name_text.setFont(font)
        self.name_text.setPos(-80, 95)

        self.health_bar = HealthBar(max_health, current_health, self)
        self.health_bar.setPos(-50, 130)

        self.hp_text =  QGraphicsTextItem(f"{current_health}/{max_health} HP", self)
        self.hp_text.setDefaultTextColor(Qt.white)
        self.hp_text.setFont(QFont("Arial", 9))
        self.hp_text.setPos(-45, 145)

        def setHealth(self, health):
            self.current_health = health
            self.health_bar.setHealth(health)
            self.hp_text.setPlainText(f"{health}/{self.max_health} HP")

class TokenItem(QGraphicsPixmapItem):

    def __init__(self, pixmap, border_color=Qt.green, callback=None):
        super().__init__(pixmap)
        self.callback = callback

        self.setFlag(QGraphicsPixmapItem.ItemIsMovable, True)
        self.setFlag(QGraphicsPixmapItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsPixmapItem.ItemSendsScenePositionChanges, True)
        self.setFlag(QGraphicsPixmapItem.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)
        self.border_color = border_color
        self.preview = None

    def paint(self, painter, option, widget):
        path = QPainterPath()
        path.addEllipse(QRectF(0, 0, self.pixmap().width(), self.pixmap().height()))
        painter.setClipPath(path)
        super().paint(painter, option, widget)

        pen = QPen(QColor(self.border_color))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.setClipping(False)
        painter.drawEllipse(QRectF(1, 1, self.pixmap().width()-2, self.pixmap().height()-2))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            for child in self.childItems():
                child.setSelected(False)
            self.setSelected(True)
            self.setFocus()
        super().mousePressEvent(event)

    def hoverEnterEvent(self, event):
        if self.preview is None:
            from PyQt5.QtWidgets import QLabel
            self.preview = QLabel()
            self.preview.setWindowFlags(Qt.ToolTip)
            enlarged_pixmap = self.pixmap().scaled(100, 100, Qt.KeepAspectRatio,
        Qt.SmoothTransformation)
            self.preview.setPixmap(enlarged_pixmap)
        posf = event.screenPos()
        pos = QPoint(int(posf.x()), int(posf.y()))
        self.preview.move(pos + QPoint(20, 20))
        self.preview.show()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if self.preview:
            self.preview.hide()
        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.callback:
            self.callback(self)
        event.accept()

    def contextMenuEvent(self, event):
        if self.callback:
            self.callback(self)
        event.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RPG Studio")
        self.resize(1200, 700)
        self.sceneCounter = 0
        self.rulerMode = False
        self.currentRuler = None
        self.currentTheme = "light"

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.South)
        self.setCentralWidget(self.tabs)

        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(__file__)
        
        self.cinematicsDir = os.path.join(base_dir, "cinematics")
        os.makedirs(self.cinematicsDir, exist_ok=True)

        self.cineTimer = QTimer(self)
        self.cineTimer.setSingleShot(True)
        self.cineTimer.timeout.connect(self.runCinematic)
        self.pendingCinematicName = None 

        self.scenes = []
        self.views = []
        self.turnLists = []
        self.nameInputs = []
        self.mapItems = []
        self.fogItems = []
        self.tokenLights = {}
        self.savedLights = {}

        self.initMenu()
        self.addSceneTab("Cena 1")
        self.initCinematicsTab()

        self.videoWindow = QMainWindow(self)
        self.videoWindow.setWindowTitle("Cinematic")
        self.videoWindow.resize(800,450)
        
        self.videoWidget = QVideoWidget(self.videoWindow)
        self.videoWindow.setCentralWidget(self.videoWidget)
        
        self.vlc_instance = vlc.Instance()
        self.vlc_player = self.vlc_instance.media_player_new()

        self.pendingCinematicPath = None

        self.loadSettings()
    
    def addSceneTab(self, name=None):
        if name is None:
            self.sceneCounter += 1
            name = f'Cena {self.sceneCounter}'

        scene = QGraphicsScene(self)
        view = MapGraphicView(scene)
        view.mainWindow = self

        turnOrderList = QListWidget()
        turnOrderList.setDragDropMode(QListWidget.InternalMove)

        nameInput = QLineEdit()
        nameInput.setPlaceholderText("Digite o nome")
        addButton = QPushButton("Adicionar Turno")
        deleteTurnButton = QPushButton("Deletar")

        inputLayout = QVBoxLayout()
        inputLayout.addWidget(nameInput)
        inputLayout.addWidget(addButton)
        inputLayout.addWidget(deleteTurnButton)

        listContainer = QWidget()
        listLayout = QVBoxLayout(listContainer)
        listLayout.addLayout(inputLayout)
        listLayout.addWidget(turnOrderList)

        splitter = QSplitter()
        splitter.addWidget(view)
        splitter.addWidget(listContainer)
        splitter.setSizes([800, 350])

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(splitter)

        index = self.tabs.addTab(container, name)

        self.scenes.append(scene)
        self.views.append(view)
        self.turnLists.append(turnOrderList)
        self.nameInputs.append(nameInput)
        self.mapItems.append(None)
        self.fogItems.append(None)

        addButton.clicked.connect(lambda _, i=index: self.addTurn(i))
        deleteTurnButton.clicked.connect(lambda _, i=index: self.deleteSelectedTurn(i))

    def currentIndex(self):
        return self.tabs.currentIndex()
    
    def initMenu(self):
        menu = self.menuBar()

        mapMenu = menu.addMenu("Mapa/Cena")
        openAction = mapMenu.addAction("Abrir Mapa")
        openAction.triggered.connect(self.openImage)

        newSceneAction = mapMenu.addAction("Nova Cena")
        newSceneAction.triggered.connect(lambda: self.addSceneTab("Nova Cena"))

        clearSceneAction = mapMenu.addAction("Limpar Cena")
        clearSceneAction.triggered.connect(lambda: self.clearCurrentScene)

        cineMenu = menu.addMenu("Cinematics")
        addCineAction = cineMenu.addAction("Adicionar Cinematic")
        addCineAction.triggered.connect(self.addCinematicFile)

        tokenMenu = menu.addMenu("Tokens")
        openTokenAction = tokenMenu.addAction("Add Player Token")
        openTokenAction.triggered.connect(self.openTokenImage)

        textMenu = menu.addMenu("Texto")
        addTextAction = textMenu.addAction("Adicionar Texto")
        addTextAction.triggered.connect(self.addTextOnMap)

        fogMenu = menu.addMenu("Névoa")
        addFogAction = fogMenu.addAction("Adicionar Névoa")
        addFogAction.triggered.connect(self.setFogOnMap)

        themeMenu = menu.addMenu("Tema")
        lightAction = themeMenu.addAction("Claro")
        darkAction = themeMenu.addAction("Escuro")

        lightAction.triggered.connect(lambda: self.apply_theme("light"))
        darkAction.triggered.connect(lambda: self.apply_theme("dark"))

        functionsMenu = menu.addMenu("Funções")
        self.rubberBandAction = functionsMenu.addAction("Seleção Multipla")
        self.rubberBandAction.setCheckable(True)
        self.rubberBandAction.setChecked(False)
        self.rubberBandAction.triggered.connect(self.toggleRubberBandMode)

        self.rulerAction = functionsMenu.addAction("Régua")
        self.rulerAction.setCheckable(True)
        self.rulerAction.setChecked(False)
        self.rulerAction.triggered.connect(self.toggleRulerMode)

    def addCinematicFile(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar arquivo de Cinematic",
            "",
            "Vídeos (*.mp4 *.avi *.mkv *.mov *.webm);;Todos os Arquivos(*)",
            options=options
        )
        if not filename:
            return
        
        base = os.path.basename(filename)
        dest = os.path.join(self.cinematicsDir, base)

        if os.path.exists(dest):
            name, ext = os.path.splitext(base)
            i = 1
            while True:
                new_base = f"{name}_{i}{ext}"
                dest = os.path.join(self.cinematicsDir, new_base)
                if not os.path.exists(dest):
                    base = new_base
                    break
                i += 1

        shutil.copy2(filename, dest)
        self.reloadCinematicList()

    def initCinematicsTab(self):
        self.cineWidget = QWidget()
        layout = QVBoxLayout(self.cineWidget)

        self.cineList = QListWidget()

        self.cineSartButton = QPushButton("Iniciar Cinematic (5s)")
        self.cineSartButton.clicked.connect(self.startSelectedCinematic)

        layout.addWidget(QLabel("Cinematic Disponíveis: "))
        layout.addWidget(self.cineList)
        layout.addWidget(self.cineSartButton)

        self.reloadCinematicList()

        self.tabs.addTab(self.cineWidget, "Cinematics")

    def reloadCinematicList(self):
        self.cineList.clear()
        if not os.path.isdir(self.cinematicsDir):
            return
        
        for name in sorted(os.listdir(self.cinematicsDir), key=str.lower):
            path = os.path.join(self.cinematicsDir, name)
            if os.path.isfile(path):
                self.cineList.addItem(name)

    def startSelectedCinematic(self):
        item = self.cineList.currentItem()
        if not item:
            return
        
        name = item.text()
        self.pendingCinematicName = name
        self.pendingCinematicPath = os.path.join(self.cinematicsDir, name)

        self.cineSartButton.setEnabled(False)
        self.cineSartButton.setText(f"Iniciando '{name}' em 5s...")
        self.cineTimer.start(5000)

    def runCinematic(self):
        name = self.pendingCinematicName
        path = self.pendingCinematicPath

        print("CINEMATIC:", name, path)

        self.pendingCinematicName = None
        self.pendingCinematicPath = None

        self.cineSartButton.setEnabled(True)
        self.cineSartButton.setText("Iniciar Cinematic (5s)")

        if not name or not path or not os.path.isfile(path):
            print("Arquivo não encontrado")
            return
        
        media = self.vlc_instance.media_new(path)
        self.vlc_player.set_media(media)

        win_id = int(self.videoWidget.winId())
        self.vlc_player.set_hwnd(win_id)

        self.videoWindow.show()
        self.vlc_player.play()

    def toggleRubberBandMode(self, checked):
        if checked:
            self.rubberBandAction.setText("Seleção Multipla (ON)")
        else:
            self.rubberBandAction.setText("Seleção Multipla")

        idx = self.currentIndex()
        if idx < 0:
            return
        
        view = self.views[idx]
        if checked:
            view.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            view.setDragMode(QGraphicsView.ScrollHandDrag)     

    def openImage(self):
        idx = self.currentIndex()
        if idx < 0:
            return

        scene = self.scenes[idx]

        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(self, "Open Map Image", "","Image Files (*.png *.jpg *.bmp)",
        options=options)

        if filename:
            pixmap = QPixmap(filename)
            if self.mapItems[idx]:
                scene.removeItem(self.mapItems[idx])
            mapItem = QGraphicsPixmapItem(pixmap)
            mapItem.setZValue(0)
            scene.addItem(mapItem)
            scene.setSceneRect(QRectF(pixmap.rect()))
            self.mapItems[idx] = mapItem

    def openTokenImage(self):
        idx = self.currentIndex()
        if idx < 0:
            return
        
        scene = self.scenes[idx]
        view = self.views[idx]
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(self, "Open Token Image", "", "Image Files (*.png *.jpg *.bmp)",
        options=options)

        if not filename:
            return
        color = QColorDialog.getColor(Qt.green, self, "Select Border Color")
        if not color.isValid():
            color = Qt.green

        pixmap = self.create_token_pixmap(filename)
        token = TokenItem(pixmap, border_color=color, callback=self.editTokenDialog)
        token.setZValue(3)

        center = view.mapToScene(view.viewport().rect().center())
        token.setPos(center - token.boundingRect().center())
        scene.addItem(token)

    def create_token_pixmap(self, image_path):
        size = 40
        original = QPixmap(image_path).scaled(size, size, Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation)
        
        rounded = QPixmap(size, size)
        rounded.fill(Qt.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, original)
        painter.end()

        return rounded

    def editTokenDialog(self, token):
        color = QColorDialog.getColor(token.border_color, self, "Selecione cor da borda")
        if color.isValid():
            token.border_color = color
            token.update()
        #Seleção: Circulo ou Cone

        light_type, ok = QInputDialog.getItem(
            self, "Tipo de Visão",
            "Ecolha o tipo de visão:",
            ["Nenhuma", "Círculo(360°)", "Cone Rotacionável"], 0, False
        )
        
        if not ok:
            return

        if token in self.tokenLights:
            old = self.tokenLights.pop(token)
            if isinstance(old ,LightItem):
                self.savedLights[token] = ("circle", old.radius, None, None)
            elif isinstance(old, LightCone):
                self.savedLights[token] = ("cone", old.radius, old.angle, old.rotation_angle)
                
            old.setParentItem(None)
            self.scenes[self.currentIndex()].removeItem(old)
        
        if light_type == "Nenhuma":
            return
        
        if token in self.savedLights:
            saved_type, saved_radius, saved_angle, saved_rot = self.savedLights[token]
        else:
            saved_type = saved_radius = saved_angle = saved_rot = None

        radius, ok = QInputDialog.getInt(self, "Raio de Visão", "Defina o raio de visão: ", 100, 10, 600)

        if not ok:
            return
        

        if light_type == "Círculo(360°)":
            light = LightItem(radius, QPointF(0, 0))
        else:
            # CONE - pede ângulo + rotação inicial
            default_angle = saved_angle if (saved_type == "cone" and saved_angle) else 90
            default_rot = saved_rot if (saved_type == "cone" and saved_rot is not None) else 0

            angle, ok2 = QInputDialog.getInt(
                self, "Ângulo do Cone",
                "Ângulo Fixo (60-120°): ",
                int(default_angle), 60, 120
            )
            if not ok2:
                return
            
            rotation, ok3 = QInputDialog.getInt(
                self, "Rotação Cone",
                "Rotação Inicial (0 = Norte, 90 = Leste): ",
                int(default_rot), 0, 359
            )
            if not ok3:
                return
            
            light = LightCone(radius, QPointF(0, 0), angle)
            light.setRotationAngle(rotation)

            self.savedLights[token] = ("cone", radius, angle, rotation)

        light.setParentItem(token)
        light.setPos(token.boundingRect().center())
        self.tokenLights[token] = light

    def toggleRulerMode(self, checked):
        self.rulerMode = checked
        if checked:
            self.rubberBandAction.setChecked(False)
            self.toggleRubberBandMode(False)

        if not checked and self.currentRuler:
            scene = self.scenes[self.currentIndex()]
            scene.removeItem(self.currentRuler)
            self.currentRuler = None

    def addTextOnMap(self):
        idx = self.currentIndex()
        if idx < 0:
            return
        scene = self.scenes[idx]
        view = self.views[idx]

        text, ok = QInputDialog.getText(self, "Adicionar Texto", "Digite o texto:")

        if ok and text:
            textItem = QGraphicsTextItem(text)
            textItem.setDefaultTextColor(Qt.white)
            font = QFont()
            font.setPointSize(14)
            textItem.setFont(font)
            textItem.setFlag(QGraphicsTextItem.ItemIsMovable, True)
            textItem.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
            textItem.setZValue(1)

            center = view.mapToScene(view.viewport().rect().center())
            textItem.setPos(center)
            scene.addItem(textItem)

    def setFogOnMap(self):
        idx = self.currentIndex()
        if idx < 0:
            return
        
        scene = self.scenes[idx]
        view = self.views[idx]
        
        #Escolhe a densidade da névoa
        densidade, ok = QInputDialog.getInt(self, "Densidade da Névoa",
        "Digite a densidade (0-255) sendo 0 nenhuma e 255 completo:", 180, 0, 255)

        if not ok:
            return

        if self.fogItems[idx]:
            scene.removeItem(self.fogItems[idx])

        rect = scene.sceneRect()
        fog = FogItem(rect)
        fog.setDensity(densidade)
        scene.addItem(fog)
        self.fogItems[idx] = fog

    def apply_theme(self, mode):
        self.currentTheme = mode
        app = QApplication.instance()

        if mode =="dark":
            app.setStyle("Fusion")
            palette = app.palette()

            palette.setColor(QPalette.Window, QColor(45, 45, 45))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(30, 30, 30))
            palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(45, 45, 45))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Highlight, QColor(90, 120, 200))
            palette.setColor(QPalette.HighlightedText, Qt.black)

            app.setPalette(palette)
        else:
            app.setStyle("")
            app.setPalette(app.style().standardPalette())

    def clearCurrentScene(self):
        idx = self.currentIndex()
        if idx < 0:
            return
        scene = self.scenes[idx]
        mapItem = self.mapItems[idx]
        items = list(scene.items())
        for item in list(scene.items()):
            scene.removeItem(item)

        self.mapItems[idx] = None
        self.turnLists[idx].clear()
        self.fogItems[idx] = None
        #Remove Luzes relacionadas a cena
        toRemove = []
        for token, light in self.tokenLights.items():
            if light.scene() == scene:
                scene.removeItem(light)
                toRemove.append(token)
        for token in toRemove:
            self.tokenLights.pop(token)

        # Limpar luzes, réguas, etc, se implementar futuramente

    def addTurn(self, idx):
        if idx < 0:
            return
        
        lineEdit = self.nameInputs[idx]
        name = lineEdit.text().strip()

        if name:
            self.turnLists[idx].addItem(name)
            lineEdit.clear()

    def deleteSelectedTurn(self, idx):
        if idx < 0:
            return
        listWidget = self.turnLists[idx]
        for item in listWidget.selectedItems():
            row = listWidget.row(item)
            listWidget.takeItem(row)

    def keyPressEvent(self, event):
        idx = self.currentIndex()
        if idx < 0:
            return
        
        scene = self.scenes[idx]

        if event.key() == Qt.Key_Delete:
            for item in scene.selectedItems():
                if isinstance(item, TokenItem):
                    scene.removeItem(item)

            return

        step = 5
        dx = dy = 0

        if event.key() == Qt.Key_Left:
            dx = -step
        elif event.key() == Qt.Key_Right:
            dx = step
        elif event.key() == Qt.Key_Up:
            dy = -step
        elif event.key() == Qt.Key_Down:
            dy = step

        if dx != 0 or dy != 0:
            for item in scene.selectedItems():
                if isinstance(item, TokenItem):
                    item.moveBy(dx, dy)

            return

        super().keyPressEvent(event) 

    def saveSettings(self):
        data = {}
        data["theme"] = getattr(self, "currentTheme", "light")
        data["window"] = {
            "size": [self.width(), self.height()],
            "pos": [self.x(), self.y()]
        }
        scenes_data = []
        for i in range(len(self.scenes)):
            scene_info = {
                "name": self.tabs.tabText(i),
                "turns": [self.turnLists[i].item(j).text() 
                    for j in range(self.turnLists[i].count())]
            }
            scenes_data.append(scene_info)
        data["scenes"] = scenes_data
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def loadSettings(self):
        if not os.path.isfile(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        
        theme = data.get("theme", "light")
        self.apply_theme(theme)

        win = data.get("window", {})
        size = win.get("size")
        pos = win.get("pos")
        if size and len(size) == 2:
            self.resize(size[0], size[1])
        if pos and len(pos) == 2:
            self.move(pos[0], pos[1])
        
        scenes_data = data.get("scenes", [])

        self.tabs.clear()
        self.scenes = []
        self.views = []
        self.turnLists = []
        self.nameInputs = []
        self.mapItems = []
        self.fogItems = []

        for scene_info in scenes_data:
            name = scene_info.get("name", "Cena")
            self.addSceneTab(name)
            idx = self.tabs.count() - 1
            for turn in scene_info.get("turns", []):
                self.turnLists[idx].addItem(turn)

        self.initCinematicsTab()

    def closeEvent(self, event):
        self.saveSettings()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
