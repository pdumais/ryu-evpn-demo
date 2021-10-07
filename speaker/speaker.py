import bgp;
import signal
import eventlet

quit = False

def signal_handler(sig, frame):
    global quit
    quit = True


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    bgp = bgp.Bgp(None, 65001, "192.168.100.102")
    bgp.start()

    bgp.add_vtep("192.168.1.2", 200)
    bgp.add_mac("192.168.1.2", "aa:bb:cc:dd:ee:fe", "192.168.242.7" , 200)

    bgp.add_neighbour(64512, "192.168.100.101")

    print('Press Ctrl+C')
    while (not quit): 
        eventlet.sleep(1)

    bgp.stop()




