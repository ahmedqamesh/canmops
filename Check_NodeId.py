# -*- coding: utf-8 -*-
from controlServer.canWrapper   import CanWrapper
# All the can configurations of the CAN controller should be set first from $HOME/config/main_cfg.yml
def test(interface):
    wrapper.confirm_Mops()
    wrapper.stop()        

if __name__=='__main__':
    interface = "socketcan" #other options can be Kvaser or AnaGate
    #wrapper = canWrapper.CanWrapper(interface = "AnaGate")
    wrapper = CanWrapper(interface = interface)
    #wrapper =  CanWrapper(interface = "Kvaser")
    test(interface)
    
    