from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QFileDialog, QVBoxLayout, QWidget, QListWidget, QLineEdit, QLabel, QPushButton, QSplitter, QTabWidget, QColorDialog, 
QInputDialog, QGraphicsTextItem, QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsSimpleTextItem)

from PyQt5.QtGui import (QPixmap, QPainter, QPainterPath, QPen, QColor, QBrush, QFont, QRadialGradient)
from PyQt5.QtCore import Qt, QRectF, QPoint, QPointF, QSizeF
import sys, math

class MapGraphicView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self._zoom = 0
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
        gradient = QRadialGradient(0, 0, radius)
        gradient.setColorAt(0, QColor(255, 255, 200, 180))
        gradient.setColorAt(1, QColor(0, 0, 0, 0))
        self.setBrush(QBrush(gradient))
        self.setPos(center)
        self.setZValue(2)
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, False)
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable, False)

class LightCone(QGraphicsEllipseItem):
    def __init__(self, radius, center, angle=90):
        super().__init__(-radius, -radius, radius*2, radius*2)
        self.radius = radius
        self.angle = angle
        self.rotation_angle = 0
        self.setPos(center)
        self.setZValue(2)
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, False)
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable, False)

    def setRotationAngle(self, angle):
        self.rotation_angle = angle
        self.update()

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)

        center = QPointF(self.boundingRect().center())
        half_angle = self.angle / 2 * math.pi / 180
        dir_rad = self.rotation_angle * math.pi / 180

        path = QPainterPath()
        path.moveTo(center)

        #Ponto 1 (Esquerda)
        p1 = QPointF(
            center.x() + self.radius * math.cos(dir_rad - half_angle),
            center.y() + self.radius * math.sin(dir_rad - half_angle)
        )
        path.lineTo(p1)

        #Arco do Cone
        arc_rect = QRectF(center, QSizeF(self.radius* 1.8, self.radius* 1.8))
        start_angle = (self.rotation_angle + self.angle/2) * 180 / math.pi
        path.arcTo(arc_rect, start_angle, self.angle)

        #Ponto 2 (Direita)
        p2 = QPointF(
            center.x() + self.radius * math.cos(dir_rad + half_angle),
            center.y() + self.radius * math.sin(dir_rad + half_angle)
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

class RulerItem(QGraphicsLineItem):
    def __init__(self, start, end, text):
        super().__init__(start.x(), start.y(), end.x(), end.y())
        self.setPen(QPen(Qt.yellow, 2))
        self.textItem = QGraphicsSimpleTextItem(text, self)
        self.textItem.setBrush(QBrush(Qt.white))
        mid = QPointF((start.x() + end.x()) / 2, (start.y() + end.y()) / 2)
        self.textItem.setPos(mid)
        self.setZValue(1)

class TokenItem(QGraphicsPixmapItem):

    def __init__(self, pixmap, border_color=Qt.green, callback=None):
        super().__init__(pixmap)
        self.callback = callback

        self.setFlag(QGraphicsPixmapItem.ItemIsMovable, True)
        self.setFlag(QGraphicsPixmapItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsPixmapItem.ItemSendsScenePositionChanges, True)
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

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.South)
        self.setCentralWidget(self.tabs)

        self.scenes = []
        self.views = []
        self.turnLists = []
        self.nameInputs = []
        self.mapItems = []
        self.fogItems = []
        self.tokenLights = {}

        self.initMenu()
        self.addSceneTab("Cena 1")
    
    def addSceneTab(self, name=None):
        if name is None:
            self.sceneCounter += 1
            name = f'Cena {self.sceneCounter}'

        scene = QGraphicsScene(self)
        view = MapGraphicView(scene)

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

        tokenMenu = menu.addMenu("Tokens")
        openTokenAction = tokenMenu.addAction("Add Player Token")
        openTokenAction.triggered.connect(self.openTokenImage)

        textMenu = menu.addMenu("Texto")
        addTextAction = textMenu.addAction("Adicionar Texto")
        addTextAction.triggered.connect(self.addTextOnMap)

        fogMenu = menu.addMenu("Névoa")
        addFogAction = fogMenu.addAction("Adicionar Névoa")
        addFogAction.triggered.connect(self.setFogOnMap)

        functionsMenu = menu.addMenu("Funções")
        self.rubberBandAction = functionsMenu.addAction("Seleção Multipla")
        self.rubberBandAction.setCheckable(True)
        self.rubberBandAction.setChecked(False)
        self.rubberBandAction.triggered.connect(self.toggleRubberBandMode)

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

        radius, ok = QInputDialog.getInt(self, "Raio de Visão", "Defina o raio de visão: ", 100, 10, 600)

        if not ok:
            return
        
        #Seleção: Circulo ou Cone
        light_type, ok = QInputDialog.getItem(self, "Tipo de Visão",
        "Ecolha o tipo de visão:", ["Círculo(360°)", "Cone Rotacionável"], 0, False)
        if not ok:
            return

        #Remove Visão antiga se houver
        if token in self.tokenLights:
            light = self.tokenLights.pop(token)
            light.setParentItem(None)
            self.scenes[self.currentIndex()].removeItem(light)

        if light_type == "Círculo(360°)":
            light = LightItem(radius, QPointF(0, 0))
        else:
            # CONE - pede ângulo + rotação inicial
            angle, ok2 = QInputDialog.getInt(self, "Ângulo do Cone", "Ângulo Fixo (60-120°): ", 90, 60, 120)
            if not ok2: return
            rotation, ok3 = QInputDialog.getInt(self, "Rotação Cone", "Rotação Inicial (0 = Norte 90 = Leste): ", 0, 0, 359)
            if not ok3: return
            light = LightCone(radius, QPointF(0, 0), angle)
            light.setRotationAngle(rotation)

        light.setParentItem(token)
        light.setPos(token.boundingRect().center())
        self.tokenLights[token] = light

        if token in self.tokenLights and isinstance(self.tokenLights[token], LightCone):
            current_light = self.tokenLights[token]
            new_rotation, ok = QInputDialog.getInt(self, "Ajustar Rotação do Cone",
            f"Rotação Atual: {current_light.rotation_angle}°\nNovo valor (0-359°): ",
            current_light.rotation_angle, 0, 359)

            if ok:
                current_light.setRotationAngle(new_rotation)

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

    def clearCurrentScene(self):
        idx = self.currentIndex()
        if idx < 0:
            return
        scene = self.scenes[idx]
        mapItem = self.mapItems[idx]
        items = list(scene.items())
        for item in items:
            if item != mapItem:
                scene.removeItem(item)
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
