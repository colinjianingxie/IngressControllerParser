
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