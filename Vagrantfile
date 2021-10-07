# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "generic/ubuntu2004"

  config.vm.provision "file", source:"speaker/speaker.py", destination:"/tmp/bgp/"
  config.vm.provision "file", source:"speaker/receiver.py", destination:"/tmp/bgp/"
  config.vm.provision "file", source:"speaker/bgp.py", destination:"/tmp/bgp/"
  config.vm.provision "file", source:"speaker/ovsmanager.py", destination:"/tmp/bgp/"
  config.vm.provision "file", source:"speaker/requirements.txt", destination:"/tmp/bgp/"
  config.vm.provision "file", source:"speaker/speak", destination:"/tmp/bgp/"
  config.vm.provision "file", source:"speaker/receive", destination:"/tmp/bgp/"

  config.vm.provision "shell", inline: <<-SHELL
    apt-get update
    apt-get -y install openvswitch-switch python3-pip python3.8-venv
    cd /tmp/bgp && python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt
    ovs-vsctl add-br br0
  SHELL

  config.vm.define "receiver" do |rec|
    rec.vm.network :private_network, ip: "192.168.100.101"
    config.vm.provision "shell", inline: <<-SHELL
      ovs-vsctl set-manager "ptcp:6640"
      ovs-vsctl set-controller br0 tcp:127.0.0.1:6633  
      ip link set br0 up
    SHELL
  end

  config.vm.define "speaker" do |sp|
    sp.vm.network :private_network, ip: "192.168.100.102"
  end


end
