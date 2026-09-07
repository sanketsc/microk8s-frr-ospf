# microk8s-frr-ospf
Run OSPF between 2 FRR routers on a MicroK8s instance using Multus CNI, static IPAM, and automated Python provisioning.

A Kubernetes based network simulation platform that creates virtual network topologies using containerized routers and automates their configuration.
This project combines Kubernetes, Multus CNI, Linux networking, FRRouting (FRR), Python, and Jinja2 to build a lightweight network lab that runs entirely on a local Kubernetes cluster.

The initial implementation demonstrates two containerized routers connected through a dedicated virtual Ethernet segment and running OSPF.
