import bgp;
import eventlet
import sys
import os

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import (MAIN_DISPATCHER, CONFIG_DISPATCHER)
from ryu.controller.handler import set_ev_cls
import ryu.app.ofctl.api
from ryu.controller import dpset
from ryu.controller import dpset

class Receiver(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    bgp = None
    _CONTEXTS = {
        'dpset': dpset.DPSet,
    }

    def __init__(self, *args, **kwargs):
        super(Receiver, self).__init__(*args, **kwargs)
        self.dpset = kwargs['dpset']
        print("Waiting for OVS to establish openflow connection")

    # When the OF controller has connected to us, we will establish a BGP session
    @set_ev_cls(dpset.EventDP, dpset.DPSET_EV_DISPATCHER)
    def handler_datapath(self, ev):
        self.bgp = bgp.Bgp(self, 64512, "192.168.100.101")
        self.bgp.set_datapath_id(os.getenv("DPID"))
        self.bgp.start()

        self.bgp.add_neighbour(65001, "192.168.100.102")


    def get_datapath(self, dpid):
        return self.dpset.get(dpid)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        pass

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        print(datapath)

    def close(self):
        print("Shuting down")
        self.bgp.stop()
