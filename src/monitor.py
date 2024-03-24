from kubernetes import client, config, watch

# Load the kube config from the default location (`~/.kube/config`).
config.load_kube_config()

# Create an instance of the API class.
v1 = client.CoreV1Api()
w = watch.Watch()

# {"DocumentIncarnation":1,"Events":[{"EventId":"51941B56-8080-45AC-81AE-8BDA818F5958","EventStatus":"Scheduled","EventType":"Preempt","ResourceType":"VirtualMachine","Resources":["aks-workloads1-15413341-vmss_3"],"NotBefore":"Sat, 16 Mar 2024 19:52:09 GMT","Description":"","EventSource":"Platform"}]}

# Watching for events in all namespaces. Adjust the namespace as necessary.
for event in w.stream(v1.list_event_for_all_namespaces):
    print(f"Event: {event['type']} {event['object'].kind}")
    # Here, you can filter events and trigger reactions
    if event['object'].reason == 'Preempted':  # Example condition
        # Trigger your reaction here
        print("Node Preemption Event Detected!")
