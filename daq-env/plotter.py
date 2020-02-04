from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import pyqtgraph as pg
import numpy as np
import design as UiTemplate
import sys
import os

class Plotter():
    def __init__(self, p_widget, temp_ref=None):
        """
            Constrói o gráfico, se temp_ref for inficado então, são colocadas
            linhas de referência para a área de acionamento das amostras
            baseado na equação t ± (0.0035 * t + 0.62), onde t = temperatura
            nominal de operação.
        """

        self.widget = p_widget
        self.widget.setLimits(xMin=0, yMin=0, yMax=500)

        self.buffer_size = 3600 # 1 hora
        self.plot_points = 600  # 10 minutos
        self.x_data = np.empty(self.buffer_size)
        self.y1_data = np.empty(self.buffer_size)
        self.y2_data = np.empty(self.buffer_size)
        self.marks_x_data = np.empty(0)
        self.marks_y_data = np.empty(0)
        
        self.curve1 = self.widget.plot(pen=pg.mkPen('#FF7043', width=2.0))
        self.curve2 = pg.PlotCurveItem(pen=pg.mkPen('#000000', width=2.0))
        self.curve3 = self.widget.plot(pen=None, symbol='o')

        # Right Y Axis ViewBox configuration
        p1 = self.widget.plotItem
        self._vb2 = pg.ViewBox()
        p1.showAxis('right')
        p1.scene().addItem(self._vb2)
        p1.getAxis('right').linkToView(self._vb2)
        self._vb2.setXLink(p1)
        self._vb2.addItem(self.curve2)
        self._updateViews()

        # Infinite lines:
        # t ± (0.0035t + 0,62) °C, t = temperatura nominal de operação
        if temp_ref is not None:
            self.setInfiniteLines(temp_ref)

        #configura o visual do gráfico
        self.widget.setAntialiasing(True)
        self.widget.setBackground('#62727b')
        
        axisPen = pg.mkPen(color='ffffff', width=2)
        self.widget.plotItem.setTitle('')
        self.widget.plotItem.setLabel(axis='left', text='Temperatura (°C)')
        self.widget.plotItem.setLabel(axis='bottom', text='Tempo (s)')
        self.widget.plotItem.setLabel(axis='right', text='Taxa de Elevação (°C/min)')
        self.widget.plotItem.getAxis('left').setPen(axisPen)
        self.widget.plotItem.getAxis('right').setPen(axisPen)
        self.widget.plotItem.getAxis('bottom').setPen(axisPen)
        self.widget.plotItem.getAxis('left').setLabel(**{'color':'#ff7043', 'font': 'bold 12px'})
        self.widget.plotItem.getAxis('right').setLabel(**{'color':'#000000', 'font': 'bold 12px'})
        self.widget.plotItem.getAxis('bottom').setLabel(**{'color':'#ffffff', 'font': 'bold 12px'})

        self._config_handlers()

    
    def addPoint(self, x, y1, y2):
        """
            Adiciona um ponto e plota a curva com os valores atualizados
        """
        # scroll array
        self.x_data[:-1]  = self.x_data[1:]
        self.y1_data[:-1] = self.y1_data[1:]
        self.y2_data[:-1] = self.y2_data[1:]
        
        # set the last index in array
        self.x_data[-1] = x
        self.y1_data[-1] = y1
        self.y2_data[-1] = y2

        # atualiza os pontos das curvas     
        self.curve1.setData(self.x_data[-self.plot_points:], self.y1_data[-self.plot_points:])
        self.curve2.setData(self.x_data[-self.plot_points:], self.y2_data[-self.plot_points:])

    def registerPoint(self, x, y):
        """
            Registra um ponto no gráfico
        """
        self.marks_x_data = np.append(self.marks_x_data, x)
        self.marks_y_data = np.append(self.marks_y_data, y)
        self.curve3.setData(self.marks_x_data, self.marks_y_data)

    def resetData(self):
        """
            Limpa todos os dados registrados e o gráfico
        """
        self.x_data = np.zeros(self.buffer_size)
        self.y1_data = np.zeros(self.buffer_size)
        self.y2_data = np.zeros(self.buffer_size)
        self.marks_x_data = np.empty(0)
        self.marks_y_data = np.empty(0)

        self.curve1.setData(self.x_data, self.y1_data)
        self.curve2.setData(self.x_data, self.y2_data) 
        self.curve3.setData(self.marks_x_data, self.marks_y_data, clear=True)
        

    def setInfiniteLines(self, temp_ref):
        
        if temp_ref == None:
            return

        t = temp_ref
        max_t = t + (0.0035 * t + 0.62)
        min_t = t - (0.0035 * t + 0.62)

        pos_max = QtCore.QPointF(0, max_t)
        pos_min = QtCore.QPointF(0, min_t)
        lbl_max = '{:.1f} ºC'.format(max_t)
        lbl_min = '{:.1f} ºC'.format(min_t)
        
        try:
            self.line_sup.setValue(pos_max)
            self.line_inf.setValue(pos_min)
            self.line_sup.label.setText(lbl_max)
            self.line_inf.label.setText(lbl_min)
            
        except:
            self.line_sup = pg.InfiniteLine(pos=pos_max, angle=0, movable=False, label=lbl_max)
            self.line_inf = pg.InfiniteLine(pos=pos_min, angle=0, movable=False, label=lbl_min)
            
            self.widget.plotItem.addItem(self.line_sup)
            self.widget.plotItem.addItem(self.line_inf)

        


    def _updateViews(self):
        self._vb2.setGeometry(self.widget.plotItem.vb.sceneBoundingRect())
        self._vb2.linkedViewChanged(self.widget.plotItem.vb, self._vb2.XAxis)

    def _config_handlers(self):
        self.widget.plotItem.vb.sigResized.connect(self._updateViews)
