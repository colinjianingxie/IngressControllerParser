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

We need to be able to access the kubernetes client API. So let's install the library by running in the terminal: **pip3 install kubernetes**. In addition, we are going to be exposing metrics on a local server so that Prometheus can detect it. We need to install the Prometheus library: **pip3 install prometheus_client**

### Minikube Setup
1. Make sure minikube is started by running: **minikube start**
2. Create a **test** namespace by running: **kubectl create ns test** we will be installing an ingress controller into this namespace.
3. Create a **test2** namespace by running: **kubectl create ns test2** we will be installing another ingress controller into this namespace.
4. Create an **service-ns-1** namespace by running: **kubectl create ns service-ns-1** this will be where the demo service will be stored.
5. Turn on the ingress for minikube by running: **minikube addons enable ingress**

### Setting up /etc/hosts

We need to redirect the minikube ip address to a url.

1. In minikube, run: **kubectl cluster-info**
2. Obtain the master ip address of the cluster: **(192.168.xxx.xxx)**
3. Under your local machine's /etc/hosts, add the following redirection ip in the file by running: **sudo vim /etc/hosts** and writing/saving: **(192.168.xxx.xxx) foo.bar.com **

