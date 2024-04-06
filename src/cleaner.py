from kubernetes import client, config
from kubernetes.client.rest import ApiException

import time
from kubernetes import client

# https://github.com/kubernetes-client/python/blob/master/examples/in_cluster_config.py
config.load_incluster_config()


def main():
    while True:
        v1 = client.CoreV1Api()
        nodes = v1.list_node(watch=False)
        nodes = [node.metadata.name for node in nodes.items]
        try:
            pvs = v1.list_persistent_volume(watch=False)
        except ApiException as e:
            print(f"Error: {e}")
        # deleting PVs on nodes that are not in the cluster
        for pv in pvs.items:
            if not pv.metadata.name.startswith("local-pv-"):
                continue
            if (
                pv.spec.node_affinity
                and pv.spec.node_affinity.required.node_selector_terms
            ):
                for term in pv.spec.node_affinity.required.node_selector_terms:
                    for expr in term.match_expressions:
                        if (
                            expr.key == "kubernetes.io/hostname"
                            # assume only one value in the list
                            and expr.values[0] not in nodes
                        ):
                            try:
                                v1.delete_persistent_volume(pv.metadata.name)
                                print(
                                    "PVs of node {} successfully deleted: {}".format(
                                        expr.values[0], pv.metadata.name
                                    )
                                )
                            except ApiException as e:
                                print(f"Error: {e}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
