import os
import kopf
from kubernetes import client, config, utils
import logging
import yaml
import datetime

logging.basicConfig(filename="./log.log",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)
logger = logging.getLogger("Operator Logger")
logger.debug("INITIALIZING")

if os.environ.get('ENV') == 'DEV':
  config.load_kube_config()
else:
  config.load_incluster_config()

def get_default_index_file():
  path = os.path.dirname(__file__) + '/default_index.html'
  try:
    index = open(path, 'rt').read()
  except:
    kopf.PermanentError("Error on reading default index file")
    raise FileExistsError
  
  return index

def get_yaml_files(name, replicas, port, namespace, index_html=""):
  path = os.path.dirname(__file__) + '/manifests/application/application.yaml'
  logger.debug(f"path: {path}")
  try:
    tmpl = open(path, 'rt').read()
  except:
    kopf.PermanentError("Error on reading template file")
    raise
  
  logger.debug("Got template")
  
  text = tmpl.format(app_name=name, deployment_replicas=int(replicas), port=int(port), namespace=namespace, index_html="").split("---\n")
  logger.debug("Templating completed: {text}")
  yaml_files = [yaml.safe_load(x) for x in text]
  logger.debug("Generates YAML Files")
  yaml_files[1]['data']['index.html'] = index_html # Templating the index.html file with tmpl.format doesn't work for some reason. (Not the best fix)
  
  return yaml_files

def get_cm_yaml_files(name, namespace, index_html=""):
  path = os.path.dirname(__file__) + '/manifests/application/cm.yaml'
  logger.debug(f"path: {path}")
  try:
    tmpl = open(path, 'rt').read()
  except:
    kopf.PermanentError("Error on reading template file")
    raise
  
  logger.debug("Got template")
  
  text = tmpl.format(app_name=name, namespace=namespace, index_html="")
  logger.debug(f"Templating completed: {text}")
  yaml_file = yaml.safe_load(text)
  logger.debug("Generates YAML Files")
  yaml_file['data']['index.html'] = index_html # Templating the index.html file with tmpl.format doesn't work for some reason. (Not the best fix)
  logger.debug(yaml_file)
  
  return yaml_file

@kopf.on.create('tppython.grupo4.ultra.uaionline.edu', 'v1', 'tppythondeployment')
def fn_create(namespace, name, spec, body, **kwargs):
  logger.info("Starting fn_create")
  
  replicas = spec.get("replicas")
  if not replicas:
    replicas = 1
  port = spec.get("port")
  if not port:
    port = 8080
  index_file = spec.get("index_file")
  if not index_file:
    index_file = str(get_default_index_file())
    
  logger.debug(f"replicas: {replicas} - port: {port}")
  yaml_files = get_yaml_files(name, replicas, port, namespace, index_file)
  
  for obj in yaml_files:
    kopf.adopt(obj)

  k8s_client = client.ApiClient()
  utils.create_from_yaml(k8s_client, yaml_objects=yaml_files)
  
  logger.info("Created")
  
@kopf.on.update('tppython.grupo4.ultra.uaionline.edu', 'v1', 'tppythondeployment')
def fn_update(namespace, name, spec, new, **kwargs):
  logger.info("Starting fn_update")

  logger.debug(1)  
  if new.get('spec') is not None and new['spec'].get('port') is not None:
    kopf.PermanentError("The port cannot be modified")
    return
  
  logger.debug(2)
  if new.get('spec') is not None and new['spec'].get('replicas') is not None:
    replicas = new['spec']['replicas']
    apps_v1 = client.AppsV1Api()
    apps_v1.patch_namespaced_deployment_scale(name, namespace, {"spec": {"replicas": replicas}})
  
  logger.debug(3)
  if new.get('spec') is not None and new['spec'].get('index_html') is not None:
    logger.debug(3.1)
    k8s_client = client.CoreV1Api()
    index_file = new['spec']['index_html']
    
    cm = get_cm_yaml_files(name, namespace, index_file)
    logger.debug(cm)
    
    k8s_client.patch_namespaced_config_map(f"{name}-index", namespace, cm)
    
    # Restart the pod so the cm changes have effect
    apps_v1 = client.AppsV1Api()
    now = datetime.datetime.utcnow()
    now = str(now.isoformat("T") + "Z")
    body = {
        'spec': {
            'template':{
                'metadata': {
                    'annotations': {
                        'kubectl.kubernetes.io/restartedAt': now
                    }
                }
            }
        }
    }
    apps_v1.patch_namespaced_deployment(name, namespace, body, pretty='true')