# -*- python -*-
#
#       Template grapheditor definitions for MTG Edition.
#
#       Copyright 2006-2010 INRIA - CIRAD - INRA
#
#       File author(s): Daniel Barbeau <daniel.barbeau@sophia.inria.fr>
#
#       Distributed under the Cecill-C License.
#       See accompanying file LICENSE.txt or copy at
#           http://www.cecill.info/licences/Licence_CeCILL-C_V1-en.html
#
#       OpenAlea WebSite : http://openalea.gforge.inria.fr
#
###############################################################################

__license__ = "Cecill-C"
__revision__ = " $Id$ "

from random import randint as rint
from math import sin, cos, radians

from openalea.grapheditor import qt, GraphAdapterBase
from openalea.core.observer import Observed

from openalea.mtg import MTG
from openalea.mtg import algo

###############################################################
###############################################################
# -- A wrapper around mtg.MTG that implements notification -- #
###############################################################

class ObservableMTG(GraphAdapterBase, Observed):
    """An adapter to vplants.newmtg.mtg.MTG. It has the role to
    add notifications to actions performed on the underlying graph"""
    def __init__(self):
        GraphAdapterBase.__init__(self)
        Observed.__init__(self)
        self.set_graph(MTG())

    def new_vertex(self, **kwargs):
        self.graph._id += 1
        id_ = self.graph._id
        self.add_vertex(id_, **kwargs)
        return id_

    def add_vertex(self, vid, **kwargs):
        vertex_added = [vid]
        edge_added=[]
        pid = kwargs.pop("parent", None)
        edge_type = kwargs.pop("edge_type", "<")
        g = self.graph
        if pid is None:
            vid = g.add_component(g.root, component_id=vid, **kwargs)
            edge_added.append((g.root, vid))
        else:
            if edge_type in ["<", "+"]:
                vid = g.add_child(pid, child=vid,edge_type=edge_type, **kwargs)
                edge_added.append((pid, vid))
            elif edge_type == "/":
                vid = g.add_component(pid, component_id=vid, **kwargs)
                edge_added.append((pid, vid))
            else: # add a complex
                cpx_id = g.complex(pid)
                if pid in list(g.component_roots(cpx_id)):
                    g._id -= 1
                    return
                # TODO : What is the type of the edge?
                g.add_child(cpx_id, child=vid, **kwargs)
                g.add_component(vid, component_id=pid)
                edge_added.append((cpx_id, vid))
                edge_added.append((vid, pid))


        self.notify_listeners(("vertex_added", ("vertex",vid)))

        for src, tgt in edge_added:
            self.add_edge( src, tgt)

    def remove_vertex(self, vertex):
        g = self.graph
        pid = g.parent(vertex)
        children = list(g.children(vertex))
        self.remove_edge(pid,vertex)
        for cid in children:
            self.remove_edge(vertex,cid)
            self.add_edge(pid,cid)
        g.remove_vertex(vertex, reparent_child=True)
        self.notify_listeners(("vertex_removed", ("vertex",vertex)))

    def add_edge(self, src_vertex, tgt_vertex, **kwargs):
        g = self.graph
        edge = src_vertex, tgt_vertex
        self.notify_listeners(("edge_added", ("default", edge, src_vertex, tgt_vertex)))
        self.notify_listeners(("vertex_event", (src_vertex, "refresh")))
        self.notify_listeners(("vertex_event", (tgt_vertex, "refresh")))

    def remove_edge(self, src_vertex, tgt_vertex):
        edge = src_vertex, tgt_vertex
        self.notify_listeners(("edge_removed", ("default",edge)))

    # def remove_edges(self, edges):
    #     GraphAdapterBase.remove_edges(self, (e for e in edges))






##############################################
##############################################
# -- The graphical part of the MTG editor -- #
##############################################
from PyQt4 import QtGui, QtCore

class Vertex( qt.DefaultGraphicalVertex ):
    max_scale = 6

    def __init__(self, *args, **kwargs):
        qt.DefaultGraphicalVertex.__init__(self, *args, **kwargs)
        self.setFlag(QtGui.QGraphicsItem.ItemIsFocusable, True)
        self._label = QtGui.QGraphicsSimpleTextItem(self)

    def _mtg(self):
        return self.graph().graph
    mtg = property(_mtg)

    def initialise_from_model(self):
        """Responsible for building the vertex' appearance
        from the vertex model"""
        g = self.mtg

        # -- set the color based on the scale of this vertex and the HSV wheel--
        scale = g.scale(self.vertex())
        s = (scale%self.max_scale)/float(self.max_scale)
        color = QtGui.QColor.fromHsvF(s, 1,1)
        brush = QtGui.QBrush(color)
        self.setBrush(brush)
        self._label.setText(str(self.vertex()))
        self._label.setPos(self.boundingRect().center()-self._label.boundingRect().bottomRight()/2)

        # -- call to parent handles the position --
        qt.DefaultGraphicalVertex.initialise_from_model(self)
        self.setFocus()
        self.setSelected(True)

    def store_view_data(self, **kwargs):
        vid = self.vertex()
        self.mtg._add_vertex_properties(vid,kwargs)

    def get_view_data(self, key):
        vid = self.vertex()
        return self.mtg.property(key).get(vid)

    # -- Extend this if you want to handle more notifications
    # -- but be sure to call the one from the superclass too
    def notify(self, sender, event):
        """Handle notifications from the vertex model"""
        if event == "refresh":
            self.notify_position_change()
        qt.DefaultGraphicalVertex.notify(self, sender, event)

    def default_position(self):
        """If there is no position obtained by get_view_data("position"),
        use the return value from this one"""
        return [rint(0,200)]*2

    ########################################################
    # The following methods are meant to modify the model! #
    ########################################################
    def add_child(self, *args, **kwargs):
        """ This methods modifies the mtg by adding a child to this vertex.
        The view will be updated through the graph's notifications.
        """
        gm = self.graph()
        x, y = self.get_view_data("position")
        edge_type =  kwargs.get("edge_type", "<")
        if edge_type in ["+","<"]:
            y -= 40
        elif edge_type in ["\\","/"]:
            pass #y==y

        if edge_type == "<":
            n = len(algo.sons(self.mtg, self.vertex(), EdgeType="<"))
            if n > 0: #there can only be one successor
                return
        elif edge_type == "+":
            children = algo.sons(self.mtg, self.vertex(), EdgeType="+")
            n = len(children)
            n = n if n < 60/30 else n+1
            angle = -60 + n*30
            x += sin(radians(angle))*80
        elif edge_type == "/":
            x += 200
        elif edge_type == "\\":
            x -= 200

        gm.new_vertex(parent=self.vertex(), position=[x,y], edge_type=edge_type )

        # -- this is required to correctly display the edges right from the start --
        # -- it's a bug in grapheditor --
        self.notify_position_change()
        print "Vertex.add_child", x, y

    def add_component(self, *args):
        """ This methods modifies the mtg by adding a component to this vertex.
        The view will be updated through the graph's notifications.
        """
        print "called add_component"

    ##########################
    # Some Qt Event handling #
    ##########################
    def keyPressEvent(self, event):
        k = event.key()
        edge_type = "<"
        to_add = True
        if k == QtCore.Qt.Key_Less:
            edge_type="<"
            print "succesor"
        elif k == QtCore.Qt.Key_Plus :
            edge_type="+"
            print "branch"
        elif k == QtCore.Qt.Key_Slash :
            edge_type="/"
            print "component"
        elif k == QtCore.Qt.Key_Backslash :
            edge_type="\\"
            print "complex"
        elif k == QtCore.Qt.Key_Delete :
            to_add=False
        else:
            return
        event.accept()
        if to_add:
            self.add_child(edge_type=edge_type)
        else:
            self.graph().remove_vertex(self.vertex())


    def mouseDoubleClickEvent(self, event):
        self.add_child()





class MtgView( qt.View ):

    def __init__(self, parent):
        qt.View.__init__(self, parent)

        self.copyRequest.connect(self.on_copy_request)
        self.cutRequest.connect(self.on_cut_request)
        self.pasteRequest.connect(self.on_paste_request)
        self.deleteRequest.connect(self.on_delete_request)



    def on_copy_request(self, view, scene, a):
        """Implements the mtg copy operation.
        View is a subclass of QGraphicsView (MtgView in this case)
        scene is a subclass of QGraphicsScene (openalea.grapheditor.qtgraphview.Scene).
        You can copy whatever you want: vertices, edges: you handle it!
        You also handle where stuff is copied to.
        If event evaluation should stop set a.accept=True.
        """
        print "on_copy_request"

    def on_cut_request(self, view, scene, a):
        """Implements the mtg cut operation.
        View is a subclass of QGraphicsView (MtgView in this case)
        scene is a subclass of QGraphicsScene (openalea.grapheditor.qtgraphview.Scene)
        You can cut whatever you want: vertices, edges: you handle it!
        You also handle where stuff is cut to.
        If event evaluation should stop set a.accept=True.
        """
        print "on_cut_request"

    def on_paste_request(self, view, scene, a):
        """Implements the mtg paste operation.
        View is a subclass of QGraphicsView (MtgView in this case)
        scene is a subclass of QGraphicsScene (openalea.grapheditor.qtgraphview.Scene)
        You can paste whatever you want: vertices, edges: you handle it!
        You also handle where stuff is pasted from.
        If event evaluation should stop set a.accept=True.
        """
        print "on_paste_request"

    def on_delete_request(self, view, scene, a):
        """Implements the mtg delete operation.
        View is a subclass of QGraphicsView (MtgView in this case)
        scene is a subclass of QGraphicsScene (openalea.grapheditor.qtgraphview.Scene)
        You can delete whatever you want: vertices, edges: you handle it!
        If event evaluation should stop set a.accept=True.
        """
        # scene = self.scene()
        # selectedItem = scene.get_selected_items(
        # self.scene().graph().remove_vertex(
        print "on_delete_request"


    #########################
    # Handling mouse events #
    #########################
    def mouseDoubleClickEvent(self, event):
        qt.View.mouseDoubleClickEvent(self, event)
        if not event.isAccepted():
            self.dropHandler(event)

    def dropHandler(self, event):
        position = self.mapToScene(event.pos())
        position = [position.x(), position.y()]
        # -- the new_vertex call is forwarded to the graph or to the
        # -- graph_adapter if available with *args and **kwargs
        self.scene().new_vertex(position=position)

    # -- implement this to customize mouse motion handler.
    # -- !!! Be sure to call the parent's implementation somewhere inside! --
    # def mouseMoveEvent(self, e):
    #     qt.View.mouseMoveEvent(self, e)

    # -- implement this to customize mouse button right click.
    # -- !!! Be sure to call the parent's implementation somewhere inside! --
    # def contextMenuEvent(self, event):
    #     QtGui.QGraphicsView.contextMenuEvent(self, event)


def initialise_graph_view_from_model(graphView, graphModel):
    """ This method must be implemented to correctly display
    the graphModel in the graphView. This basically means
    browsing the graph structure and issuing the notifications
    that allow to build the visual representation of the graph

    If you wonder why this is not a member of MtgView:
    1) It serves to initialise the scene, not the view. The view holds the scene.
       One scene can be viewed by many views.
    2) As a consequence, it should be a method of a qtgraphview.Scene subclass
       which is not meant to be used directly but rather through the strategy business.
       It is not meant to be subclassed either, although that is possible.
    3) If one would subclass qtgraphview.Scene, that person would need to subclass
       qtgraphview.QtGraphStrategyMaker.
    In the end it's just way easier to simply implement this function and declare it
    to the QtGraphStrategyMaker contructor.
    """
    g = graphModel.graph
    gm = graphModel
    for v in g:
        gm.notify_listeners(("vertex_added", ("vertex", v)))






# -- This creates a GraphicalMtg factory, a class that creates views for MTGS --
GraphicalMtgFactory = qt.QtGraphStrategyMaker( graphView            = MtgView,
                                               vertexWidgetMap      = {"vertex":Vertex},
                                               edgeWidgetMap        = {"default":qt.DefaultGraphicalEdge,
                                                                       "floating-default":qt.DefaultGraphicalFloatingEdge},
                                               graphViewInitialiser = initialise_graph_view_from_model
                                               )






if __name__ == "__main__":
    from random import randint as rint

    #THE APPLICATION'S MAIN WINDOW
    class MainWindow(QtGui.QMainWindow):
        def __init__(self, parent=None):
            """                """
            QtGui.QMainWindow.__init__(self, parent)

            self.setMinimumSize(800,600)
            self.__graph = ObservableMTG()
            self.__graphView = GraphicalMtgFactory.create_view(self.__graph, parent=self)

            # for p in range(1):
            #     print "got here!"
            #     self.__graph.new_vertex(position=[10.0, 10.0],
            #                             color=QtGui.QColor(rint(0,255),rint(0,255),rint(0,255)))

            self.setCentralWidget(self.__graphView)


    app = QtGui.QApplication(["GraphEditor and Mtg test"])
    QtGui.QApplication.processEvents()
    w = MainWindow()
    w.show()
    app.exec_()

