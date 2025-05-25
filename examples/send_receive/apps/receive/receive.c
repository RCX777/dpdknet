#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <string.h>

#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_lcore.h>
#include <rte_mbuf.h>

#define RX_RING_SIZE 1024
#define TX_RING_SIZE 1024

#define NUM_MBUFS 8191
#define MBUF_CACHE_SIZE 250
#define BURST_SIZE 32

static inline int
port_init(uint16_t port, struct rte_mempool *mbuf_pool)
{
    struct rte_eth_conf port_conf = {0};
    const uint16_t rx_rings = 1, tx_rings = 0;  // no TX queues needed
    uint16_t nb_rxd = RX_RING_SIZE;
    int retval;

    if (!rte_eth_dev_is_valid_port(port))
        return -1;

    retval = rte_eth_dev_configure(port, rx_rings, tx_rings, &port_conf);
    if (retval != 0)
        return retval;

    retval = rte_eth_dev_adjust_nb_rx_tx_desc(port, &nb_rxd, NULL);
    if (retval != 0)
        return retval;

    retval = rte_eth_rx_queue_setup(port, 0, nb_rxd,
        rte_eth_dev_socket_id(port), NULL, mbuf_pool);
    if (retval < 0)
        return retval;

    retval = rte_eth_dev_start(port);
    if (retval < 0)
        return retval;

    // retval = rte_eth_promiscuous_enable(port);
    // if (retval != 0)
    //     return retval;

    return 0;
}

static __rte_noreturn void
lcore_main(uint16_t port)
{
    struct rte_mbuf *bufs[BURST_SIZE];

    printf("Starting packet capture on port %u\n", port);

    for (;;) {
        const uint16_t nb_rx = rte_eth_rx_burst(port, 0, bufs, BURST_SIZE);

        if (nb_rx == 0)
            continue;

        for (uint16_t i = 0; i < nb_rx; i++) {
            struct rte_mbuf *pkt = bufs[i];
            printf("Received packet len=%u\n", rte_pktmbuf_pkt_len(pkt));
            // Add any other metadata print you want here

            // Drop packet (free mbuf)
            rte_pktmbuf_free(pkt);
        }
    }
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

    uint16_t port = 0;  // bind only to port 0
    if (port_init(port, mbuf_pool) != 0)
        rte_exit(EXIT_FAILURE, "Cannot initialize port %" PRIu16 "\n", port);

    lcore_main(port);

    rte_eal_cleanup();

    return 0;
}

