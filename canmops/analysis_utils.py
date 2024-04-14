from __future__ import division
import logging
import os
import yaml
import numpy as np
import pandas as pd
import csv
from pathlib import Path
import coloredlogs as cl
import socket
import ipaddress


class AnalysisUtils(object):
    
    def __init__(self):
        pass
    # Conversion functions    
    def save_to_h5(self,data=None, outname=None, directory=None, title = "Beamspot scan results"):
        if not os.path.exists(directory):
                os.mkdir(directory)
        filename = os.path.join(directory, outname)
        with tb.open_file(filename, "w") as out_file_h5:
            out_file_h5.create_array(out_file_h5.root, name='data', title = title, obj=data)  
    
    def open_yaml_file(self,directory=None , file=None):
        filename = os.path.join(directory, file)
        with open(filename, 'r') as ymlfile:
            cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
        return cfg
    
    def dump_yaml_file(self,directory=None , file=None, loaded = None):
        
        filename = os.path.join(directory, file)
        with open(filename, 'w') as ymlfile:
            yaml.dump(loaded, ymlfile, sort_keys=False)#default_flow_style=False
    
    def save_to_csv(self,data=None, outname=None, directory=None):
        df = pd.DataFrame(data)
        if not os.path.exists(directory):
                os.mkdir(directory)
        filename = os.path.join(directory, outname)    
        df.to_csv(filename, index=True)

    def read_csv_file(self, file=None):
        """ This function will read the data using pandas
        """
        data_file = pd.read_csv(file,encoding = 'utf-8').fillna(0)
        return data_file
                
    def open_h5_file(self,outname=None, directory=None):
        filename = os.path.join(directory, outname)
        with tb.open_file(filename, 'r') as in_file:
            data = in_file.root.data[:]
        return data
                    
    def get_subindex_description_yaml(self,dictionary = None, index =None, subindex = None):
        index_item = [dictionary[i] for i in [index] if i in dictionary]
        subindex_items = index_item[0]["subindex_items"]
        subindex_description_items = subindex_items[subindex]
        return subindex_description_items
    
    def get_info_yaml(self,dictionary = None, index =None, subindex = "description_items"):
        index_item = [dictionary[i] for i in [index] if i in dictionary]
        index_description_items = index_item[0][subindex]
        return index_description_items
                
    def get_subindex_yaml(self,dictionary = None, index =None, subindex = "subindex_items"):
        index_item = [dictionary[i] for i in [index] if i in dictionary]
        subindex_items = index_item[0][subindex]
        return subindex_items.keys()
    
    def open_csv_file(self,outputname=None, directory=None, fieldnames = ['A', 'B']):
        if not os.path.exists(directory):
            os.mkdir(directory)
        filename = os.path.join(directory, outputname) 
        
        out_file_csv = open(filename + '.csv', 'w+')
        return out_file_csv

    def build_data_base(self,fieldnames=["A","B"],outputname = False, directory = False):
        out_file_csv =self.open_csv_file(outputname=outputname, directory=directory)
        
        writer = csv.DictWriter(out_file_csv, fieldnames=fieldnames)

        writer.writeheader()    
        
        csv_writer = csv.writer(out_file_csv)  # , delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)     
           
        return csv_writer, out_file_csv 
  
    
    def get_ip_device_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
        s.close()
    
    def get_ip_from_subnet(self, ip_subnet):
        #https://realpython.com/python-ipaddress-module/
        ips= ipaddress.ip_network(ip_subnet)
        ip_list=[str(ip) for ip in ips]
        return ip_list

    