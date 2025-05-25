#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_mbuf.h>
#include <rte_lcore.h>

#define NUM_MBUFS 8191
#define MBUF_CACHE_SIZE 250
#define BURST_SIZE 1

#define DUMMY_PKT_SIZE 64

static inline int
port_init(uint16_t port, struct rte_mempool *mbuf_pool)
{
    struct rte_eth_conf port_conf = {0};
    const uint16_t rx_rings = 0, tx_rings = 1;  // only TX queue needed
    uint16_t nb_txd = 1024;
    int retval;

    if (!rte_eth_dev_is_valid_port(port))
        return -1;

    retval = rte_eth_dev_configure(port, rx_rings, tx_rings, &port_conf);
    if (retval != 0)
        return retval;

    retval = rte_eth_dev_adjust_nb_rx_tx_desc(port, NULL, &nb_txd);
    if (retval != 0)
        return retval;

    // No RX queue setup since rx_rings=0

    struct rte_eth_txconf txconf;
    struct rte_eth_dev_info dev_info;
    rte_eth_dev_info_get(port, &dev_info);
    txconf = dev_info.default_txconf;
    txconf.offloads = 0;

    retval = rte_eth_tx_queue_setup(port, 0, nb_txd,
                                   rte_eth_dev_socket_id(port), &txconf);
    if (retval < 0)
        return retval;

    retval = rte_eth_dev_start(port);
    if (retval < 0)
        return retval;

    return 0;
}

int main(int argc, char **argv)
{
    int ret = rte_eal_init(argc, argv);
    if (ret < 0)
        rte_exit(EXIT_FAILURE, "Failed to initialize EAL\n");

    argc -= ret;
    argv += ret;

    unsigned nb_ports = rte_eth_dev_count_avail();
    if (nb_ports < 1)
        rte_exit(EXIT_FAILURE, "No available ports\n");

    struct rte_mempool *mbuf_pool = rte_pktmbuf_pool_create("MBUF_POOL",
        NUM_MBUFS, MBUF_CACHE_SIZE, 0, RTE_MBUF_DEFAULT_BUF_SIZE, rte_socket_id());

    if (mbuf_pool == NULL)
        rte_exit(EXIT_FAILURE, "Cannot create mbuf pool\n");

    uint16_t port = 0;
    if (port_init(port, mbuf_pool) != 0)
        rte_exit(EXIT_FAILURE, "Cannot initialize port %" PRIu16 "\n", port);

    printf("Sending dummy packets on port %u every second...\n", port);

    while (1) {
        struct rte_mbuf *pkt = rte_pktmbuf_alloc(mbuf_pool);
        if (pkt == NULL) {
            printf("Failed to allocate mbuf\n");
            sleep(1);
            continue;
        }

        // Initialize packet data to dummy values
        char *pkt_data = rte_pktmbuf_mtod(pkt, char *);
        memset(pkt_data, 0xAB, DUMMY_PKT_SIZE);  // fill with 0xAB

        pkt->data_len = DUMMY_PKT_SIZE;
        pkt->pkt_len = DUMMY_PKT_SIZE;

        // Send packet
        uint16_t nb_tx = rte_eth_tx_burst(port, 0, &pkt, 1);
        if (nb_tx < 1) {
            // Packet not sent, free it
            rte_pktmbuf_free(pkt);
            printf("Failed to send packet: %s\n", strerror(-nb_tx));
        } else {
            printf("Sent dummy packet of size %d bytes\n", DUMMY_PKT_SIZE);
        }

        sleep(1);  // wait 1 second before sending next packet
    }

    rte_eal_cleanup();

    return 0;
}

