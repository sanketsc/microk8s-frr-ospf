# microk8s-frr-ospf

A Kubernetes based network simulation platform that creates virtual network topologies using containerized routers and automates their configuration.
This project combines **Kubernetes, MicroK8s, Multus CNI, Linux networking, FRRouting (FRR), Python, and Jinja2** to build a lightweight, programmable network lab that can run on a local Microk8s cluster.

The initial implementation demonstrates two containerized routers connected through a dedicated virtual Ethernet segment and running OSPF.

---

## Overview

Traditional network labs often require physical routers, large virtual machines, or complex virtualization platforms.

This project explores a container-native approach:

> **Use Kubernetes as the infrastructure layer for a programmable network simulation environment.**

Virtual routers run as Kubernetes Pods. Multus CNI provides additional network interfaces that represent simulated router interfaces, while FRRouting provides routing-protocol functionality.

The automation layer is designed to dynamically:

- Define a network topology
- Create the required router Pods
- Attach simulated network interfaces
- Generate router configuration using Jinja2
- Apply configuration to the routers
- Verify connectivity and routing-protocol state

The architecture is designed to evolve from a simple two-router lab into dynamically generated multi-router topologies.

---

## Current Topology

The current POC contains two FRRouting routers connected through a dedicated Linux bridge.

```text
                         MicroK8s Node
                  ┌─────────────────────────┐
                  │                         │
                  │       router-br0        │
                  │      Linux Bridge       │
                  │       /        \        │
                  │      /          \       │
                  │   net1          net1    │
                  │     │             │     │
                  │  ┌───────┐    ┌───────┐ │
                  │  │  R1   │    │  R2   │ │
                  │  │  FRR  │    │  FRR  │ │
                  │  └───────┘    └───────┘ │
                  │                         │
                  └─────────────────────────┘

                  R1: 10.10.10.2/24
                  R2: 10.10.10.3/24

                         OSPF Area 0
```
---

## OSPF Verification

Use the following commands to check the OSPF interface status and neighbor relationships.

### 1. OSPF Interface Status

```bash
microk8s kubectl exec -it deploy/router-1 -- vtysh -c "show ip ospf interface net1"
```

**Output:**
```text
% Can't open configuration file /etc/frr/vtysh.conf due to 'No such file or directory'.
net1 is up
  ifindex 3, MTU 1500 bytes, BW 10000 Mbit <UP,BROADCAST,RUNNING,MULTICAST>
  Internet Address 10.10.10.2/24, Broadcast 10.10.10.255, Area 0.0.0.0
  MTU mismatch detection: enabled
  Router ID 1.1.1.1, Network Type BROADCAST, Cost: 10
  Transmit Delay is 1 sec, State Backup, Priority 1
  Designated Router (ID) 2.2.2.2 Interface Address 10.10.10.3/24
  Backup Designated Router (ID) 1.1.1.1, Interface Address 10.10.10.2
  Multicast group memberships: OSPFAllRouters OSPFDesignatedRouters
  Timer intervals configured, Hello 10s, Dead 40s, Wait 40s, Retransmit 5
    Hello due in 8.113s
  Neighbor Count is 1, Adjacent neighbor count is 1
```

### 2. OSPF Neighbor Verification

```bash
microk8s kubectl exec -it deploy/router-1 -- vtysh -c "show ip ospf neighbor"
```

**Output:**
```text
% Can't open configuration file /etc/frr/vtysh.conf due to 'No such file or directory'.

Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL
2.2.2.2           1 Full/DR         20.012s           30.482s 10.10.10.3      net1:10.10.10.2                      0     0     0
```



