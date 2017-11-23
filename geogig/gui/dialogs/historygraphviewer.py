from __future__ import division, absolute_import, unicode_literals
import collections
import itertools
import math
import re
import sys

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt import QtCore
from qgis.PyQt import QtGui
from qgis.PyQt import QtWidgets

from geogig.geogigwebapi.commitish import Commitish

class Cache(object):

    _label_font = None

    @classmethod
    def label_font(cls):
        font = cls._label_font
        if font is None:
            font = cls._label_font = QtWidgets.QApplication.font()
            font.setPointSize(6)
        return font


class Edge(QtWidgets.QGraphicsItem):
    item_type = QtWidgets.QGraphicsItem.UserType + 1

    def __init__(self, child, parent, color):

        QtWidgets.QGraphicsItem.__init__(self)

        self.setAcceptedMouseButtons(Qt.NoButton)
        self.child = child
        self.parent = parent
        self.commit = child.commit
        self.setZValue(-2)

        self.recomputeBound()

        self.pen = QtGui.QPen(color, 4.0, Qt.SolidLine, Qt.SquareCap, Qt.RoundJoin)

    def recomputeBound(self):
        dest_pt = Commit.item_bbox.center()

        self.source_pt = self.mapFromItem(self.child, dest_pt)
        self.dest_pt = self.mapFromItem(self.parent, dest_pt)
        self.line = QtCore.QLineF(self.source_pt, self.dest_pt)

        width = self.dest_pt.x() - self.source_pt.x()
        height = self.dest_pt.y() - self.source_pt.y()
        rect = QtCore.QRectF(self.source_pt, QtCore.QSizeF(width, height))
        self.bound = rect.normalized()

    # Qt overrides
    def type(self):
        return self.item_type

    def boundingRect(self):
        return self.bound

    def paint(self, painter, option, widget):
        path = QtGui.QPainterPath()
        path.moveTo(self.child.x(), self.child.y())
        if self.child.commit.isMerge():
            path.lineTo(self.parent.x(), self.child.y())
        elif self.parent.commit.isFork():
            path.lineTo(self.child.x(), self.parent.y())
        path.lineTo(self.parent.x(), self.parent.y())
        painter.setPen(self.pen)
        painter.drawPath(path)

def rgb(r, g, b):
    color = QtGui.QColor()
    color.setRgb(r, g, b)
    return color

class EdgeColor(object):
    """An edge color factory"""


    current_color_index = 0
    colors = [
                QtGui.QColor(Qt.red),
                QtGui.QColor(Qt.green),
                QtGui.QColor(Qt.blue),
                QtGui.QColor(Qt.black),
                QtGui.QColor(Qt.darkRed),
                QtGui.QColor(Qt.darkGreen),
                QtGui.QColor(Qt.darkBlue),
                QtGui.QColor(Qt.cyan),
                QtGui.QColor(Qt.magenta),
                # Orange; Qt.yellow is too low-contrast
                rgb(0xff, 0x66, 0x00),
                QtGui.QColor(Qt.gray),
                QtGui.QColor(Qt.darkCyan),
                QtGui.QColor(Qt.darkMagenta),
                QtGui.QColor(Qt.darkYellow),
                QtGui.QColor(Qt.darkGray),
             ]

    @classmethod
    def cycle(cls):
        cls.current_color_index += 1
        cls.current_color_index %= len(cls.colors)
        color = cls.colors[cls.current_color_index]
        color.setAlpha(128)
        return color

    @classmethod
    def current(cls):
        return cls.colors[cls.current_color_index]

    @classmethod
    def reset(cls):
        cls.current_color_index = 0


class Commit(QtWidgets.QGraphicsItem):
    item_type = QtWidgets.QGraphicsItem.UserType + 2
    commit_radius = 12.0
    merge_radius = 18.0

    item_shape = QtGui.QPainterPath()
    item_shape.addRect(commit_radius/-2.0,
                       commit_radius/-2.0,
                       commit_radius, commit_radius)
    item_bbox = item_shape.boundingRect()

    inner_rect = QtGui.QPainterPath()
    inner_rect.addRect(commit_radius/-2.0 + 2.0,
                       commit_radius/-2.0 + 2.0,
                       commit_radius - 4.0,
                       commit_radius - 4.0)
    inner_rect = inner_rect.boundingRect()

    commit_color = QtGui.QColor(Qt.white)
    outline_color = commit_color.darker()
    merge_color = QtGui.QColor(Qt.lightGray)

    commit_selected_color = QtGui.QColor(Qt.green)
    selected_outline_color = commit_selected_color.darker()

    commit_pen = QtGui.QPen()
    commit_pen.setWidth(1.0)
    commit_pen.setColor(outline_color)

    def __init__(self, commit,
                 selectable=QtWidgets.QGraphicsItem.ItemIsSelectable,
                 cursor=Qt.PointingHandCursor,
                 xpos=commit_radius/2.0 + 1.0,
                 cached_commit_color=commit_color,
                 cached_merge_color=merge_color):

        QtWidgets.QGraphicsItem.__init__(self)

        self.commit = commit

        self.setZValue(0)
        self.setFlag(selectable)
        self.setCursor(cursor)
        self.setToolTip(commit.commitid[:12] + ': ' + commit.message)

        if commit.tags:
            self.label = label = Label(commit)
            label.setParentItem(self)
            label.setPos(xpos + 1, -self.commit_radius/2.0)
        else:
            self.label = None

        if len(commit.parents) > 1:
            self.brush = cached_merge_color
        else:
            self.brush = cached_commit_color

        self.pressed = False
        self.dragged = False
        self.selected = False

        self.edges = {}

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
            # Broadcast selection to other widgets
            commits = [i.commit.commitid for i in self.scene().selectedItems()]
            self.scene().parent().selecting = True
            self.scene().parent().itemSelected.emit(commits)
            self.scene().parent().selecting = False
            # Cache the pen for use in paint()
            if value:
                self.brush = self.commit_selected_color
                color = self.selected_outline_color
            else:
                if len(self.commit.parents) > 1:
                    self.brush = self.merge_color
                else:
                    self.brush = self.commit_color
                color = self.outline_color
            commit_pen = QtGui.QPen()
            commit_pen.setWidth(1.0)
            commit_pen.setColor(color)
            self.commit_pen = commit_pen

        return QtWidgets.QGraphicsItem.itemChange(self, change, value)

    def type(self):
        return self.item_type

    def boundingRect(self, rect=item_bbox):
        return rect

    def shape(self):
        return self.item_shape

    def paint(self, painter, option, widget,
              cache=Cache):

        # Do not draw outside the exposed rect
        painter.setClipRect(option.exposedRect)

        # Draw ellipse
        painter.setPen(self.commit_pen)
        painter.setBrush(self.brush)
        painter.drawEllipse(self.inner_rect)

    def mousePressEvent(self, event):
        QtWidgets.QGraphicsItem.mousePressEvent(self, event)
        self.pressed = True
        self.selected = self.isSelected()

    def mouseMoveEvent(self, event):
        if self.pressed:
            self.dragged = True
        QtWidgets.QGraphicsItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        QtWidgets.QGraphicsItem.mouseReleaseEvent(self, event)
        if (not self.dragged and
                self.selected and
                event.button() == Qt.LeftButton):
            return
        self.pressed = False
        self.dragged = False


class Label(QtWidgets.QGraphicsItem):

    item_type = QtWidgets.QGraphicsItem.UserType + 3

    head_color=QtGui.QColor(Qt.green)
    other_color = QtGui.QColor(Qt.white)
    remote_color = QtGui.QColor(Qt.yellow)

    head_pen = QtGui.QPen()
    head_pen.setColor(head_color.darker().darker())
    head_pen.setWidth(1.0)

    text_pen = QtGui.QPen()
    text_pen.setColor(QtGui.QColor(Qt.darkGray))
    text_pen.setWidth(1.0)

    alpha = 180
    head_color.setAlpha(alpha)
    other_color.setAlpha(alpha)
    remote_color.setAlpha(alpha)

    border = 2
    item_spacing = 5
    text_offset = 1

    def __init__(self, commit):
        QtWidgets.QGraphicsItem.__init__(self)
        self.setZValue(-1)
        self.commit = commit

    def type(self):
        return self.item_type

    def boundingRect(self, cache=Cache):
        QPainterPath = QtGui.QPainterPath
        QRectF = QtCore.QRectF

        width = 72
        height = 18
        current_width = 0
        spacing = self.item_spacing
        border = self.border + self.text_offset  # text offset=1 in paint()

        font = cache.label_font()
        item_shape = QPainterPath()

        base_rect = QRectF(0, 0, width, height)
        base_rect = base_rect.adjusted(-border, -border, border, border)
        item_shape.addRect(base_rect)

        for tag in self.commit.tags:
            text_shape = QPainterPath()
            text_shape.addText(current_width, 0, font, tag)
            text_rect = text_shape.boundingRect()
            box_rect = text_rect.adjusted(-border, -border, border, border)
            item_shape.addRect(box_rect)
            current_width = item_shape.boundingRect().width() + spacing

        return item_shape.boundingRect()

    def paint(self, painter, option, widget, cache=Cache):
        # Draw tags and branches
        font = cache.label_font()
        painter.setFont(font)

        current_width = 0
        border = self.border
        offset = self.text_offset
        spacing = self.item_spacing
        QRectF = QtCore.QRectF

        HEAD = 'HEAD'
        remotes_prefix = 'remotes/'
        tags_prefix = 'tags/'
        heads_prefix = 'heads/'
        remotes_len = len(remotes_prefix)
        tags_len = len(tags_prefix)
        heads_len = len(heads_prefix)

        for tag in self.commit.tags:
            if tag == HEAD:
                painter.setPen(self.text_pen)
                painter.setBrush(self.remote_color)
            elif tag.startswith(remotes_prefix):
                tag = tag[remotes_len:]
                painter.setPen(self.text_pen)
                painter.setBrush(self.other_color)
            elif tag.startswith(tags_prefix):
                tag = tag[tags_len:]
                painter.setPen(self.text_pen)
                painter.setBrush(self.remote_color)
            elif tag.startswith(heads_prefix):
                tag = tag[heads_len:]
                painter.setPen(self.head_pen)
                painter.setBrush(self.head_color)
            else:
                painter.setPen(self.text_pen)
                painter.setBrush(self.other_color)

            text_rect = painter.boundingRect(
                    QRectF(current_width, 0, 0, 0), Qt.TextSingleLine, tag)
            box_rect = text_rect.adjusted(-offset, -offset, offset, offset)

            painter.drawRoundedRect(box_rect, border, border)
            painter.drawText(text_rect, Qt.TextSingleLine, tag)
            current_width += text_rect.width() + spacing


class GraphView(QtWidgets.QGraphicsView):

    x_adjust = int(Commit.commit_radius*4/3)
    y_adjust = int(Commit.commit_radius*4/3)

    x_off = -18
    y_off = -24

    itemSelected = pyqtSignal(list)
    contextMenuRequested = pyqtSignal(object)

    def __init__(self, parent):
        QtWidgets.QGraphicsView.__init__(self, parent)

        highlight = self.palette().color(QtGui.QPalette.Highlight)
        Commit.commit_selected_color = highlight
        Commit.selected_outline_color = highlight.darker()

        self.selection_list = []
        self.menu_actions = None
        self.commits = []
        self.items = {}
        self.saved_matrix = self.transform()

        self.x_start = 24
        self.x_min = 24
        self.x_offsets = collections.defaultdict(lambda: self.x_min)

        self.is_panning = False
        self.pressed = False
        self.selecting = False
        self.last_mouse = [0, 0]
        self.zoom = 2
        self.setDragMode(self.RubberBandDrag)

        scene = QtWidgets.QGraphicsScene(self)
        scene.setItemIndexMethod(QtWidgets.QGraphicsScene.NoIndex)
        self.setScene(scene)

        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setViewportUpdateMode(self.BoundingRectViewportUpdate)
        self.setCacheMode(QtWidgets.QGraphicsView.CacheBackground)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setBackgroundBrush(QtGui.QColor(Qt.white))

        self.scaleView(1.5)


    def clear(self):
        EdgeColor.reset()
        self.scene().clear()
        self.selection_list = []
        self.items.clear()
        self.x_offsets.clear()
        self.x_min = 24
        self.commits = []

    def updateTags(self, tags):
        for commit in self.commits:
            commit.tags = tags.get(commit.commitid, [])
        self.refreshGraph()

    def selectCommits(self, commits):
        if self.selecting:
            return
        self.select([commit.commitid for commit in commits])

    def select(self, oids):
        self.scene().clearSelection()
        for oid in oids:
            try:
                item = self.items[oid]
            except KeyError:
                continue
            item.setSelected(True)
            item_rect = item.sceneTransform().mapRect(item.boundingRect())
            self.ensureVisible(item_rect)

    def setInitialView(self):
        self_commits = self.commits
        self_items = self.items

        commits = self_commits[-7:]
        items = [self_items[c.commitid] for c in commits]

        selected = self.scene().selectedItems()
        if selected:
            items.extend(selected)

        self.fit_view_to_items(items)

    def fitViewToItems(self, items):
        if not items:
            rect = self.scene().itemsBoundingRect()
        else:
            x_min = y_min = sys.maxint
            x_max = y_max = -sys.maxint

            for item in items:
                pos = item.pos()
                x = pos.x()
                y = pos.y()
                x_min = min(x_min, x)
                x_max = max(x_max, x)
                y_min = min(y_min, y)
                y_max = max(y_max, y)

            rect = QtCore.QRectF(x_min, y_min,
                                 abs(x_max - x_min),
                                 abs(y_max - y_min))

        x_adjust = abs(GraphView.x_adjust)
        y_adjust = abs(GraphView.y_adjust)

        count = max(2.0, 10.0 - len(items)/2.0)
        y_offset = int(y_adjust * count)
        x_offset = int(x_adjust * count)
        rect.setX(rect.x() - x_offset//2)
        rect.setY(rect.y() - y_adjust//2)
        rect.setHeight(rect.height() + y_offset)
        rect.setWidth(rect.width() + x_offset)

        self.fitInView(rect, Qt.KeepAspectRatio)
        self.scene().invalidate()

    def saveSelection(self, event):
        if event.button() != Qt.LeftButton:
            return
        elif Qt.ShiftModifier != event.modifiers():
            return
        self.selection_list = self.scene().selectedItems()

    def restoreSelection(self, event):
        if Qt.ShiftModifier != event.modifiers():
            return
        for item in self.selection_list:
            item.setSelected(True)

    def handleEvent(self, event_handler, event):
        self.saveSelection(event)
        event_handler(self, event)
        self.restoreSelection(event)
        self.update()

    def pan(self, event):
        pos = event.pos()
        dx = pos.x() - self.mouse_start[0]
        dy = pos.y() - self.mouse_start[1]

        if dx == 0 and dy == 0:
            return

        rect = QtCore.QRect(0, 0, abs(dx), abs(dy))
        delta = self.mapToScene(rect).boundingRect()

        tx = delta.width()
        if dx < 0.0:
            tx = -tx

        ty = delta.height()
        if dy < 0.0:
            ty = -ty

        matrix = self.transform()
        matrix.reset()
        matrix *= self.saved_matrix
        matrix.translate(tx, ty)

        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setTransform(matrix)


    def wheelPan(self, event):
        """Handle mouse wheel panning."""
        unit = QtCore.QRectF(0.0, 0.0, 1.0, 1.0)
        factor = 1.0 / self.transform().mapRect(unit).width()
        tx = event.delta()
        ty = 0.0
        if event.orientation() == Qt.Vertical:
            (tx, ty) = (ty, tx)
        matrix = self.transform().translate(tx * factor, ty * factor)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setTransform(matrix)

    def scaleView(self, scale):
        factor = (self.transform()
                  .scale(scale, scale)
                  .mapRect(QtCore.QRectF(0, 0, 1, 1))
                  .width())
        if factor < 0.07 or factor > 100.0:
            return
        self.zoom = scale

        adjust_scrollbars = True
        scrollbar = self.verticalScrollBar()
        if scrollbar:
            value = scrollbar.value()
            min_ = scrollbar.minimum()
            max_ = scrollbar.maximum()
            range_ = max_ - min_
            distance = value - min_
            nonzero_range = range_ > 0.1
            if nonzero_range:
                scrolloffset = distance/range_
            else:
                adjust_scrollbars = False

        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.scale(scale, scale)

        scrollbar = self.verticalScrollBar()
        if scrollbar and adjust_scrollbars:
            min_ = scrollbar.minimum()
            max_ = scrollbar.maximum()
            range_ = max_ - min_
            value = min_ + int(float(range_) * scrolloffset)
            scrollbar.setValue(value)

    def refreshGraph(self):
        commits = self.commits
        self.clear()
        self.setCommits(commits)
        self.scene().invalidate()

    def setCommits(self, commits):
        """Traverse commits and add them to the view."""
        self.commits = commits
        scene = self.scene()
        for commit in commits:
            item = Commit(commit)
            self.items[commit.commitid] = item
            for ref in commit.tags:
                self.items[ref] = item
            scene.addItem(item)

        self.layoutCommits()
        self.link(commits)

    def link(self, commits):
        """Create edges linking commits with their parents"""
        scene = self.scene()
        linked = []
        def linkCommit(commit, color=None):
            color = color or EdgeColor.cycle()
            linked.append(commit.commitid)
            try:
                commitItem = self.items[commit.commitid]
            except KeyError:
                return
            for i, parent in enumerate(commit.parents):
                try:
                    parentItem = self.items[parent.commitid]
                    if i == 0:
                        nextColor = color
                        edge = Edge(commitItem, parentItem, color)
                    else:
                        nextColor = EdgeColor.cycle()
                        edge = Edge(commitItem, parentItem, nextColor)
                    if parent.commitid not in linked:
                        linkCommit(parent, nextColor)
                except KeyError:
                    continue
                scene.addItem(edge)
        linkCommit(commits[0])

    def layoutCommits(self):
        positions = self.positionNodes()
        for oid, (x, y) in positions.items():
            item = self.items[oid]
            pos = item.pos()
            if pos != (x, y):
                item.setPos(x, y)

    def recomputeGrid(self):
        self.commitRows = {}
        self.commitColumns = {}
        for i, commit in enumerate(self.commits):
            self.commitRows[commit.commitid] = len(self.commits) - i
        used = []
        self.maxCol = 0

        def addCommit(commit, col):
            used.append(commit.commitid)
            self.commitColumns[commit.commitid] = col
            try:
                for i, parent in enumerate(commit.parents):
                    if parent.commitid not in used:
                        if i == 0:
                            nextCol = col
                        else:
                            self.maxCol = self.maxCol + 1
                            nextCol = self.maxCol
                        addCommit(parent, nextCol)
            except:
                pass

        addCommit(self.commits[0], 0)

        cols = 0
        for i, commit in enumerate(reversed(self.commits)):
            col = self.commitColumns[commit.commitid]
            self.commitColumns[commit.commitid] = min(col, cols)

            if commit.isMerge():
                cols -= 1
            elif  commit.isFork():
                cols += 1

    def positionNodes(self):
        self.recomputeGrid()

        x_start = self.x_start
        x_min = self.x_min
        x_off = self.x_off
        y_off = self.y_off

        positions = {}

        for node in self.commits:
            try:
                col = self.commitColumns[node.commitid]
                row = self.commitRows[node.commitid]
                x_pos = x_start + col * x_off
                y_pos = y_off + row * y_off

                positions[node.commitid] = (x_pos, y_pos)
                x_min = min(x_min, x_pos)
            except:
                pass

        self.x_min = x_min

        return positions

    # Qt overrides
    def contextMenuEvent(self, event):
        self.contextMenuRequested.emit(self.mapToGlobal(event.pos()))

    def mousePressEvent(self, event):
        if event.button() == Qt.MidButton:
            pos = event.pos()
            self.mouse_start = [pos.x(), pos.y()]
            self.saved_matrix = self.transform()
            self.is_panning = True
            return
        if event.button() == Qt.RightButton:
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self.pressed = True
        self.handleEvent(QtWidgets.QGraphicsView.mousePressEvent, event)

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        if self.is_panning:
            self.pan(event)
            return
        self.last_mouse[0] = pos.x()
        self.last_mouse[1] = pos.y()
        self.handleEvent(QtWidgets.QGraphicsView.mouseMoveEvent, event)
        if self.pressed:
            self.viewport().repaint()

    def mouseReleaseEvent(self, event):
        self.pressed = False
        if event.button() == Qt.MidButton:
            self.is_panning = False
            return
        self.handle_event(QtWidgets.QGraphicsView.mouseReleaseEvent, event)
        self.selection_list = []
        self.viewport().repaint()

    def wheelEvent(self, event):
        self.wheelPan(event)

    def fitInView(self, rect, flags=Qt.IgnoreAspectRatio):
        """Override fitInView to remove unwanted margins

        https://bugreports.qt.io/browse/QTBUG-42331 - based on QT sources

        """
        if self.scene() is None or rect.isNull():
            return
        unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
        self.scale(1.0/unity.width(), 1.0/unity.height())
        view_rect = self.viewport().rect()
        scene_rect = self.transform().mapRect(rect)
        xratio = view_rect.width() / scene_rect.width()
        yratio = view_rect.height() / scene_rect.height()
        if flags == Qt.KeepAspectRatio:
            xratio = yratio = min(xratio, yratio)
        elif flags == Qt.KeepAspectRatioByExpanding:
            xratio = yratio = max(xratio, yratio)
        self.scale(xratio, yratio)
        self.centerOn(rect.center())


