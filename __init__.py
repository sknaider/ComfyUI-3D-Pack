import os
import sys
from pathlib import Path
import logging

import folder_paths as comfy_paths

# ROOT_PATH = os.path.join(comfy_paths.get_folder_paths("custom_nodes")[0], "ComfyUI-3D-Pack")
ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
MODULE_PATH = os.path.join(ROOT_PATH, "Gen_3D_Modules")
MV_ALGO_PATH = os.path.join(ROOT_PATH, "MVs_Algorithms")

sys.path.append(ROOT_PATH)
sys.path.append(MODULE_PATH)
sys.path.append(MV_ALGO_PATH)

import shutil
import __main__
import importlib
import inspect
from .webserver.server import server, set_web_conf
from .shared_utils.log_utils import setup_logger

# Common formatter for simplicity, adjust as needed
common_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

# Setup logging for transformers
setup_logger('transformers', logging.WARNING, [logging.WARNING], [logging.ERROR, logging.CRITICAL], common_formatter)

# Setup logging for diffusers
setup_logger('diffusers_logging', logging.INFO, [logging.INFO, logging.WARNING], [logging.ERROR, logging.CRITICAL], common_formatter)

# Redirect warnings to the logging system
logging.captureWarnings(True)

# Load enterprise configuration
from .config import get_config

app_config = get_config(Path(ROOT_PATH))

# Configure web server with security settings
web_conf = {
    'clients_ip': app_config.security.allowed_ips,
    'api_keys': app_config.security.api_keys,
    'enable_auth': app_config.security.enable_auth,
    'allowed_directories': [
        app_config.storage.output_base_path,
        app_config.storage.models_base_path,
    ],
    'output_directory': app_config.storage.output_base_path,
}
set_web_conf(web_conf)

# Log into huggingface if given user specified token
hf_token = app_config.huggingface_token
if hf_token and isinstance(hf_token, str) and len(hf_token) > 0:
    try:
        from huggingface_hub import login
        login(token=hf_token)
        logging.info("Successfully logged into HuggingFace")
    except Exception as e:
        logging.error(f"Failed to login to HuggingFace: {e}")

# Backward compatibility: expose sys_conf for legacy code
sys_conf = {
    'huggingface': {'token': hf_token or ""},
    'web': {'clients_ip': app_config.web_clients_ip}
}

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

nodes_filename = "nodes"
module = importlib.import_module(f".{nodes_filename}", package=__name__)
for name, cls in inspect.getmembers(module, inspect.isclass):
    if cls.__module__ == module.__name__:
        name = name.replace("_", " ")

        node = f"[Comfy3D] {name}"
        disp = f"{name}"

        NODE_CLASS_MAPPINGS[node] = cls
        NODE_DISPLAY_NAME_MAPPINGS[node] = disp
        
WEB_DIRECTORY = "./web"
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']

# # Cleanup old extension folder
folder_web = os.path.join(os.path.dirname(os.path.realpath(__main__.__file__)), "web")
extensions_folder = os.path.join(folder_web, 'extensions', 'ComfyUI-3D-Pack')

def cleanup():
    if os.path.exists(extensions_folder):
        shutil.rmtree(extensions_folder)
        print('\033[34mComfy3D: \033[92mRemoved old extension folder\033[0m')

cleanup()