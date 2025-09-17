# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/10 18:53
import os
import sys
import json

import geemap
import ee

from flash.model.DataSourceConfigure import DataSourceConfigure


class Initializer:
    '''
    初始化类
    '''
    def __init__(self):
        os.environ['HTTP_PROXY'] = "http://127.0.0.1:7897"
        os.environ['HTTPS_PROXY'] = "http://127.0.0.1:7897"
        pass

    def initialize(self, data_source_configure: DataSourceConfigure):
        '''
        初始化
        :return:
        '''


        # JSON 密钥文件路径
        key_file = os.path.join(data_source_configure.data_path_config.base_path,'key')
        files = os.listdir(key_file)[0]
        key_file = os.path.join(key_file,files)
        with open(key_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        service_account = data["client_email"]

        # 用服务账号凭证初始化 Earth Engine
        credentials = ee.ServiceAccountCredentials(service_account, key_file)
        ee.Initialize(credentials)
        pass

if __name__ == '__main__':
    initializer = Initializer()
    initializer.initialize()