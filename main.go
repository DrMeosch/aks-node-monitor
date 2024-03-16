package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"time"
)

// Structs to unmarshal JSON response
type ScheduledEvent struct {
	EventId       string   `json:"EventId"`
	EventStatus   string   `json:"EventStatus"`
	EventType     string   `json:"EventType"`
	ResourceType  string   `json:"ResourceType"`
	Resources     []string `json:"Resources"`
	NotBefore     string   `json:"NotBefore"`
	Description   string   `json:"Description"`
	EventSource   string   `json:"EventSource"`
}

type EventResponse struct {
	DocumentIncarnation int              `json:"DocumentIncarnation"`
	Events              []ScheduledEvent `json:"Events"`
}

func main() {
	nodeName := os.Getenv("NODE_NAME")
	if nodeName == "" {
		fmt.Println("NODE_NAME environment variable not set.")
		return
	}

	url := "http://169.254.169.254/metadata/scheduledevents?api-version=2019-08-01"
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		// Create a new HTTP client
		client := &http.Client{}

		// Create request
		req, err := http.NewRequest("GET", url, nil)
		if err != nil {
			fmt.Println("Error creating request:", err)
			continue
		}

		// Set required header
		req.Header.Set("Metadata", "true")

		// Perform the request
		resp, err := client.Do(req)
		if err != nil {
			fmt.Println("Error performing request:", err)
			continue
		}

		defer resp.Body.Close()

		// Decode JSON response
		var eventResp EventResponse
		err = json.NewDecoder(resp.Body).Decode(&eventResp)
		if err != nil {
			fmt.Println("Error decoding response:", err)
			continue
		}

		// Check for Preempt events and node name
		for _, event := range eventResp.Events {
			if event.EventType == "Preempt" {
				for _, resource := range event.Resources {
					if resource == nodeName {
						fmt.Println("Preempt event found for this node. Draining node.")
						cmd := exec.Command("kubectl", "drain", nodeName)
						err := cmd.Run()
						if err != nil {
							fmt.Println("Error executing kubectl command:", err)
						} else {
							fmt.Println("Node successfully drained.")
						}
						return
					}
				}
			}
		}
	}
}
