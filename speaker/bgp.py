import eventlet

from ovsmanager import OvsManager
from ryu.lib.packet.bgp import ( EvpnNLRI )
from ryu.services.protocols.bgp.bgpspeaker import (BGPSpeaker,
                                                  EvpnPath,
                                                  EVPN_MULTICAST_ETAG_ROUTE,
                                                  EVPN_MAC_IP_ADV_ROUTE,
                                                  RF_L2_EVPN,
                                                  PMSI_TYPE_INGRESS_REP)



class Bgp:
    speaker = None
    local_as = None
    local_id = None
    ready = False
    vteps = []
    macs = []
    ovs = None
    datapath_id = None
    app = None

    def __init__(self, app, local_as, local_id):
        eventlet.monkey_patch()
        self.app = app
        self.local_as = local_as
        self.local_id = local_id

    def set_datapath_id(self, dpid):
        self.datapath_id = dpid.strip("\"");
        self.ovs = OvsManager(self.app, self.datapath_id)

    def on_best_path_change(self, ev):
        if not isinstance(ev.path, EvpnPath):
            return

        if ev.path.nlri.type == EvpnNLRI.MAC_IP_ADVERTISEMENT:
            ip = ev.path.nlri.ip_addr
            mac = ev.path.nlri.mac_addr
            [vtep_addr, vni] = ev.path.nlri.route_dist.split(':')
            
            print(f"Got Route type 2 advertisement for {mac}={ip} -> {vtep_addr}:{vni}")
            if self.ovs is not None:
                self.ovs.create_mac_flow(ip, mac, vtep_addr, vni)

        elif ev.path.nlri.type == EvpnNLRI.INCLUSIVE_MULTICAST_ETHERNET_TAG:
            [vtep_addr, vni] = ev.path.nlri.route_dist.split(':')
            print(f"Got Route type 3 advertisement for vtep {vtep_addr}, vni={vni}")

            if self.ovs is not None:
                self.ovs.create_vxlan_tunnel(vtep_addr, vni)

    def on_peer_down(self, remote_ip, remote_as):
        print("Peer down:", remote_ip, remote_as)

    def on_peer_up(self, remote_ip, remote_as):
        print("Peer up:", remote_ip, remote_as)

        self.send_config(remote_ip, remote_as)

    def add_vtep(self, vtep, vni):
        self.vteps.append({'vtep': vtep, 'vni': vni})

        rd = vtep+':'+str(vni)
        self.speaker.vrf_add(route_dist=rd, import_rts=[rd], export_rts=[rd], route_family='evpn')

    def add_mac(self, vtep, mac, ip, vni):
        if len(list(filter(lambda v: v['vni'] == vni, self.vteps))) > 0:
            self.macs.append({'vtep': vtep, 'vni': vni, 'mac': mac, 'ip': ip})
        else:
            print("Can't add this MAC, vrf doesn't exist")


    def send_config(self, remote_ip, remote_as):
        for vtep in self.vteps:
            self.send_vtep_route(vtep['vtep'], vtep['vni'])

        for mac in self.macs:
            self.send_mac_route(mac['vtep'], mac['mac'], mac['ip'], mac['vni'])


    # Route type 2: MAC/IP Advertisement Route
    def send_mac_route(self, vtep_ip, mac, ip, vni):
       self.speaker.evpn_prefix_add(
           route_type=EVPN_MAC_IP_ADV_ROUTE, 
           route_dist=vtep_ip+":"+str(vni),
           #esi=0, # Single homed
           ethernet_tag_id=0,
           mac_addr=mac,
           ip_addr=ip,
           next_hop=vtep_ip,
           tunnel_type='vxlan',
           vni=vni,
           gw_ip_addr=vtep_ip
       )

    # Route type 3: Inclusive Multicast Ethernet Tag Route
    def send_vtep_route(self, vtep_ip, vni ):
       self.speaker.evpn_prefix_add(
           route_type=EVPN_MULTICAST_ETAG_ROUTE,
           route_dist=vtep_ip+":"+str(vni),
           ethernet_tag_id=0,
           ip_addr=vtep_ip,
           tunnel_type='vxlan',
           vni=vni, 
           gw_ip_addr=vtep_ip,
           next_hop=vtep_ip
       )

    def start(self):
        self.speaker = BGPSpeaker(as_number=self.local_as, router_id=self.local_id,
                            peer_up_handler=self.on_peer_up,
                            best_path_change_handler=self.on_best_path_change,
                            peer_down_handler=self.on_peer_down)

    def add_neighbour(self, remote_as, ip):
        self.speaker.neighbor_add(ip, remote_as, local_as=self.local_as, enable_evpn=True, enable_ipv4=False)

    def stop(self):
        if self.ovs is not None:
            self.ovs.clear_vxlan_tunnels()
        self.speaker.shutdown()



