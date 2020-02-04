from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import numpy as np
import design as UiTemplate
import plotter
import logger
import serial
import serial.tools.list_ports
import configparser
import sys
import os


class DAQ(UiTemplate.Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self._App = QtWidgets.QApplication(sys.argv)
        self._MainWindow = QtWidgets.QMainWindow()
        self.setupUi(self._MainWindow)

        temp_nominal = self.sb_tempNominal.value()
        self.plot_ensaio = plotter.Plotter(self.plotWidget, temp_nominal)
        self.plotWidget.plotItem.setLimits(minXRange=60, minYRange=10, maxYRange=500)
        rect = QtCore.QRectF(QtCore.QPointF(0, 500), QtCore.QPointF(3600, 0))
        self.plotWidget.plotItem.setRange(rect=rect, xRange=(0, 30), disableAutoRange=False)

        self.log = None # instancia o logger em btnSaveEnsaioHandler()

        # flags de controle
        self.aquisiting = False

        # buffers
        self.buffer_temp = None
        self.buffer_time = None

        # files
        self.logFile = None
        self.logPath = './log.txt'
        self.regFile = None
        self.regPath = './registros.txt'

        # temporizadores e timers
        self.timer_01 = QtCore.QTimer()
        self.timer_02 = QtCore.QTimer()
        self.time_01 = QtCore.QTime()
        self.time_02 = QtCore.QTime()
        self.timer_01.setTimerType(0)
        self.timer_02.setTimerType(0)

        self.plot_interval      = 1000      # plot interval in ms
        self.timer_01_interval  = 100       # timer interval in ms
        self.timer_01_counter   = 0         # timer overflow counter

        self.timer_01.start(self.timer_01_interval)

        # UI init
        self.parseStyleSheet()
        style = open('ui_style.qss').read()
        self._MainWindow.setStyleSheet(style)

        # curvas e arrays de dados
        self.t_curve = self.plotWidget.plot(pen='r')
        self.m_curve = self.plotWidget.plot(pen=None, symbol='o')
        self.m_x_data = np.empty(0)
        self.m_y_data = np.empty(0)
        
        # configs go here
        self._init_widgets()
        self._config_set_handlers()

        self._MainWindow.show()
        sys.exit(self._App.exec())


    def _init_widgets(self):
                   
        # Configurações Tab
        #######################################################################
        #                          Tab: Configurações                         #
        #######################################################################
        # Portas Seriais
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.cb_port.addItem(port.device)
            
        self.cb_baud.setCurrentIndex(4)     # Baudrates - default: 9600
        self.cb_datasize.setCurrentIndex(3) # Bits de dado - default: 8
        self.cb_parity.setCurrentIndex(2)   # Bit de paridade - default: Nenhum 
        self.cb_stopbits.setCurrentIndex(0) # Bit de parada - default: 1

        #######################################################################
        #                         Tab: Dados do Ensaio                        #
        #######################################################################
        # Diretorio do Ensaio
        path = os.path.abspath('Ensaios') 
        self.txtPastaEnsaio.setText(path)

        # Ensaio
        # inicia a pré-visualização e os botões de registro
        self.btnVisualizarHandler() 

        # Date Picker set today
        hoje = QtCore.QDate.currentDate()
        self.dateData.setDate(hoje)


    def _config_set_handlers(self):
        
        # atualiza os dados no gráfico
        self.timer_01.timeout.connect(self.timer_01Handler)
        #self.timer_02.timeout.connect(None)
        self.btn_startEnsaio.clicked.connect(self.btnStartEnsaioHandler)
        #self.btnRegistrar.clicked.connect(self.btnRegistrarHandler)
        
        # Dados do Ensaio
        self.sb_tempNominal.valueChanged.connect(self.sbTempNominalHandler)
        self.cbFaixaTemp.currentIndexChanged.connect(self.cbFaixaTempHandler)
        self.cbTipo.currentIndexChanged.connect(self.cbTipoHandler)
        self.btn_Visualizar.clicked.connect(self.btnVisualizarHandler)
        self.btnSaveEnsaio.clicked.connect(self.btnSaveEnsaioHandler)

        self.txtCliente.textChanged.connect(self.txtChangedHandler)
        self.txtOCP.textChanged.connect(self.txtChangedHandler)
        self.txtOrcamento.textChanged.connect(self.txtChangedHandler)
        self.txtTec1.textChanged.connect(self.txtChangedHandler)
        self.txtFabricante.textChanged.connect(self.txtChangedHandler)
        self.txtModelo.textChanged.connect(self.txtChangedHandler)

        # Diretorio do Ensaio
        self.btnBuscarPasta.clicked.connect(self.btnBuscarPastaHandler)

   
    def timer_01Handler(self):
        
        self.time_01 = self.time_01.addMSecs(self.timer_01_interval)

        self.buffer_temp = np.random.normal(loc=self.sb_tempNominal.value(), scale=5.0, size=1)
        self.buffer_time = self.time_01
        try:
            self.buffer_t_elev = self.plot_ensaio.y2_data[-2]
        except:
            pass        

        # plota o valor no gráfico se estiver o timer_01 atingir o valor de plot_interval
        trigger = self.plot_interval // self.timer_01_interval
        
        if self.timer_01_counter >= trigger:
            # atualiza os dados de temperatura e taxa de elevação
            x  = self.time_to_secs(self.buffer_time)
            y1 = self.buffer_temp
            y2 = (self.plot_ensaio.y1_data[-1] - self.plot_ensaio.y1_data[-2]) * 60

            # atualiza os valores na UI
            self.lblTemp.setText('{:.2f}'.format(y1[0]))
            self.lblTaxa.setText('{:.2f}'.format(y2))

            if self.aquisiting:
                # atualiza os gráficos e o tempo de ensaio
                self.lblTempo.setText(self.buffer_time.toString('hh:mm:ss'))
                self.plot_ensaio.addPoint(x, y1, y2)
                
                #formatar linha do log
                #log_text = '{} {:6.3f} {:6.3f}\n'.format(self.buffer_time.toString('hh:mm:ss'), y1[0], y2)
                #self.log.appendEnsaio(log_text)
            
            # reseta o contador de estouro do timer_01
            self.timer_01_counter = 0
        
        else:
            self.timer_01_counter += 1

    def time_to_secs(self, time:QtCore.QTime)->float:
        """
            Converte os valores de um QTime para segundos
        """
        hh = time.hour() * 3600
        mm = time.minute() * 60
        ss = time.second() 
        zz = time.msec() / 1000

        return (hh + mm + ss + zz)

    
    #===================== QPushButtons Signal Handlers ======================#

    def btnVisualizarHandler(self):
        """
            Gera uma pré-visualização de como as amostras devem ser
            acomodadas no banho de óleo baseado no número de colunas
            e linhas declarados na configuração.

        """
        total = self.sb_numAmostras.value()
        cols  = self.sb_qntCols.value()
        rows  = self.sb_qntLinhas.value()

        # Se cols * rows <= total de amostras, gera a pré-visualização
        if cols * rows <= total:

            # calcula as dimensões dos elementos da pré-visualização
            parent_height = self.layoutPreview.geometry().height()
            parent_width  = self.layoutPreview.geometry().width()
            child_height  = (parent_height // rows) * .8
            child_width   = (parent_width // cols) * .8
            child_size    = min(child_height, child_width)
            child_max_size = 60
            child_min_size = 40
            if child_size > child_max_size:
                child_height = child_width = child_max_size
            if child_size < child_min_size:
                child_height = child_width = child_min_size

            # limita o tamanho da pré-visualização a 50% do tamanho da tela
            # principal, tanto para largura como para altura
            # max_h = self._MainWindow.geometry().height() * .6
            # max_w = self._MainWindow.geometry().width() * .6
            max_h = self.layoutPreview.maximumHeight()
            max_w = self.layoutPreview.maximumWidth()

            if child_height * rows > max_h or child_width * cols > max_w:
                msg = QtWidgets.QMessageBox()
                msg.setWindowTitle("Aviso!")
                msg.setText("Tente uma disposição das amostras mais uniforme.")
                msg.exec()
                return
            
            # Deleta o Widget que esta servindo de container para o GridLayout 
            # do mapeamento
            self.layoutPreview.layout().takeAt(0).widget().deleteLater()

            previewArea = QtWidgets.QWidget()
            self.layoutPreview.layout().addWidget(previewArea)
            grid = QtWidgets.QGridLayout()
            previewArea.setLayout(grid)

            count = 1
            for r in range(rows):
                for c in range(cols):
                    lbl = QtWidgets.QLabel('{}'.format(count))
                    lbl.setObjectName('preview-lbl')
                    lbl.setAlignment(QtCore.Qt.AlignCenter)
                    
                    # utiliza a menot dimensão para formar o círculo
                    if child_width < child_height:
                        lbl.setFixedSize(child_width, child_width)
                        radius = child_width // 2
                    else:
                        lbl.setFixedSize(child_height, child_height)
                        radius = child_height // 2
                    
                    # atualiza a border-radius das labels calculadas 
                    style =  "QLabel#preview-lbl {border-radius: " + str(radius) + "px;}"
                    lbl.setStyleSheet(style)

                    grid.addWidget(lbl, r, c)
                    count += 1

            # posiciona os botoes na tela de ensaio
            try:
                # deleta o layout antigo caso exista
                self.btnsFrame.layout().takeAt(0).widget().deleteLater()
            except:
                pass

            container = QtWidgets.QWidget()
            self.btnsFrame.layout().addWidget(container)
            btns_grid = QtWidgets.QGridLayout()
            container.setLayout(btns_grid)

            parent_width  = self.btnsFrame.geometry().width()
            child_width   = parent_width // cols
            min_w = 15
            if child_width < min_w:
                child_width = min_w

            count = 1
            for r in range(rows):
                for c in range(cols):
                    btn = QtWidgets.QPushButton()
                    btn.setText('{}'.format(count))
                    btn.setObjectName('btn_' + str(count))
                    btn.setMinimumWidth(child_width)
                    btn.clicked.connect(self.btnRegistrarHandler)

                    btns_grid.addWidget(btn, r, c)
                    count += 1

        # se cols * rows > numero total de amostras alerta o usuário
        else:
            box = QtWidgets.QMessageBox()
            box.setIcon(QtWidgets.QMessageBox.Warning)
            box.setWindowTitle('Atenção!')
            box.setText("A disposição desejada não atende ao número de amostras declaras")
            box.exec_()   
 

    def btnStartEnsaioHandler(self):
        
        if self.aquisiting == False:
            
            self.aquisiting = True
            #self.logFile = open(self.logPath, 'w')

            self.lblHora.setText(QtCore.QTime.currentTime().toString())
            self.time_01 = self.time_01.fromString('00:00:00', 'hh:mm:ss')

            icon = QtGui.QIcon('imgs/16x16/restart.png')
            self.btn_startEnsaio.setIcon(icon)
            self.btn_startEnsaio.setText('Reiniciar')

        else:    
            qm = QtWidgets.QMessageBox
            msg = QtWidgets.QMessageBox()
            msg.setWindowTitle("Aviso!")
            msg.setIcon(qm.Warning)
            msg.setText("Se reiniciar o teste, será perdido todos os dados atuais. Deseja continuar?")
            msg.setStandardButtons(qm.Yes | qm.No)

            resp = msg.exec()

            if resp == qm.Yes:
                # referencia o layout que contém os botões de registro
                layout = self.btnsFrame.layout().itemAt(0).widget().layout()
                
                widgets = (layout.itemAt(i) for i in range(layout.count()))
                for w in widgets:
                    btn = w.widget()
                    btn.setEnabled(True)
                    

                # reseta gráfico e tabela            
                self.plot_ensaio.resetData()
                self.tableRegistros.clearContents()
                self.tableRegistros.setRowCount(0)
                self.aquisiting = False

                msg = qm()
                msg.setWindowTitle("Mensagem")
                msg.setText("Dados apagados!")
                msg.exec()

                icon = QtGui.QIcon('imgs/128x128/play.png')
                self.btn_startEnsaio.setIcon(icon)
                self.btn_startEnsaio.setText(' Iniciar')
    
    
    def btnRegistrarHandler(self):
        btn = self._MainWindow.sender()

        if self.aquisiting:        
            x  = self.time_to_secs(self.buffer_time)
            y1 = self.buffer_temp
            #y2 = (self.plot_ensaio.y1_data[-1] - self.plot_ensaio.y1_data[-2]) * 60
            delta = x - self.plot_ensaio.x_data[-1]
            y2 = (self.plot_ensaio.y1_data[-1] - self.plot_ensaio.y1_data[-2]) * (delta * 60)
               
            self.plot_ensaio.addPoint(x, y1, y2)
            self.plot_ensaio.registerPoint(x, y1)

            # atualiza a tabela de registros
            row = self.tableRegistros.rowCount()
            item = int(btn.objectName()[btn.objectName().rfind('_') + 1:])
            cb = QtWidgets.QComboBox()
            cb.setProperty('row', row)
            cb.setProperty('col', 3)
            cb.addItems(['Selecione','Completo', 'Parcial'])
            cb.currentIndexChanged.connect(self.tableComboBoxesHandler)

            col1 = QtWidgets.QTableWidgetItem('{:02}'.format(item))
            col2 = QtWidgets.QTableWidgetItem(self.buffer_time.toString("hh:mm:ss.z"))
            col3 = QtWidgets.QTableWidgetItem('{:.2f}'.format(self.buffer_temp[0])) 
            col4 = QtWidgets.QTableWidgetItem()

            self.tableRegistros.insertRow(row)
            self.tableRegistros.scrollToBottom()
            cols = [col1, col2, col3, col4]
            i = 0            
            for col in cols:
                col.setTextAlignment(QtCore.Qt.AlignCenter)
                col.setFlags(QtCore.Qt.ItemIsEnabled)
                self.tableRegistros.setItem(row, i, col)
                i += 1
            self.tableRegistros.setCellWidget(row, 3, cb)
        
            cb = self.tableRegistros.cellWidget(row, 3)
            cb.currentIndexChanged.connect(self.tableComboBoxesHandler)

            btn.setEnabled(False) 

    
    def btnArquivoHandler(self):

        """
        if self.logPath:    
            self.logFile = open(self.logPath, 'w')          
            self.logFile.write('{:10}\t{:10}\n'.format('Hora','Temperatura'))
            self.logFile.close()
        """
        try:
            self.logPath = QtWidgets.QFileDialog.getSaveFileName(self._MainWindow, 'Selecionar Arquivo', filter='*.txt')[0]
            self.logFile = open(self.logPath,'a+')

            if len(self.logFile.read()):
                print('arquivo ja tem dados')
        except FileExistsError:
            print('arquivo ja existe')
        except FileNotFoundError:
            print('arquivo nao encontrado')


    def btnBuscarPastaHandler(self):
        old_path = self.txtPastaEnsaio.text()
        path = QtWidgets.QFileDialog.getExistingDirectory(caption="Selecione o Diretorio", directory='Ensaios')
        
        if path != None and path != '' and path != old_path:
            self.txtPastaEnsaio.setText(path)

            # Se o diretório não estiver vazio ...
            if len(os.listdir(path)) > 0:
                file_exists = (os.path.isfile(path + '/ensaio.txt') or  
                               os.path.isfile(path + '/registros.txt'))

                if file_exists:
                    qm = QtWidgets.QMessageBox
                    reply = qm.question(self._MainWindow, 'Aviso!',
                        'Esta pasta contém arquivos. Continuar mesmo assim?')
                    
                    if reply:
                        print('sobrescrever os arquivos')
                    else:
                        msg = QtWidgets.QMessageBox()
                        msg.setWindowTitle('Mensagem')
                        msg.setText('')


    def btnSaveEnsaioHandler(self):
        """
            Valida e salva os dados do ensaio
        """
        ok = True
        mandatory_fields = [self.txtCliente, self.txtOCP, self.txtOrcamento, 
                self.txtTec1, self.txtFabricante, self.txtModelo]

        for field in mandatory_fields:
            if field.text().strip() == '':
                # adiciona a propriedade 'mandatory' caso o campo esteja vazio.
                # ela é retirada quando é inserido algum valor no campo.
                field.setProperty('mandatory', 'True')
                field.setStyle(field.style())
                ok = False

        if ok == False:    
            msg = QtWidgets.QMessageBox()
            msg.setWindowTitle('Aviso!')
            msg.setText('Os campos em <style>span {color: red; font:bold;}</style><span>vermelho</span> são obrigatórios.')
            msg.exec()

        else:            
            cliente = self.txtCliente.text()
            modelo = self.txtModelo.text()
            data = QtCore.QDate.currentDate().toString(QtCore.Qt.ISODate).replace('-','')
            hora = QtCore.QTime.currentTime().toString(QtCore.Qt.TextDate).replace(':','')

            try:

                files_path = 'Ensaios/{}/{}_{}{}/'.format(cliente, modelo, data, hora)
                os.makedirs(files_path, exist_ok=True)
                self.log = logger.Logger(directory=files_path)

                logData = \
"""
Cliente: {}
OCP: {}
Orçamento No: {}
Item No: {}
Data: {}
Técnico 1: {}
Técnico 2: {}

Fabricante: {}
Modelo: {}
Tipo elemento termossensível: {}
Letra código: {}
Temperatura de operação declarada: {}
Faixa de temperatura nominal de operação: {}
{} {}
Observações: {}

Termohigrometro: {}
Banho de óleo: {}

""".format( self.txtCliente.text(), \
            self.txtOCP.text(), \
            self.txtOrcamento.text(), \
            self.txtItem.text(), \
            self.dateData.date().toString(QtCore.Qt.SystemLocaleShortDate), \
            self.txtTec1.text(), \
            self.txtTec2.text(), \
            self.txtFabricante.text(), \
            self.txtModelo.text(), \
            self.cbTipo.currentText(), \
            self.cbLetraCod.currentText(), \
            self.sb_tempNominal.value(), \
            self.cbFaixaTemp.currentText(), \
            self.lblCores.text(), self.cbCores.currentText(), \
            self.txtObservacoes.toPlainText(), \
            self.cbTermohigrometro.currentText(), \
            self.cbBanhoOleo.currentText()
            )

                self.log.saveHeader(logData)

                self.savePreferences(files_path + 'ensaio.ld')

                with open(files_path + 'ensaio.ld', 'a') as configFile:
                    config = configparser.ConfigParser()
                    config["PATH"] = {'files': files_path}
                    config.write(configFile)


            except FileExistsError:
                print('Erro: pasta já existe')


 
    #====================== QComboBoxes Signal Handlers ======================#
    
    def cbTipoHandler(self):
        cb = self.cbTipo

        if cb.currentText() == 'Liga fusível':
            options = ['Incolor ou preta', 'Branca', 'Azul', 'Vermelha',
                        'Verde', 'Laranja', 'Outro']
            
            self.cbCores.clear()
            self.cbCores.addItems(options)
            self.lblCores.setText("Cor dos braços:")
            
        elif cb.currentText() == 'Ampola de vidro':
            options = ['Vermelha ou laranja', 'Amarela ou verde', 'Azul', 'Roxa',
                        'Preta', 'Outro']
            
            self.cbCores.clear()
            self.cbCores.addItems(options)
            self.lblCores.setText("Cor do líquido:")

        self.cbFaixaTempHandler()

    def cbFaixaTempHandler(self):
        cb = self.cbFaixaTemp
        tipo_chuveiro = self.cbTipo.currentText()
            
        if self.cbCores.currentText() == 'Outro':
            return

        if tipo_chuveiro == 'Liga fusível':
            curr_index = cb.currentIndex()

            if curr_index == 0: self.cbCores.setCurrentIndex(0)
            elif curr_index == 1: self.cbCores.setCurrentIndex(1)
            elif curr_index == 2: self.cbCores.setCurrentIndex(2)
            elif curr_index == 3: self.cbCores.setCurrentIndex(3)
            elif curr_index == 4: self.cbCores.setCurrentIndex(4)
            elif curr_index == 5 or curr_index == 6 :
                    self.cbCores.setCurrentIndex(5)

        elif tipo_chuveiro == 'Ampola de vidro':
            curr_index = cb.currentIndex()

            if curr_index == 0: self.cbCores.setCurrentIndex(0)
            elif curr_index == 1: self.cbCores.setCurrentIndex(1)
            elif curr_index == 2: self.cbCores.setCurrentIndex(2)
            elif curr_index == 3: self.cbCores.setCurrentIndex(3)
            elif curr_index >= 4 or curr_index <= 6: 
                self.cbCores.setCurrentIndex(4)

    def tableComboBoxesHandler(self):
        
        if self.aquisiting:
            cb = self._MainWindow.sender()
            row = cb.property('row')
            col = cb.property('col')

            t_registro = self.tableRegistros.item(row, 2).text() 
            t_registro = float(t_registro.replace(',','.'))
            t_nominal = self.sb_tempNominal.value()
            max_t = t_nominal + (0.0035 * t_nominal + 0.62)
            min_t = t_nominal - (0.0035 * t_nominal + 0.62)

            if t_registro >= min_t and t_registro <= max_t and cb.currentText() == 'Completo':
                res = 'Aprovado'
            else:
                res = 'Reprovado'   

            cell = QtWidgets.QTableWidgetItem(res)
            cell.setFlags(QtCore.Qt.ItemIsEnabled)
            cell.setTextAlignment(QtCore.Qt.AlignCenter)
            self.tableRegistros.setItem(row, col + 1, cell)
                
            
    #============= QSpinBoxes and QDoubleSpinBoxes Signal Handlers ===========#
    
    def sbTempNominalHandler(self):
        sb = self.sb_tempNominal
        val = sb.value()
        rng_temp = self.cbFaixaTemp

        if val >= 57 and val <= 77: rng_temp.setCurrentIndex(0)
        elif val >= 79 and val <= 107: rng_temp.setCurrentIndex(1)
        elif val >= 121 and val <= 149: rng_temp.setCurrentIndex(2)
        elif val >= 163 and val <= 191: rng_temp.setCurrentIndex(3)
        elif val >= 204 and val <= 246: rng_temp.setCurrentIndex(4)
        elif val >= 260 and val <= 302: rng_temp.setCurrentIndex(5)
        elif val >= 320 and val <= 343: rng_temp.setCurrentIndex(6)
        else: rng_temp.setCurrentIndex(7)

        self.plot_ensaio.setInfiniteLines(self.sb_tempNominal.value())

    
    #============== QLineEdit and QPlainTextEdit Signal Handlers =============#

    def txtChangedHandler(self):
        txt = self._MainWindow.sender()
        
        if txt.property('mandatory') == 'True':
            txt.setProperty('mandatory', None)
            txt.setStyleSheet("QLineEdit{border-color: #62727b;}")
            txt.setStyle(txt.style())            



    def savePreferences(self, file):
        config = configparser.ConfigParser()

        config['ID ENSAIO'] = { 'Cliente': self.txtCliente.text(),
                                'OCP': self.txtOCP.text(),
                                'Orcamento': self.txtOrcamento.text(),
                                'ItemNo': self.txtItem.text(),
                                'Data': self.dateData.date().toString(QtCore.Qt.SystemLocaleShortDate),
                                'Tecnico1': self.txtTec1.text(),
                                'Tecnico2': self.txtTec2.text()
                               }
        config['ID AMOSTRA'] = { 'Fabricante': self.txtFabricante.text(),
                                 'Modelo': self.txtModelo.text(),
                                 'Tipo_elemento_termossensivel': self.cbTipo.currentIndex(),
                                 'Letra_Cod': self.cbLetraCod.currentIndex(),
                                 'Temp_declarada': self.sb_tempNominal.value(),
                                 'Faixa_Temp': self.cbFaixaTemp.currentIndex(),
                                 'Cor': self.cbCores.currentIndex(),
                                 'Observacoes': self.txtObservacoes.toPlainText()
                                }
        config['ENSAIO'] = { 'NoAmostras': self.sb_numAmostras.value(),
                             'NoLinhas': self.sb_qntLinhas.value(),
                             'NoColunas': self.sb_qntCols.value() 
                            }
        config['SERIAL'] = { 'Porta': self.cb_port.currentIndex(),
                             'Baud': self.cb_baud.currentIndex(),
                             'Data': self.cb_datasize.currentIndex(),
                             'Parity': self.cb_parity.currentIndex(),
                             'Stop': self.cb_stopbits.currentIndex()
                            }

        # salva os dados no arquivo 'file'.ini                      
        with open(file, 'w') as configFile:
            config.write(configFile)


    def parseStyleSheet(self):    

        #paleta de cores:
        _p_base     = '#37474f'
        _p_dark     = '#102027'
        _p_light    = '#62727b'
        _p_text     = '#ffffff'
        _s_base     = '#ff7043'
        _s_dark     = '#c63f17' 
        _s_light    = '#ffa270'
        _s_text     = '#000000'

        with open('ui_style.qss', 'w') as new_file:
            with open('style.qss', 'r') as old_file:
                for line in old_file: 
                    if line.find('@p_base') != -1:
                        new_file.write(line.replace('@p_base', _p_base))
                    elif line.find('@p_dark') != -1:
                        new_file.write(line.replace('@p_dark', _p_dark))
                    elif line.find('@p_light') != -1:
                        new_file.write(line.replace('@p_light', _p_light))
                    elif line.find('@s_base') != -1:
                        new_file.write(line.replace('@s_base', _s_base))
                    elif line.find('@s_dark') != -1:
                        new_file.write(line.replace('@s_dark', _s_dark))
                    elif line.find('@s_light') != -1:
                        new_file.write(line.replace('@s_light', _s_light))
                    elif line.find('@p_text') != -1:
                        new_file.write(line.replace('@p_text', _p_text))
                    elif line.find('@s_text') != -1:
                        new_file.write(line.replace('@s_text', _s_text))
                    else:
                        new_file.write(line)
        
        new_file.close()
        old_file.close()
        


if __name__ == '__main__':
    daq = DAQ()
    