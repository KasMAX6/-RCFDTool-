# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/10 18:53
import os

import geemap
import ee


class Initializer:
    '''
    初始化类
    '''
    def __init__(self):
        os.environ['HTTP_PROXY'] = "http://127.0.0.1:7897"
        os.environ['HTTPS_PROXY'] = "http://127.0.0.1:7897"
        pass

    def initialize(self):
        '''
        初始化
        :return:
        '''

        # 服务账号邮箱（在 JSON 文件里能看到）
        service_account = "token-324@corn-427712.iam.gserviceaccount.com"
        # JSON 密钥文件路径
        key_file = r"E:\pysiderLearn\pysiderProject\flash\key\corn-427712-6bb826b25e07.json"

        # 用服务账号凭证初始化 Earth Engine
        credentials = ee.ServiceAccountCredentials(service_account, key_file)
        ee.Initialize(credentials)


        pass

if __name__ == '__main__':
    initializer = Initializer()
    initializer.initialize()