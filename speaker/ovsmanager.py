from ryu.controller.handler import set_ev_cls
from ryu.services.protocols.ovsdb import api as ovsdb
from ryu.services.protocols.ovsdb import event as ovsdb_event
from ryu.lib.ovs.bridge import OVSBridge
import ryu.ofproto.ofproto_v1_3_parser as parser
from ryu.app.ofctl import api as ofctl_api
from ryu import cfg
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types

class OvsManager():
    ovs = None
    dpid = None
    app = None

    def __init__(self, app, dpid):
        self.app = app
        self.dpid = int(dpid,16)
        self.ovs = OVSBridge(
            CONF=self.app.CONF,
            datapath_id=self.dpid,
            ovsdb_addr="tcp:127.0.0.1:6640")
        self.ovs.init()

        self.app.get_datapath(self.dpid)
        print("Connecting to local OVS")

    def add_flow(self, datapath, priority, match, instructions, table):
        mod = parser.OFPFlowMod(
            datapath=datapath,
            table_id=table,
            priority=priority,
            match=match,
            instructions=instructions)

        print("Adding flow")
        datapath.send_msg(mod)

    def clear_vxlan_tunnels(self):
        ports = list(filter(lambda x:x.startswith("evpn-"),self.ovs.get_port_name_list()))
        for p in ports:
            print(f"Deleting port {p}")
            self.ovs.del_port(p)

    def create_vxlan_tunnel(self, ip, vni):
        try:
            self.ovs.add_vxlan_port(f"evpn-{ip}:{vni}", ip, local_ip=None, key=vni, ofport=None)
        except:
            pass

    def create_mac_flow(self, ip, mac, vtep, vni):
        datapath = self.app.get_datapath(self.dpid)
        if datapath is not None:
            print("Found datapath")

        out_port = self.ovs.get_ofport(f"evpn-{vtep}:{vni}")

        match = parser.OFPMatch(metadata=(int(vni), parser.UINT64_MAX), eth_dst=mac)
        actions = [parser.OFPActionOutput(out_port)]
        instructions = [parser.OFPInstructionActions(datapath.ofproto.OFPIT_APPLY_ACTIONS, actions)]

        self.add_flow(datapath, 1, match, instructions, 0)

        # Add the ARP reply flow:
        match = parser.OFPMatch(metadata=(int(vni), parser.UINT64_MAX),
            eth_type=ether_types.ETH_TYPE_ARP,
            arp_op=arp.ARP_REQUEST,
            arp_tpa=ip)

        actions = [
            parser.NXActionRegMove(
                src_field="eth_src", dst_field="eth_dst", n_bits=48),
            parser.OFPActionSetField(eth_src=mac),
            parser.OFPActionSetField(arp_op=arp.ARP_REPLY),
            parser.NXActionRegMove(
                src_field="arp_sha", dst_field="arp_tha", n_bits=48),
            parser.NXActionRegMove(
                src_field="arp_spa", dst_field="arp_tpa", n_bits=32),
            parser.OFPActionSetField(arp_sha=mac),
            parser.OFPActionSetField(arp_spa=ip),
            parser.OFPActionOutput(datapath.ofproto.OFPP_IN_PORT)]
        instructions = [
            parser.OFPInstructionActions(
                datapath.ofproto.OFPIT_APPLY_ACTIONS, actions)]

        self.add_flow(datapath, 2, match, instructions, 1)
