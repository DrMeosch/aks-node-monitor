from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

import os
import requests
import time

# https://github.com/kubernetes-client/python/blob/master/examples/in_cluster_config.py
config.load_incluster_config()

# delete pvc in this namespace
MONITOR_NAMESPACE = ["splunk"]


def main():

    while True:
        # add polling for scheduled events here
        # to improve the performance

        try:
            v1 = client.CoreV1Api()
            events = v1.list_event_for_all_namespaces(watch=False)
            events = [
                event
                for event in events.items
                if event.type == "Warning" and event.reason == "PreemptScheduled"
            ]
            nodes = v1.list_node(watch=False)
            nodes = [node.metadata.name for node in nodes.items]
        except requests.RequestException as err:
            print(f"Error performing request: {err}")
            time.sleep(0.1)
            continue

        for event in events:
            if event.involved_object.kind == "Node":
                node_name = event.involved_object.name
                if node_name in nodes:
                    print("Preempt event found for node: {}".format(node_name))
                    # cordoning the node
                    body = client.V1Node(spec=client.V1NodeSpec(unschedulable=True))
                    v1.patch_node(node_name, body)
                    print("Node successfully cordoned: {}".format(node_name))

                    # deleting pods on the node
                    try:
                        pods = v1.list_pod_for_all_namespaces(watch=False)
                    except ApiException as e:
                        print(f"Error: {e}")

                    for pod in pods.items:
                        if (
                            pod.spec.node_name == node_name
                            and pod.metadata.owner_references[0].kind != "DaemonSet"
                        ):
                            volumes = pod.spec.volumes
                            try:
                                v1.delete_namespaced_pod(
                                    pod.metadata.name, pod.metadata.namespace
                                )
                            except ApiException as e:
                                print(f"Error deleting pod {pod.metadata.name}: {e}")
                            else:
                                print(
                                    "Pod on node successfully deleted: {}".format(
                                        pod.metadata.name
                                    )
                                )
                            for volume in volumes:
                                if (
                                    volume.persistent_volume_claim is not None
                                    and pod.metadata.namespace in MONITOR_NAMESPACE
                                ):
                                    pvc_name = volume.persistent_volume_claim.claim_name
                                    try:
                                        v1.delete_namespaced_persistent_volume_claim(
                                            pvc_name, pod.metadata.namespace
                                        )
                                        print(
                                            "Pod PVCs on node successfully deleted: {}".format(
                                                pvc_name
                                            )
                                        )
                                    except ApiException as e:
                                        print(f"Error: {e}")

                    try:
                        pvs = v1.list_persistent_volume(watch=False)
                    except ApiException as e:
                        print(f"Error: {e}")
                    # deleting PVs on the node
                    for pv in pvs.items:
                        if not pv.metadata.name.startswith("local-pv-"):
                            continue
                        if (
                            pv.spec.node_affinity
                            and pv.spec.node_affinity.required.node_selector_terms
                        ):
                            for (
                                term
                            ) in pv.spec.node_affinity.required.node_selector_terms:
                                for expr in term.match_expressions:
                                    if (
                                        expr.key == "kubernetes.io/hostname"
                                        and node_name in expr.values
                                    ):
                                        try:
                                            v1.delete_persistent_volume(
                                                pv.metadata.name
                                            )
                                            print(
                                                "PVs on node {} successfully deleted: {}".format(
                                                    node_name, pv.metadata.name
                                                )
                                            )
                                        except ApiException as e:
                                            print(f"Error: {e}")

        # sleep for 1 seconds before polling again
        # https://learn.microsoft.com/en-us/azure/virtual-machines/windows/scheduled-events#polling-frequency
        time.sleep(1)


if __name__ == "__main__":
    main()
