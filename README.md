


SwiftDeploy  
the CLI generates Nginx and Docker Compose configurations, manages the container lifecycle, and keeps your stack healthy.

The manifest is the single source of truth. Generated files are disposable 
— swiftdeploy init always recreates them from scratch.


Project Structure
swiftdeploy/
├── manifest.yaml          
├── swiftdeploy           
├── docker-compose.yaml.j2     
├── nginx.conf.js2             
└── app/
    └── main.py 

manifest.yaml
The base manifest structure:
yamlservices:
  image: swift-deploy-1-node:latest
  port: 3000

nginx:
  image: nginx:latest
  port: 8080
  proxy_timeout: 30

network:
  name: swiftdeploy-net
  driver_type: bridge
You may extend this manifest, but the fields above are required and must not be removed.

CLI Reference
Run all commands from the project root:


NOTE : "RUN docker build -t swift-deploy-1-node:latest ."
Before swiftdeploy init , so init can attest if there is an image


init
Parses manifest.yaml and generates nginx.conf and docker-compose.yml from templates.
bash./swiftdeploy init
validate

Runs 5 pre-flight checks before deployment. Exits non-zero on any failure.

Check description manifest.yaml exists and is valid YAML
All required fields are present,non-empty
The Docker image referenced in the manifest exists locally
The Nginx port is not already bound on the host5The generated nginx.conf is syntactically valid

bash./swiftdeploy validate

deploy

Runs init, brings up the full stack, and blocks until health checks pass or a 60-second timeout is reached.
bash./swiftdeploy deploy

promote

Switches the deployment mode between stable and canary with a rolling service restart.
bash./swiftdeploy promote canary
./swiftdeploy promote stable
What it does:

Updates the mode field in manifest.yaml in-place
Regenerates docker-compose.yml with the new MODE env var
Restarts the service container only (Nginx is untouched)
Confirms the new mode by hitting /healthz

teardown
Stops and removes all containers, networks, and volumes.
bash./swiftdeploy teardown
./swiftdeploy teardown --clean   # Also deletes generated config files

API Service
The service runs in either stable or canary mode, controlled by the MODE environment variable. Both modes use the same image.

Endpoints
MethodPathDescription
GET/ Welcome message with current mode, version, and server timestamp
GET/ healthzLiveness check — returns status and process uptime in seconds
POST/chaosSimulates degraded behaviour (canary mode only)
Canary Mode

Adds X-Mode: canary header to every response
Activates the /chaos endpoint

Chaos Endpoint (POST /chaos)
json{ "mode": "slow", "duration": 5 }
Sleeps N seconds before responding.
json{ "mode": "error", "rate": 0.5 }
Returns HTTP 500 on approximately 50% of subsequent requests.
json{ "mode": "recover" }
Cancels any active chaos state and returns to normal operation.

Nginx
Generated nginx.conf behaviour:

Listens on nginx.port from the manifest
Timeouts set from nginx.proxy_timeout
Returns JSON error bodies on 502, 503, 504:

json  { "error": "...", "code": "...", "service": "...", "contact": "..." }

Adds X-Deployed-By: swiftdeploy to every response
Forwards X-Mode header from the upstream service
Access log format:

  $time_iso8601 | $status | ${request_time}s | $upstream_addr | $request

The service port is never exposed directly. All traffic routes through Nginx.


Docker & Security

Containers run as a non-root user with dropped Linux capabilities
MODE, APP_VERSION, and APP_PORT are injected into the service container
A named volume is mounted for logs
Health check defined on /healthz
Images must be under 300MB
Restart policy and network are derived from the manifest


