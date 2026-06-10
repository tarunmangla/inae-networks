"""
firewall.py - a learning switch with a simple firewall policy.

It behaves like a normal L2 learning switch (learns MAC->port, installs
forwarding flows) BUT also installs high-priority "drop" rules that block
ICMP between a configured pair of hosts.

Policy below blocks ping between h1 (10.0.0.1) and h3 (10.0.0.3), both ways.
h1<->h2 and h2<->h3 stay fully reachable.

Flow priorities:
  100  firewall drop rules   (checked first)
    1  learned forwarding    (normal traffic)
    0  table-miss -> controller
"""
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types


class Firewall(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # Pairs of IPs whose ICMP traffic should be dropped (both directions).
    BLOCK_ICMP = [("10.0.0.1", "10.0.0.3")]

    def __init__(self, *args, **kwargs):
        super(Firewall, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    def add_flow(self, dp, priority, match, actions, idle=0):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        # An empty action list means "drop".
        if actions:
            inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        else:
            inst = []
        mod = parser.OFPFlowMod(datapath=dp, priority=priority, match=match,
                                instructions=inst, idle_timeout=idle)
        dp.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features_handler(self, ev):
        dp = ev.msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        # Table-miss -> controller.
        self.add_flow(dp, 0, parser.OFPMatch(),
                      [parser.OFPActionOutput(ofp.OFPP_CONTROLLER,
                                              ofp.OFPCML_NO_BUFFER)])

        # Install firewall drop rules. eth_type=0x0800 is IPv4, ip_proto=1 ICMP.
        for a, b in self.BLOCK_ICMP:
            for src, dst in ((a, b), (b, a)):
                match = parser.OFPMatch(eth_type=0x0800, ip_proto=1,
                                        ipv4_src=src, ipv4_dst=dst)
                self.add_flow(dp, 100, match, [])  # drop
                self.logger.info("FIREWALL drop ICMP %s -> %s", src, dst)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return  # ignore link-discovery noise

        dpid = dp.id
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][eth.src] = in_port  # learn

        out_port = self.mac_to_port[dpid].get(eth.dst, ofp.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]

        # If we know the destination port, install a forwarding flow so the
        # controller stops seeing these packets.
        if out_port != ofp.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port,
                                    eth_src=eth.src, eth_dst=eth.dst)
            self.add_flow(dp, 1, match, actions, idle=30)

        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        out = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        dp.send_msg(out)
