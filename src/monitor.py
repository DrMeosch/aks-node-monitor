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
    node_name = os.getenv("NODE_NAME")
    pod_name = os.getenv("POD_NAME")
    if not node_name or not pod_name:
        print("Environment variables not set.")
        return

    url = "http://169.254.169.254/metadata/scheduledevents?api-version=2019-08-01"
    headers = {"Metadata": "true"}

    while True:
        # add polling for scheduled events here
        # to improve the performance

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            event_response = response.json()
        except requests.RequestException as err:
            print(f"Error performing request: {err}")
            time.sleep(0.1)
            continue

        for event in event_response["Events"]:
            if event["EventType"] == "Preempt":
                if node_name in event["Resources"]:
                    print("Preempt event found for this node.")
                    v1 = client.CoreV1Api()
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
                        if pod.metadata.name == pod_name:
                            continue
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

        # sleep for 10 seconds before polling again
        time.sleep(0.1)


if __name__ == "__main__":
    main()
