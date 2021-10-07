# Intro
This is a demo application to test Ryu for EVPN support. The demo uses Vagrant to spin up 2 VMs.
On one VM is deployed a speaker that sends a fake EVPN advertisement. The other VM listens for EVPN
advertisements and creates vxlan tunnels on the local instance of OpenVSwitch and will add flows to 
send traffic that match type2 routes to the correct tunnel. A flow also gets installed to get OVS
to reply to ARP queries instead of flooding them on the tunnel.

# Pre-req
You need libvirt, kvm-qemu and vagrant to run this demo

# Usage

- vagrant up
- open 2 terminals and on the first, we will run the speaker and on the second, we'll run the receiver
- On the first terminal (speaker demo)
  - vagrant ssh speaker
  - cd /tmp/bgp && ./speak

- On the second terminal (receiver demo)
  - vagrant ssh receiver
  - cd /tmp/bgp && sudo ./receive

After both apps are running, the speaker will send a EVPN Type2 route and a Type3 route. 
The receiver will use the ovsdb API to make the changes on the local OVS. After receiving the type3 route, you can do
```
vagrant@ubuntu2004:~$ sudo ovs-vsctl show
8ee16ecd-d8c3-4eeb-b1e3-069f90c6934e
    Manager "ptcp:6640"
    Bridge br0
        Port "evpn-192.168.1.2:200"
            Interface "evpn-192.168.1.2:200"
                type: vxlan
                options: {key="200", remote_ip="192.168.1.2"}
        Port br0
            Interface br0
                type: internal
    ovs_version: "2.13.3"
```

This shows that the vxlan tunnel was successfully created based on what the speaker has advertised.

You can also dump the flow table to see the inserted MAC/IP translations. For each type2 routes advertised, you'll have 2 flows:

    - 1 for directing the packets matching this MAC to the right vxlan port
    - 1 for ARP reply

```
vagrant@ubuntu2004:~$ sudo ovs-ofctl dump-flows br0
 cookie=0x0, duration=83.827s, table=0, n_packets=0, n_bytes=0, priority=1,metadata=0xc8,dl_dst=aa:bb:cc:dd:ee:fe actions=output:"evpn-192.168.1."
 cookie=0x0, duration=83.827s, table=1, n_packets=0, n_bytes=0, priority=2,arp,metadata=0xc8,arp_tpa=192.168.242.7,arp_op=1 actions=move:NXM_OF_ETH_SRC[]->NXM_OF_ETH_DST[],mod_dl_src:aa:bb:cc:dd:ee:fe,load:0x2->NXM_OF_ARP_OP[],move:NXM_NX_ARP_SHA[]->NXM_NX_ARP_THA[],move:NXM_OF_ARP_SPA[]->NXM_OF_ARP_TPA[],load:0xaabbccddeefe->NXM_NX_ARP_SHA[],load:0xc0a8f207->NXM_OF_ARP_SPA[],IN_PORT
```
