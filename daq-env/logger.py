class Logger():
    
    def __init__(self, ensaio='ensaio.txt', registros='registros.txt', directory=None):
        
        if directory == None:
            self._logEnsaio = ensaio
            self._logRegistros = registros
        else:
            self._logEnsaio = directory + ensaio
            self._logRegistros = directory + registros

        with open(self._logEnsaio, 'w'):
            pass
        
        with open(self._logRegistros, 'w'):
            pass


    def saveHeader(self, header_text):
        with open(self._logEnsaio, 'w') as f:
            f.write(header_text)
        
        with open(self._logRegistros, 'w') as f:
            f.write(header_text)
    

    def appendEnsaio(self, line):
        """
        Adiciona um registro ao arquivo de log do ensaio
        """
        with open(self._logEnsaio, 'a') as f:
            f.write(line)


    def appendRegistro(self):
        """
        Adiciona um evento de rompimento ao arquivo de
        """
        pass


    def setDirectory(self, dirPath):
        """
        Indica em qual diretório os arquivos devem ser armazenados
        """
        self.directory = dirPath
        self._logEnsaio = self.directory + '/' + self._logEnsaio
        self._logEnsaio = self.directory + '/' + self._logRegistros
    