import argparse
from typing import Dict
from models.app_base import AppBase
from services.sprites.local_sprite import LocalSprite
from services.data_processing.index_service import IndexService


class AppInstance(AppBase):
    
    enabled_sprites = ['local_sprite']
    
    secrets: Dict[str, str] = {}
    service_name_: str = 'app_instance'
    required_sprites_ = [LocalSprite]
    required_services_ = [IndexService]
    
    def __init__(self, app_name):
        """Instantiates deployment.
        super().__init__() initializes ServiceBase. We then override the base defaults.
        """
        super().__init__()
        self.app_name = app_name
        self.setup_app_instance(self)
        self.setup_sprites()
        self.setup_services()
       

def main():
    """
    This script runs shelby-as-a-service when deployed to a container.
    AND
    When running locally.

    Usage:
        None. Deployment will be configured via automation.
        If ran without args, local_web is ran.
    """
    print(f"app.py is being run as: {__name__}")

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--run_container_deployment",
        type=str,
        help="This will be called from the dockerfile after the container deploys.",
    )
    group.add_argument(
        "--deploy_container",
        type=str,
        help="This will be called from the github actions workflow to deploy the container.",
    )
    parser.add_argument(
        "deployment_name",
        type=str,
        nargs='?',
        help="For local deployment provide the name of the deployment.",
    )
    args = parser.parse_args()
   
    if args.run_container_deployment:
        deployment = AppInstance(args.run_container_deployment)
        deployment.run_sprites()
    elif args.deploy_container: 
        deploy_container(args.deploy_container)
    elif args.deployment_name: 
        deployment = AppInstance(args.deployment_name) 
        deployment.run_sprites()
    else:
        deployment = AppInstance('base') 
        deployment.run_sprites()

if __name__ == "__main__":
    main()
