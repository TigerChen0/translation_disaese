import logging
import logging.handlers
import pandas
import pathlib

#my module
import config

#設定log的輸出
class RoLogging:
    def __init__(self):
        print('RoLogging init')
    def setfile(self,filename_str):
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        rh = logging.handlers.RotatingFileHandler(filename_str, maxBytes=10000000, backupCount=4)
        rh.setFormatter(logging.Formatter('%(asctime)s-%(levelname)s-%(message)s'))
        self.logger.addHandler(rh)

        #logging.basicConfig(filename=filename_str,format='%(asctime)s:%(levelname)s:%(message)s',level=logging.DEBUG)
        """
        logging.debug('RoLogging Debug Message Test')
        logging.info('RoLogging info Message Test')
        logging.warning('RoLogging warning Message Test')        
        logging.error('RoLogging error Message Test')        
        logging.critical('RoLogging critical Message Test')        
        """
    #設定log的輸出
    def log(self,msg,type=logging.DEBUG):
        print(msg)
        if type >= logging.DEBUG:
            self.logger.debug(msg)
        if type >= logging.INFO:
            self.logger.info(msg)
        if type >= logging.WARNING:
            self.logger.warning(msg)
        if type >= logging.ERROR:
            self.logger.error(msg)
        if type >= logging.CRITICAL:
            self.logger.critical(msg)
    #設定log的輸出,並且加上檔名
    def logf(self,file,msg,type=logging.DEBUG):
        try:
            file = pathlib.Path(file).name
            is_dataframe = isinstance(msg,pandas.DataFrame)
            if is_dataframe:
                msg = msg.to_string()
            newmsg = file+'-> '+msg
            print(newmsg)
            if type >= logging.DEBUG:
                self.logger.debug(newmsg)
            if type >= logging.INFO:
                self.logger.info(newmsg)
            if type >= logging.WARNING:
                self.logger.warning(newmsg)
            if type >= logging.ERROR:
                self.logger.error(newmsg)
            if type >= logging.CRITICAL:
                self.logger.critical(newmsg)
        except Exception as e:
            print('logf error =%s'%e)
            
#設定log的格式
m_RoLogging = RoLogging()
