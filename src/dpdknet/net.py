from dpdknet.ovs.bridge import OVSBridge

class DpdkNet:
    def __init__(self):
        pass

    def create_bridge(self, name: str, datapath: str = 'netdev') -> OVSBridge:
        """
        Create a DPDK-enabled OVS bridge with the specified name and datapath type.
        If the bridge already exists, it will not be recreated.
        """
        return OVSBridge(name, datapath)

