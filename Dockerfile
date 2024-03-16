# Create build stage based on buster image
FROM golang:1.22 AS builder
# Create working directory under /app
WORKDIR /app
# Copy over all go config (go.mod, go.sum etc.)
COPY go.* ./
# Install any required modules
RUN go mod download
# Copy over Go source code
COPY *.go ./
# Run the Go build and output binary under hello_go_http
RUN go build -o /aks-node-monitor

FROM bitnami/kubectl:latest
COPY --from=builder /aks-node-monitor /aks-node-monitor
# Make sure to expose the port the HTTP server is using
# Run the app binary when we run the container
ENTRYPOINT ["/aks-node-monitor"]