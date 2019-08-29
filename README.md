# Ingress Controller Parser
How to Parse Logs from Ingress Controllers on Mac

### Pre-Requisites
1. Python3 installed (with pip3)
2. Basic knowledge of Minikube
3. Basic understanding of Python
4. Helm Installed
5. Docker installed (Desktop Version)
6. Brew installed
7. Knowledge of vim

### Python Setup (required)

We need to be able to access the kubernetes client API. So let's install the library by running in the terminal: 
```
pip3 install kubernetes
``` 

In addition, we are going to be exposing metrics on a local server so that Prometheus can detect it. We need to install the Prometheus library: 
```
pip3 install prometheus_client
```

### Minikube Setup
1. Make sure minikube is started by running: 
```
minikube start
```
2. Create a **test** namespace by running: 
```
kubectl create ns test
```
we will be installing an ingress controller into this namespace.

3. Create a **test2** namespace by running: 
```kubectl create ns test2```
we will be installing another ingress controller into this namespace.

4. Create an **service-ns-1** namespace by running: 
```kubectl create ns service-ns-1``` 
this will be where the demo service will be stored.
5. Turn on the ingress for minikube by running: 
```minikube addons enable ingress```

### Setting up /etc/hosts

We need to redirect the minikube ip address to a url.

1. In minikube, run: ```kubectl cluster-info```
2. Obtain the master ip address of the cluster: **(192.168.xxx.xxx)**
3. Under your local machine's /etc/hosts, add the following redirection ip in the file by running: ```sudo vim /etc/hosts``` and writing/saving: **(192.168.xxx.xxx) foo.bar.com **

### Installing Services

Download the following **example.yaml**

```
kind: Service
apiVersion: v1
metadata:
  namespace: service-ns-1
  name: example-temp
  labels:
    app: example-temp
spec:
  selector:
    app: example-temp
  ports:
  - name: web
    port: 8080
    nodePort: 30910
  type: NodePort
---
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  namespace: service-ns-1
  name: example-temp
spec:
  replicas: 1
  template:
    metadata:
      labels:
        app: example-temp
    spec:
      containers:
      - name: example-temp
        image: xienokia/hello-app
        ports:
        - name: web
          containerPort: 8080
---
apiVersion: extensions/v1beta1
kind: Ingress
metadata:
  name: test-ingress-aaa
  annotations:
    kubernetes.io/ingress.class: nginx
  namespace: service-ns-1
spec:
  backend:
    serviceName: example-temp
    servicePort: 8080
  rules:
  - host: foo.bar.com
    http:
      paths:
      - path: /test
        backend:
          serviceName: example-temp
          servicePort: 8080
```


Navigate to the **example.yaml** file in the terminal and deploy the file by running in terminal: ```kubectl apply -f example.yaml```

Wait 2-3 minutes for everything to configure. To check everything has been deployed successfully, access **foo.bar.com/test** in your browser, and you should see a basic Hello World Application.

### Ingress Controller Helm Installation

We will be performing helm installations for the ingress controllers.
Add the NGINX Helm repository by running ```helm repo add nginx-stable https://helm.nginx.com/stable``` then ```helm repo update```

Initialize tiller by running: ```helm init```

Then to install the helm charts to namespace **test** and **test2** ,respectively, run:

```
helm install nginx-stable/nginx-ingress --set controller.service.type=NodePort --name my-nginx --namespace=test
```
and
```
helm install nginx-stable/nginx-ingress --set controller.service.type=NodePort --name my-nginx-2 --namespace=test2
```

### Edit the Ingress Controller Service

We now need to add custom labels to our ingress controller services, so we are able to detect the ingress controller services through the python code.

Do the following for the ingress controller in the **test** namespace:
1. Obtain the service name of the ingress controller in the **test** namespace by running: ```kubectl -n test get svc``` and copy the service name.
2. Edit the service by running: ```kubectl -n test edit svc/(insert service name)```. Note that the service name should be something like: **my-nginx-nginx-ingress**
3. Under the **labels** tag, add the following label: **service-type: ingress-controller-service** Formatting is important, so make sure there are spaces before **service-type** to align with the other metatags, and a space after the **:**

Do the following for the ingress controller in the **test2** namespace:
1. Obtain the service name of the ingress controller in the **test2** namespace by running: ```kubectl -n test2 get svc``` and copy the service name.
2. Edit the service by running: ```kubectl -n test2 edit svc/(insert service name)```. Note that the service name should be something like: **my-nginx-2-nginx-ingress**
3. Under the **labels** tag, add the following label: **service-type: ingress-controller-service** Formatting is important, so make sure there are spaces before **service-type** to align with the other metatags, and a space after the **:**

![alt text](https://github.com/colinjianingxie/IngressControllerParser/blob/master/ss_images/ss1.png "Editing the Service")

### Viewing Ingress Controller Logs

Run the following in terminal: ```kubectl -n test get svc``` and remember the nodePort of the ingress-controller-service. It should be in the form of: **80:(nodePort)** 

Run the following in terminal: ```kubectl -n test2 get svc``` and remember the nodePort of the ingress-controller-service. It should be in the form of: **80:(nodePort)** 

In your browser, go to **foo.bar.com:(insert ingress controller nodePort)/(random endpoint)** and refresh a few times to generate logs. 
- example url for **test** namespace ingress controller service: **foo.bar.com:32453/a**
- example url for **test2** namespace ingress controller service: **foo.bar.com:30071/b**

Change the **(random endpoint)** a few times for each ingress controller service to generate a few logs for those endpoints.

Run the following to see the pod name for the **test** ingress controller and take note of it: ```kubectl -n test get pod```
To view the logs for this pod, run: ```kubectl -n test log (ingress controller pod name)```


Run the following to see the pod name for the **test2** ingress controller and take note of it: ```kubectl -n test2 get pod```
To view the logs for this pod, run: ```kubectl -n test2 log (ingress controller pod name)```

### The Parser

Download the following parse.py
```python

import subprocess
import re
import os
from kubernetes import client, config
from prometheus_client import start_http_server, Summary
import random
import time
from prometheus_client import Counter
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, REGISTRY



LABEL_NAME = "service-type"
INGRESS_CONTROLLER_SERVICE = "ingress-controller-service"

log_expression = "^(?P<remote>[^ ]*) - - \[(?P<time>[^\]]*)\] \"(?P<method>\S+)(?: +(?P<path>[^\"]*) +\S*)?\" (?P<status>\d+) (?P<bytes_sent>\d+) \"(?P<url>[^ ]*)\" \"(?P<user_agent>[^\"]*)\" \"-\""

#Another regular expression
#"^(?P<remote>[^ ]*) - (?P<user>[^ ]+) \[(?P<time>[^\]]*)\] \"(?P<method>\S+)(?: +(?P<path>[^\"]*) +\S*)?\" (?P<status>\d+) (?P<bytes_sent>\d+) \"(?P<referrer>[^ ]*)\" \"(?P<user_agent>[^\"]*)\" (?P<request_length>\d+) (?P<request_time>[\d.]+) \[(?P<upstream>[^\]]*)\] (?P<upstream_addr>[^ ]*) (?P<upstream_response_length>\d+) (?P<upstream_response_time>[\d.]+) (?P<upstream_status>\d+) (?P<request_id>[^ ]*)"

class CustomCollector(object):
    def collect(self):

        c = CounterMetricFamily('requests', 'Ingress Controllers', labels=['namespace','ingress_controller_pod', 'path'])
        for ingress_controller in get_ingress_controller_list():
        	ns = ingress_controller[0]
        	ic = ingress_controller[1]
        	temp_dict = dict()
        	temp_cmd = ('kubectl -n ' + ns + ' log ' + ic).split()
        	for log in run_command(temp_cmd):
        		parseIngressLog(temp_dict, ns, ic, log)
        	for path, request_number in temp_dict.items() :
        		c.add_metric([ns,ic, path], request_number)
        yield c


def run_command(command):
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    return iter(p.stdout.readline, b'')

def get_ingress_controller_list():
	#CONNECTING TO MINIKUBE
	kube_config = os.getenv('KUBE_CONFIG')
	context = os.getenv('CONTEXT')

	proxy_url = os.getenv('HTTP_PROXY', None)
	config.load_kube_config(config_file=kube_config,
	                        context=context)
	if proxy_url:
	    logging.warning("Setting proxy: {}".format(proxy_url))
	    client.Configuration._default.proxy = proxy_url

	#ACCESSING THE API
	core_api = client.CoreV1Api()

	ingress_controllers = []

	services = core_api.list_service_for_all_namespaces(
		label_selector=f"{LABEL_NAME}={INGRESS_CONTROLLER_SERVICE}"
	)

	for service in services.items:
		label_selector = ""
		for k, v in service.spec.selector.items():
			label_selector = ",".join([label_selector, f"{k}={v}"])
		label_selector = label_selector.strip(",") #returns app=service name

		pod = core_api.list_namespaced_pod(
			namespace=service.metadata.namespace,
            label_selector=label_selector
		)
		#container = deployment.spec.template.spec
		ingress_controllers.append([service.metadata.namespace, pod.items[0].metadata.name])

	return ingress_controllers

def parseIngressLog(log_dictionary, namespace, ingress_controller, byteLog):
	stringLog = byteLog.decode()
	result_log = re.search(log_expression, stringLog)
	if result_log:
		log_remote = result_log.group('remote')
		log_time = result_log.group('time')
		log_method = result_log.group('method')
		log_path = result_log.group('path')
		log_bytes_sent = result_log.group('bytes_sent')
		log_status = result_log.group('status')
		log_url = result_log.group('url')

		log_user_agent = result_log.group('user_agent')
		if not '-' in log_url: #filter out non needed paths
			addLog(log_dictionary, namespace, ingress_controller, log_time,  log_url)
			#print(log_url)

def addLog(log_dictionary, namespace, ingress_controller, log_time, log_url):

	temp_key = log_url
	log_dictionary[temp_key] = log_dictionary.get(temp_key, 0) + 1	


# Create a metric to track time spent and requests made.
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')

# Decorate function with metric.
@REQUEST_TIME.time()
def process_request(t):
    """A dummy function that takes some time."""
    time.sleep(t)


def main():
	start_http_server(8000)

	#Add the custom metrics
	REGISTRY.register(CustomCollector())

	
	# Generate some requests.
	while True:
		process_request(random.random())



main()
```

On the terminal, navigate to where the **parse.py** file is located. Then, run the python3 program through: ```python3 parse.py```

To view the results of the program, open a browser window and navigate to: **localhost:8000**
You should see something like the following, where the results of the parse are at the bottom:
![alt text](https://github.com/colinjianingxie/IngressControllerParser/blob/master/ss_images/ss2.png "Viewing Requests")

### Installing Prometheus Locally

Now we are going to install Prometheus locally through Docker Desktop. First, we need to reconfigure Docker. Docker has recently enabled Prometheus-compatible metrics on port 9323 of the engine. So, add the following daemon.json to your docker:

(You can do this on the Mac by clicking on Docker Desktop, then **Preferences -> Daemon -> Advanced** then copy paste the following)
```
{
  "metrics-addr" : "127.0.0.1:9323",
  "experimental" : true
}
```

Now, copy and save the following as **prometheus.yml**
```
# my global config
global:
  scrape_interval:     15s # Set the scrape interval to every 15 seconds. Default is every 1 minute.
  evaluation_interval: 15s # Evaluate rules every 15 seconds. The default is every 1 minute.
  # scrape_timeout is set to the global default (10s).

  # Attach these labels to any time series or alerts when communicating with
  # external systems (federation, remote storage, Alertmanager).
  external_labels:
      monitor: 'codelab-monitor'

# Load rules once and periodically evaluate them according to the global 'evaluation_interval'.
rule_files:
  # - "first.rules"
  # - "second.rules"

# A scrape configuration containing exactly one endpoint to scrape:
# Here it's Prometheus itself.
scrape_configs:
  # The job name is added as a label `job=<job_name>` to any timeseries scraped from this config.
  - job_name: 'python'
         # metrics_path defaults to '/metrics'
         # scheme defaults to 'http'.

    static_configs:
      - targets: ['docker.for.mac.host.internal:8000']
```

Since our metrics are hosted on **localhost:8000**, we will only be targeting **localhost:8000** on Prometheus.
Once you have **prometheus.yml** downloaded, we need to copy it to the **/tmp** folder. In terminal ```vim /tmp/prometheus.yml``` and copy the **prometheus.yml** content and save. Now, we need to run Prometheus, so in the terminal: ```docker swarm init```

Next, in terminal, navigate to the **/tmp** folder and run: 
```
docker service create --replicas 1 --name my-prometheus \
    --mount type=bind,source=/tmp/prometheus.yml,destination=/etc/prometheus/prometheus.yml \
    --publish published=9090,target=9090,protocol=tcp \
    prom/prometheus
```

#### Verification
1. Verify Prometheus is running by going to: **localhost:9090**
2. Make sure **localhost:8000** is running & hosting the Prometheus metrics (by running the **parse.py** program). 
3. Verify Prometheus is scraping the target by going to: **localhost:9090/targets**
4. For the query under graphs, use: **requests_total**

If all goes well, Prometheus should be scraping the ingress controller service reqeusts.


### Setting up Grafana Locally

Grafana is a tool used to make Prometheus graphs more visually appealing.
1. Install Grafana by running the following in your terminal:
```brew update``` then ```brew install grafana```
2. To start Grafana using homebrew services, first make sure homebrew/services is installed: ```brew tap homebrew/services```
3. To start Grafana, use: ```brew services start grafana```
4. Visit **localhost:3000** and the default login / password is: **admin / admin**

### Connecting Prometheus to Grafana

1. On the left side of Grafana, setup a Data source by clicking the **gear button -> Data Sources** 
2. Click **Add data source -> Prometheus** then for the URL, type: **localhost:9090**
3. Create a dashboard by clicking the **+** button on the left side of Grafana
4. Click **Add Query**
5. Under **Queries -> Metrics**, add the following metric: **requests_total**
6. Under **General**, change the title to **Requests Total**

### Filtering by Path

#### Adding Filtered Variable
1. Click the **settings** button near the top of the dashbaord (to the right of the save button)
2. Click **Variables -> New**
3. Under the General block:
- Name: **path**
- Label: **path**
4. Under Query Options:
- Data source: **Prometheus**
- Query: **label_values(requests_total, path)
- Refresh: **On Dashboard Load**
5. Click **Add** or **Update** at the very bottom

#### Adding Filtered Query

1. Under the dashboard, click the title, **Requests Total** and click **edit**
2. Under the Queries, change the metrics: **requests_total** to **requests_total{path = "$path"}**
3. Make sure you save the dashboard changes!

Now under the dashboard, you can filter by path for the requests.
Here is an example:
![alt text](https://github.com/colinjianingxie/IngressControllerParser/blob/master/ss_images/ss3.png "Final Grafana Image")

### Changing Refresh (Optional)

1. On the top right corner, you can change the auto-refresh timer.
2. To the left of the automatic refresher, you can also change the time scope.
