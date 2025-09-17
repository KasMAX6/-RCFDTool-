# -*- coding: utf-8 -*-            
# @Author : ZXQ
# @Time : 2025/9/11 7:59
import geopandas as gpd

class VectorFile:
    def __init__(self, file_path):
        self.file_path = file_path
        self.gdf = self.__load_vector_from_file(file_path)

    def __load_vector_from_file(self, file_path):
        gdf = gpd.read_file(file_path)
        return gdf
    def geometry(self):
        return self.gdf.geometry