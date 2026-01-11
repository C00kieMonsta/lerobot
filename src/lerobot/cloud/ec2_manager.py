"""EC2 instance management for LeRobot cloud training."""

import logging
from typing import Optional
from lerobot.cloud.aws_client import AWSClient

logger = logging.getLogger(__name__)


class EC2Manager:
    """Manages EC2 instance lifecycle."""
    
    # Deep Learning AMI IDs (change for your region)
    AMI_IDS = {
        "us-east-1": "ami-0068ee3283a678afd",  # Deep Learning OSS Nvidia Driver AMI GPU TensorFlow 2.18 (Ubuntu 22.04)
        "us-west-2": "ami-0068ee3283a678afd",  # Update for your regions
    }
    
    def __init__(self, aws_client: AWSClient):
        """
        Initialize EC2Manager.
        
        Args:
            aws_client: AWSClient instance with active session
        """
        self.aws_client = aws_client
        self.ec2 = aws_client.get_ec2_client()

    def launch_instance(
        self, 
        instance_type: str = "g5.xlarge",
        ami_id: Optional[str] = None,
        key_name: str = "lerobot-training-key",
        security_group_name: str = "lerobot-training",
    ) -> str:
        """
        Launch an EC2 instance.
        
        Args:
            instance_type: EC2 instance type
            ami_id: AMI ID (Deep Learning AMI). If None, uses default for region
            key_name: EC2 key pair name
            security_group_name: Security group name
            
        Returns:
            Instance ID
        """
        if ami_id is None:
            region = self.aws_client.region
            ami_id = self.AMI_IDS.get(region)
            if ami_id is None:
                raise ValueError(f"No default AMI for region {region}")
        
        # Ensure key pair and security group exist
        logger.info("Setting up SSH key pair and security group...")
        self.aws_client.create_or_get_key_pair(key_name)
        sg_id = self.aws_client.create_or_get_security_group(security_group_name)
        
        logger.info(f"Launching {instance_type} with AMI {ami_id}")
        
        response = self.ec2.run_instances(
            ImageId=ami_id,
            MinCount=1,
            MaxCount=1,
            InstanceType=instance_type,
            SecurityGroupIds=[sg_id],
            KeyName=key_name,
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Name", "Value": "lerobot-training"},
                        {"Key": "Purpose", "Value": "LeRobot Training"},
                    ],
                }
            ],
        )
        
        instance_id = response["Instances"][0]["InstanceId"]
        logger.info(f"Instance launched: {instance_id}")
        return instance_id

    def get_instance_status(self, instance_id: str) -> str:
        """Get instance status."""
        response = self.ec2.describe_instances(InstanceIds=[instance_id])
        status = response["Reservations"][0]["Instances"][0]["State"]["Name"]
        return status
    
    def get_instance_ip(self, instance_id: str) -> Optional[str]:
        """Get public IP address of instance."""
        response = self.ec2.describe_instances(InstanceIds=[instance_id])
        instance = response["Reservations"][0]["Instances"][0]
        return instance.get("PublicIpAddress")
    
    def terminate_instance(self, instance_id: str) -> bool:
        """Terminate an instance."""
        logger.info(f"Terminating instance {instance_id}")
        self.ec2.terminate_instances(InstanceIds=[instance_id])
        return True