import base64
import logging
import sys
import time

from jinja2 import Template
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("provision")

NAMESPACE = "default"
TEMPLATE_PATH = "frr.conf.j2"
POD_READY_TIMEOUT_S = 60

# Topology parameters. In a real "request a topology" flow this dict
# would be generated from user input instead of hardcoded.
ROUTERS = {
    "router-1": {"ip": "10.10.10.2/24", "router_id": "1.1.1.1"},
    "router-2": {"ip": "10.10.10.3/24", "router_id": "2.2.2.2"},
}
NETWORK_PREFIX = "10.10.10.0/24"


def wait_for_pod(v1: client.CoreV1Api, app_label: str, namespace: str, timeout_s: int) -> str:
    """Poll until a pod with the given app label is Running; return its name."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        pods = v1.list_namespaced_pod(namespace=namespace, label_selector=f"app={app_label}")
        if pods.items and pods.items[0].status.phase == "Running":
            return pods.items[0].metadata.name
        time.sleep(2)
    raise TimeoutError(f"No Running pod found for app={app_label} after {timeout_s}s")


def exec_in_pod(v1: client.CoreV1Api, pod_name: str, namespace: str, command: list[str]) -> str:
    """Run a command in a pod and return combined stdout/stderr."""
    resp = stream(
        v1.connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        command=command,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False,
    )
    return resp


def push_config(v1: client.CoreV1Api, pod_name: str, namespace: str, rendered_conf: str) -> None:
    """
    Write frr.conf into the pod and restart the daemon suite.

    The config is base64-encoded before transport so multi-line content,
    quotes, and special characters in the rendered config can never break
    the shell command that writes the file — the previous `echo '{conf}'`
    approach was one stray quote away from failing.
    """
    b64_conf = base64.b64encode(rendered_conf.encode()).decode()
    command = [
        "/bin/sh",
        "-c",
        f"echo {b64_conf} | base64 -d > /etc/frr/frr.conf && "
        f"chown frr:frr /etc/frr/frr.conf && "
        # No systemd in this container, so call frrinit.sh directly
        # rather than relying on `systemctl` to fail over.
        f"/usr/lib/frr/frrinit.sh restart",
    ]
    result = exec_in_pod(v1, pod_name, namespace, command)
    log.info("Configured %s:\n%s", pod_name, result.strip())


def main() -> int:
    """
    Configuration script for setting up OSPF routers.
    Renders per-router FRR configs from a Jinja2 template and pushes them
    into the live FRR pods via the Kubernetes exec API, then verifies the
    OSPF adjacency came up.
    """
    
    config.load_kube_config()
    v1 = client.CoreV1Api()

    with open(TEMPLATE_PATH) as f:
        template = Template(f.read())

    pod_names: dict[str, str] = {}

    for r_name, params in ROUTERS.items():
        try:
            pod_name = wait_for_pod(v1, r_name, NAMESPACE, POD_READY_TIMEOUT_S)
        except TimeoutError as exc:
            log.error("%s: %s", r_name, exc)
            return 1
        pod_names[r_name] = pod_name

        rendered_conf = template.render(
            router_name=r_name,
            ip_address=params["ip"],
            router_id=params["router_id"],
            network_prefix=NETWORK_PREFIX,
        )

        try:
            push_config(v1, pod_name, NAMESPACE, rendered_conf)
        except ApiException as exc:
            log.error("Failed to configure %s (%s): %s", r_name, pod_name, exc)
            return 1

    # Give OSPF a few seconds to exchange hellos, then verify adjacency.
    log.info("Waiting for OSPF adjacency to form...")
    time.sleep(10)
    neighbor_output = exec_in_pod(
        v1, pod_names["router-1"], NAMESPACE, ["vtysh", "-c", "show ip ospf neighbor"]
    )
    log.info("OSPF neighbor table on router-1:\n%s", neighbor_output.strip())

    if "Full" in neighbor_output:
        log.info("Adjacency is UP.")
        return 0
    log.warning("Adjacency not yet Full — check `vtysh -c 'show ip ospf interface'` on each pod.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
