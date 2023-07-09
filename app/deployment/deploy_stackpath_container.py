#!/usr/bin/env python3

import requests
import os 
import json
import sys
from dotenv import load_dotenv
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.agents.logger_agent import LoggerAgent

load_dotenv() 

log_agent = LoggerAgent('deploy_agent', 'deploy_agent.log', level='INFO')

TYPE = os.environ.get('TYPE')

url = "https://gateway.stackpath.com/identity/v1/oauth2/token"

headers = {
    "accept": "application/json",
    "content-type": "application/json"
}
payload = {
    "grant_type": "client_credentials",
    "client_id": os.environ.get("STACKPATH_CLIENT_ID"),
    "client_secret": os.environ.get("STACKPATH_API_CLIENT_SECRET")
}
response = requests.post(url, json=payload, headers=headers)
bearer_token = json.loads(response.text)['access_token']

# get stack id
url = f"https://gateway.stackpath.com/stack/v1/stacks/{os.environ.get('STACKPATH_STACK_ID')}"

headers = {
    "accept": "application/json",
    "authorization": f"Bearer {bearer_token}"
}

response = requests.get(url, headers=headers)
stack_id = json.loads(response.text)['id']


# Get existing workloads
url = f'https://gateway.stackpath.com/workload/v1/stacks/{stack_id}/workloads'

response = requests.get(url, headers=headers)

# And delete an existing workload with the same name as the one we're trying to deploy
if response.status_code == 200:
    workloads = response.json()
    for workload in workloads['results']:
        log_agent.print_and_log(f"Existing workload: {workload['name']}")
        if workload['name'] == os.environ.get('WORKLOAD_NAME'):
            workload_id = workload['id']
            url = f'https://gateway.stackpath.com/workload/v1/stacks/{stack_id}/workloads/{workload_id}'
            response = requests.delete(url, headers=headers)
            if response.status_code == 204:
                log_agent.print_and_log(f"{workload['name']} deleted")

# Load configuration from JSON file
with open('app/deployment/sp-2_container_request_template.json') as f:
    config = json.load(f)

# Add env vars to the environment variables of the container
config['payload']['workload']['spec']['containers']['webserver']['image'] = os.environ.get('DOCKER_IMAGE_PATH')
config['payload']['workload']['spec']['imagePullCredentials'][0]['dockerRegistry']['server'] = os.environ.get('DOCKER_REGISTRY')
config['payload']['workload']['spec']['imagePullCredentials'][0]['dockerRegistry']['username'] = os.environ.get('DOCKER_USERNAME')
config['payload']['workload']['spec']['imagePullCredentials'][0]['dockerRegistry']['password'] = os.getenv('DOCKER_TOKEN')

config['payload']['workload']['name'] = os.environ.get('WORKLOAD_NAME').lower()
config['payload']['workload']['slug'] = os.environ.get('WORKLOAD_SLUG').lower()

match TYPE:
            case 'discord':
                config['payload']['workload']['spec']['containers']['webserver']['env'] = {
                    'DISCORD_TOKEN': {
                    'value': os.getenv('DISCORD_TOKEN')
                    },
                    'DISCORD_CHANNEL_ID': {
                        'value': os.getenv('DISCORD_CHANNEL_ID')
                    }
                }
            case 'slack':
                config['payload']['workload']['spec']['containers']['webserver']['env'] = {
                    'SLACK_BOT_TOKEN': {
                    'value': os.getenv('SLACK_BOT_TOKEN')
                    },
                    'SLACK_APP_TOKEN': {
                        'value': os.getenv('SLACK_APP_TOKEN')
                    }
                }
            case _:
                log_agent.print_and_log(f"TYPE not properly defined")
                
config['payload']['workload']['spec']['containers']['webserver']['env'] = {
    'OPENAI_API_KEY': {
        'value': os.getenv('OPENAI_API_KEY')
    },
    'PINECONE_API_KEY': {
        'value': os.getenv('PINECONE_API_KEY')
    },
    'VECTORSTORE_INDEX': {
        'value': os.environ.get('VECTORSTORE_INDEX')
    },
    'VECTORSTORE_NAMESPACES': {
        'value': json.dumps(os.environ.get('VECTORSTORE_NAMESPACES'))
    }
}

url = f"https://gateway.stackpath.com/workload/v1/stacks/{os.environ.get('STACKPATH_STACK_ID')}/workloads"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {bearer_token}"
}
payload = config['payload']

# Make the API call
response = requests.post(url, json=payload, headers=headers)
if response.status_code == 200:
    log_agent.print_and_log(f"{os.environ.get('WORKLOAD_NAME').lower()} created : {response.text}")
else:
    log_agent.print_and_log(f"Something went wrong creating the workload: {response.text}")

