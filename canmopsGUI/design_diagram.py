#!/usr/bin/env python
import sys
import yaml
import string
import logging
import os
from graphviz import Source
from QGraphViz.QGraphViz import QGraphViz, QGraphVizManipulationMode
from QGraphViz.DotParser import Graph, GraphType
from QGraphViz.Engines import Dot
rootdir = os.path.dirname(os.path.abspath(__file__)) 
lib_dir = rootdir[:-11]
config_dir = "config_files/"
class DesignDiagram(object):  

    def __init__(self, file_path = None, file_name = None):
       super().__init__()
       if sys.platform == 'win32':
        full_path =file_path+"\\"+file_name
       else:
        full_path =file_path+"/"+file_name 
       self.output_file = open(full_path+".dot","w+")
       self.uniq_id = 1
       
    def create_visualization(self,path =None, file_name =None):
       if sys.platform == 'win32':
        full_path =path+"\\"+file_name
        del_command = "del "
       else:
        full_path =path+"/"+file_name 
        del_command = "rm "
        with open(full_path+".dot") as f:
            dot_graph = f.read()
        graph=Source(dot_graph)
        graph.render(full_path,format = 'png', view=False)
        os.system(del_command+full_path+'.dot')
        os.system(del_command+full_path)
        return full_path+'.png'
    
    def output_to_dot (self,s):
        self.output_file.write(s)
        
    def getID(self):
        n = str(self.uniq_id)
        self.uniq_id += 1
        return n
    
    def asAttr(self,attr, val, id_name =None,child = None, edges = None):
        escaped = str.replace(val, '\"', '\\\"')  # " -> \"
        #if id_name == str(1): 
        if edges: 
            output_style ="["+attr+"""=<<table border="2" cellborder="0" cellspacing="-3">
                                   <tr><td bgcolor="lightblue"><font color="black"><font point-size='20'>   <br/>%s <br/> </font></font></td></tr></table>>]"""%(escaped)
        else:
            output_style = " [" + attr + "=\"" + escaped + "\"]"
        return output_style
    
    
    def map_render(self,ast, id_name=None):
        if id_name is None:
            id_name = self.getID()
        lab = ""
        edges = []  # (from, to, attr)
        #Every Crate is a dict
        if type(ast) is dict:
            for key,val in ast.items():
                child = self.getID()
                # Every CIC will have an Idname = 1
                label_attribute = self.asAttr(attr = "label",  val = key,id_name = id_name, child = child)
                if type(val) is dict:
                    #Node definition
                    edges.append((id_name, child, label_attribute))
                    
                    self.map_render(val, child)
                
                #Opcua_mops will never enter this since there are no lists
                elif type(val) is list:
                    last = None
                    for i in val:
                        child = self.getID()
                        edges.append((id_name, child, label_attribute))
                        self.map_render(i, child)
                        if last is not None:
                            edges.append((last, child, label_attribute))
                        last = child
                else:
                    # value here equals Temperature, Voltage, EOS humidity sensor
                    lab += (str(key) + ": " + str(val) + "\\n")
        else:       
            lab += str(ast)
        # output vertex
        self.output_to_dot(id_name + self.asAttr(attr ="label", val = lab, edges = None))
    
        # output edges    
        for (src, dest, attr) in edges:
            if src == str(1):
                style = "[color=grey penwidth=3 arrowhead=diamond]"
            else:
                style = "[color=grey penwidth=3 arrowhead=normal]"
            self.output_to_dot(src + " -> " + dest +style+ attr + ";\n")
            

    def process_yaml(self,path = None, file_name = None, graphid_name= None, file_end = ".yaml"):
        if sys.platform == 'win32':
            full_path =path+"\\"+file_name+file_end
        else:
           full_path =path+"/"+file_name+file_end 
        if file_name is not None:
            with open(full_path, 'r') as stream:
                ast = yaml.safe_load(stream)
                self.output_to_dot ("digraph graphid_name {\n")
                self.map_render(ast)
                self.output_to_dot ("}\n")
                self.output_file.close()
                graph = self.create_visualization(path =path, file_name = file_name)
            return graph
        else:
            pass
if   __name__  == "__main__":
    #test_file = "/home/dcs/git/canmops/config/opcua_config.yaml"
    test_file = os.path.join(lib_dir+"/"+config_dir, "opcua_config.yaml")
    file_name = os.path.basename(test_file)
    file_path= file_path = os.path.dirname(os.path.realpath(test_file))
    design = DesignDiagram(file_path =file_path, file_name = file_name[:-5])
    design.process_yaml(path=file_path,file_name =file_name[:-5],graphid_name = "MopsHub",file_end = ".yaml")

    
    
    