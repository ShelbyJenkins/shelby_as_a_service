import os
import sys
import textwrap
import inspect
import shutil
from importlib import import_module
from inspect import isclass
import json

class DeploymentManager:
    def __init__(self):
        pass

        # Exits here on first run

        # # secrets from sprites, and deployment
        # self.used_sprites = set()
        # self.required_secrets = set()
        # self.required_deployment_vars = {}
        # config_module_path = f"deployments.{deployment_name}.deployment_config"
        # self.config = import_module(config_module_path)
        # self.load_moniker_requirments()
        # self.load_deployment_requirments()
        # self.generate_dockerfile()
        # self.generate_pip_requirements()
        # self.generate_actions_workflow()

    @staticmethod
    def check_for_existing_deployments():
        existing_deployment_names = []
        for deployment in os.listdir("shelby_as_a_service/deployments"):
            deployment_path = os.path.join(
                "shelby_as_a_service/deployments", deployment
            )
            if os.path.isdir(deployment_path):
                if "deployment_config.json" in os.listdir(deployment_path):
                    existing_deployment_names.append(deployment)

        return existing_deployment_names

    @staticmethod
    def load_deployment_file(deployment_name, service_name=None):
        try:
            with open(
                f"shelby_as_a_service/deployments/{deployment_name}/deployment_config.json",
                "r",
                encoding="utf-8",
            ) as stream:
                config_from_file = json.load(stream)
        except json.JSONDecodeError:
            # If the JSON file is empty or invalid, return an empty dictionary (or handle in a way you see fit)
            config_from_file = {}

        if service_name:
            return config_from_file.get(service_name, None)
        else:
            return config_from_file

    @staticmethod
    def create_deployment(deployment_name):
        """Creates a new deployment by copying from the template folder.
        Does not overwrite existing deployments.
        To start fresh delete the deployment and then use this function.
        """
        dir_path = f"shelby_as_a_service/deployments/{deployment_name}"

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        if not os.path.exists(os.path.join(dir_path, "index/inputs")):
            os.makedirs(os.path.join(dir_path, "index/inputs"))

        # Creates blank deployment_config.json
        deployment_config_dest_path = os.path.join(dir_path, "deployment_config.json")
        if not os.path.exists(deployment_config_dest_path):
            with open(deployment_config_dest_path, "w", encoding="utf-8") as file:
                file.write("{}")

        index_description_dest_path = os.path.join(dir_path, "index_description.yaml")
        if not os.path.exists(index_description_dest_path):
            index_description_source_path = "shelby_as_a_service/services/deployment_service/template/index_description.yaml"
            shutil.copy(index_description_source_path, index_description_dest_path)

        dot_env_dest_path = os.path.join(dir_path, ".env")
        if not os.path.exists(dot_env_dest_path):
            dot_env_source_path = (
                "shelby_as_a_service/services/deployment_service/template/template.env"
            )
            with open(dot_env_source_path, "r", encoding="utf-8") as file:
                lines = file.readlines()
                modified_lines = []
                for line in lines:
                    # If the line starts with a comment or is empty, keep it unchanged
                    if line.startswith("#") or line.strip() == "":
                        modified_lines.append(line)
                    else:
                        modified_lines.append(f"{deployment_name.upper()}_{line}")

            with open(dot_env_dest_path, "w", encoding="utf-8") as file:
                file.writelines(modified_lines)

    @staticmethod
    def update_deployment_json_from_model(deployment_instance, deployment_name):
        """Populates deployment_config.py from models.
        If the existing deployment_config.py has existing values it does not overwrite them.
        """

        deployment_config_file = DeploymentManager.load_deployment_file(deployment_name)

        if deployment_config_file is None:
            deployment_config_file = {}

        # Deployment
        if "deployment_instance" not in deployment_config_file:
            deployment_instance_config = {}
        else:
            deployment_instance_config = deployment_config_file["deployment_instance"]

        deployment_config_file["deployment_instance"] = DeploymentManager.load_file_variables_as_dicts(
            deployment_instance.model_, deployment_instance_config
        )

        # Sprite
        for sprite_class in deployment_instance.required_sprites_:
            sprite_model = sprite_class.model_
            sprite_name_model = sprite_model.service_name_
            if sprite_name_model not in deployment_config_file:
                sprite_config = {}
            else:
                sprite_config = deployment_config_file[sprite_name_model]

            sprite_config = DeploymentManager.load_file_variables_as_dicts(sprite_model, sprite_config)

            # Services
            if "services" not in sprite_config:
                sprite_config["services"] = {}
                services_config = {}
            else:
                services_config = sprite_config["services"]

            for sprite_class_required_service in sprite_class.required_services_:
                service_model = sprite_class_required_service.model_
                service_class_name = service_model.service_name_

                # Service
                if service_class_name not in services_config:
                    service_config = {}
                else:
                    service_config = services_config[service_class_name]

                service_config = DeploymentManager.load_file_variables_as_dicts(
                    service_model, service_config
                )

                sprite_config["services"][service_class_name] = service_config

            deployment_config_file[sprite_name_model] = sprite_config

        # Save the updated configuration
        with open(
            f"shelby_as_a_service/deployments/{deployment_name}/deployment_config.json",
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(deployment_config_file, file, ensure_ascii=False, indent=4)
    
    @staticmethod
    def load_file_variables_as_dicts(model_class, config):
        """Loads variables and values from models and existing deployment_config.py.
        Adds variables from models if they don't exist in deployment_config.py.
        If values exist for variables in deployment_config.py it uses those.
        """
        if not config:
            config = {}
        # Handle 'required'
        for var, value in sorted(vars(model_class).items()):  # sort by variable name
            if (
                not var.startswith("_")
                and not var.endswith("_")
                and not callable(value)
            ):
                if config.get(var) in [None, ""]:
                    config[var] = value
                else:
                    continue

        return config
    
    @staticmethod
    def update_deployment_json_from_memory(deployment_instance, deployment_name):
        """Populates deployment_config.py from models.
        If the existing deployment_config.py has existing values it does not overwrite them.
        """

        deployment_config_file = DeploymentManager.load_deployment_file(deployment_name)

        if deployment_config_file is None:
            deployment_config_file = {}

        # Deployment
        if "deployment_instance" not in deployment_config_file:
            deployment_instance_config = {}
        else:
            deployment_instance_config = deployment_config_file["deployment_instance"]

        deployment_config_file["deployment_instance"] = DeploymentManager.load_memory_variables_as_dicts(
            deployment_instance.model_, deployment_instance_config
        )

        # Sprite
        for sprite_class in deployment_instance.required_sprites_:
            sprite_model = sprite_class.model_
            sprite_name_model = sprite_model.service_name_
            sprite_instance = getattr(deployment_instance, sprite_name_model)
            if sprite_name_model not in deployment_config_file:
                sprite_config = {}
            else:
                sprite_config = deployment_config_file[sprite_name_model]

            sprite_config = DeploymentManager.load_memory_variables_as_dicts(sprite_instance, sprite_config)

            # Services
            if "services" not in sprite_config:
                sprite_config["services"] = {}
                services_config = {}
            else:
                services_config = sprite_config["services"]

            # Service
            for sprite_class_required_service in sprite_class.required_services_:
                service_model = sprite_class_required_service.model_
                service_class_name = service_model.service_name_
                service_instance = getattr(sprite_instance, service_class_name)
                if service_class_name not in services_config:
                    service_config = {}
                else:
                    service_config = services_config[service_class_name]

                service_config = DeploymentManager.load_memory_variables_as_dicts(
                    service_instance, service_config
                )

                sprite_config["services"][service_class_name] = service_config

            deployment_config_file[sprite_name_model] = sprite_config

        # Save the updated configuration
        with open(
            f"shelby_as_a_service/deployments/{deployment_name}/deployment_config.json",
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(deployment_config_file, file, ensure_ascii=False, indent=4)

    @staticmethod
    def load_memory_variables_as_dicts(class_instance, config):
        """Loads variables and values from class_instance and existing deployment_config.py.
        If values exist for variables in class_instance it uses those.
        """
        if not config:
            config = {}
     
        for var, value in sorted(vars(class_instance).items()):  # sort by variable name
            if var in config:
                if value not in [None, ""]:
                    config[var] = value
                else:
                    continue

        return config

    def load_moniker_requirments(self):
        for moniker in self.config.DeploymentConfig.MonikerConfigs.__dict__:
            if not moniker.startswith("_") and not moniker.endswith("_"):
                moniker_config = getattr(
                    self.config.DeploymentConfig.MonikerConfigs, moniker
                )
                if moniker_config.enabled:
                    for _, sprite_config in moniker_config.__dict__.items():
                        if inspect.isclass(sprite_config):
                            if sprite_config.enabled:
                                self.used_sprites.add(sprite_config.model.sprite_name)
                                for secret in sprite_config.model.SECRETS_:
                                    self.required_secrets.add(secret)

    def load_deployment_requirments(self):
        for req_var in self.config.DeploymentConfig.model.DEPLOYMENT_REQUIREMENTS_:
            self.required_deployment_vars[req_var] = getattr(
                self.config.DeploymentConfig, req_var
            )
        for secret in self.config.DeploymentConfig.model.SECRETS_:
            self.required_secrets.add(secret)

    def generate_dockerfile(self):
        dockerfile = f"""\
# Use an official Python runtime as a parent image
FROM python:3-slim-buster

# Install Git
RUN apt-get update && apt-get install -y git

# Set the working directory in the container to /shelby-as-a-service
WORKDIR /shelby-as-a-service

# Copy all files and folders from the root directory
COPY ./ ./ 

# Install python packages
RUN pip install --no-cache-dir -r shelby_as_a_service/deployments/{self.deployment_name}/requirements.txt

# Run Deployment
CMD ["python", "shelby_as_a_service/app.py", "--run_container_deployment", "{self.deployment_name}"]
        """
        with open(
            f"shelby_as_a_service/deployments/{self.deployment_name}/Dockerfile",
            "w",
            encoding="utf-8",
        ) as f:
            f.write(dockerfile)

    def generate_pip_requirements(self):
        combined_requirements = set()
        for sprite_name in self.used_sprites:
            with open(
                f"shelby_as_a_service/deployment_maker/{sprite_name}_requirements.txt",
                "r",
                encoding="utf-8",
            ) as file:
                sprite_requirements = set(file.read().splitlines())
            combined_requirements.update(sprite_requirements)

        with open(
            f"shelby_as_a_service/deployments/{self.deployment_name}/requirements.txt",
            "w",
            encoding="utf-8",
        ) as file:
            file.write("\n".join(combined_requirements))

    def generate_actions_workflow(self):
        # For github secrets
        github_secrets_string = "### Secrets ###\n"
        for secret in self.required_secrets:
            secret_name = f"{self.deployment_name.upper()}_{secret.upper()}"
            github_secrets_string += (
                f"{secret_name}:  ${{{{ secrets.{secret_name} }}}}\n"
            )
        github_secrets_string += "# Secrets in the format of 'secrets.NAME' with the 'NAME' portion added to your forked repos secrets. #"
        github_secrets_string = textwrap.indent(github_secrets_string, " " * 24)

        # For injecting into container env
        required_secrets_string = "REQUIRED_SECRETS: "
        for secret in self.required_secrets:
            required_secrets_string += f"{secret.upper()};"
        required_secrets_string = textwrap.indent(required_secrets_string, " " * 24)

        github_actions_script = textwrap.dedent(
            f"""\
        name: {self.deployment_name}-deployment

        on: workflow_dispatch

        jobs:
            docker:
                runs-on: ubuntu-latest
                env:
                    \n{github_secrets_string}
                    \n{required_secrets_string}
                      DEPLOYMENT_NAME: {self.deployment_name}

                steps:
                    - name: Checkout code
                        uses: actions/checkout@v3
                                        
                    - name: Set up Python
                        uses: actions/setup-python@v2
                        with:
                            python-version: '3.10.11'

                    - name: Cache pip dependencies
                        uses: actions/cache@v2
                        id: cache
                        with:
                            path: ~/.cache/pip 
                            key: ${{{{ runner.os }}}}-pip-${{{{  hashFiles('**shelby_as_a_service/deployments/{self.deployment_name}/requirements.txt') }}}}
                            restore-keys: |
                                ${{{{ runner.os }}}}-pip-

                    - name: Install dependencies
                        run: |
                            python -m pip install --upgrade pip
                            if [ -f shelby_as_a_service/deployments/{self.deployment_name}/requirements.txt ]; then pip install -r shelby_as_a_service/deployments/{self.deployment_name}/requirements.txt; fi

                    - name: Login to Docker registry
                        uses: docker/login-action@v2 
                        with:
                            registry: {self.required_deployment_vars['docker_registry']}
                            username: {self.required_deployment_vars['docker_username']}
                            password: ${{{{ secrets.{self.deployment_name.upper()}_DOCKER_TOKEN }}}}

                    - name: Build and push Docker image
                        uses: docker/build-push-action@v4
                        with:
                            context: .
                            file: shelby_as_a_service/deployments/{self.deployment_name}/Dockerfile
                            push: true
                            tags: {self.required_deployment_vars['docker_username']}/{self.required_deployment_vars['docker_repo']}:{self.deployment_name}-latest

                    - name: Add execute permissions to the script
                        run: chmod +x shelby_as_a_service/app.py

                    - name: Run deployment script
                        run: python shelby_as_a_service/app.py --deploy_container {self.deployment_name}
        """
        )

        github_actions_script = github_actions_script.replace("    ", "  ")
        os.makedirs(".github/workflows", exist_ok=True)
        # with open(f'.github/workflows/{deployment_settings.github_action_workflow_name}.yaml', 'w') as f:
        with open(
            f".github/workflows/{self.deployment_name}_deployment.yaml",
            "w",
            encoding="utf-8",
        ) as f:
            f.write(github_actions_script)
