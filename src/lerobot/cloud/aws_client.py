"""AWS API client wrapper for LeRobot cloud training."""

import boto3
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AWSClient:
    """Wrapper around boto3 for AWS operations."""
    
    def __init__(self, profile_name: str = "default", region: str = "us-east-1"):
        """
        Initialize AWS client.
        
        Args:
            profile_name: AWS SSO profile name
            region: AWS region (default: us-east-1)
        """
        self.profile_name = profile_name
        self.region = region
        self.session = None
        self.ec2 = None
        self.sts = None
    
    def login(self) -> bool:
        """
        Authenticate with AWS using SSO profile.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.session = boto3.Session(
                profile_name=self.profile_name,
                region_name=self.region
            )
            self.ec2 = self.session.client("ec2")
            self.sts = self.session.client("sts")
            
            # Test connection
            caller_id = self.sts.get_caller_identity()
            account_id = caller_id["Account"]
            print(f"✓ Logged in to AWS account: {account_id}")
            return True
        except Exception as e:
            print(f"✗ Failed to login: {e}")
            return False
    
    def get_account_id(self) -> str:
        """Get AWS account ID."""
        if self.sts is None:
            raise RuntimeError("Not logged in. Call login() first.")
        return self.sts.get_caller_identity()["Account"]
    
    def get_ec2_client(self):
        """Get EC2 client."""
        if self.ec2 is None:
            raise RuntimeError("Not logged in. Call login() first.")
        return self.ec2
    
    def create_or_get_key_pair(self, key_name: str = "lerobot-training-key") -> str:
        """
        Create EC2 key pair if it doesn't exist.
        
        Args:
            key_name: Name of the key pair
            
        Returns:
            Path to private key file
        """
        from pathlib import Path
        
        key_path = Path.home() / ".ssh" / f"{key_name}.pem"
        
        try:
            # Check if key pair already exists
            self.ec2.describe_key_pairs(KeyNames=[key_name])
            logger.info(f"Key pair '{key_name}' already exists")
            return str(key_path)
        except Exception as e:
            # If key pair doesn't exist, create it
            if "NotFound" in str(e) or "does not exist" in str(e):
                logger.info(f"Creating key pair '{key_name}'...")
                response = self.ec2.create_key_pair(KeyName=key_name)
                
                # Save private key
                key_path.parent.mkdir(parents=True, exist_ok=True)
                key_path.write_text(response['KeyMaterial'])
                key_path.chmod(0o600)
                
                logger.info(f"✓ Key pair created and saved to {key_path}")
                return str(key_path)
            else:
                raise RuntimeError(f"Error checking key pair: {e}")
    
    def create_or_get_security_group(
        self,
        group_name: str = "lerobot-training",
        description: str = "Security group for LeRobot cloud training"
    ) -> str:
        """
        Create security group if it doesn't exist and allow SSH.
        
        Args:
            group_name: Security group name
            description: Security group description
            
        Returns:
            Security group ID
        """
        try:
            # Check if security group exists
            response = self.ec2.describe_security_groups(GroupNames=[group_name])
            sg_id = response['SecurityGroups'][0]['GroupId']
            logger.info(f"Security group '{group_name}' already exists: {sg_id}")
            return sg_id
        except Exception as e:
            # If security group doesn't exist, create it
            if "InvalidGroup.NotFound" in str(e) or "does not exist" in str(e):
                logger.info(f"Creating security group '{group_name}'...")
                try:
                    response = self.ec2.create_security_group(
                        GroupName=group_name,
                        Description=description
                    )
                    sg_id = response['GroupId']
                    
                    # Allow SSH from anywhere
                    self.ec2.authorize_security_group_ingress(
                        GroupId=sg_id,
                        IpPermissions=[
                            {
                                'IpProtocol': 'tcp',
                                'FromPort': 22,
                                'ToPort': 22,
                                'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH'}]
                            }
                        ]
                    )
                    
                    logger.info(f"✓ Security group created: {sg_id}")
                    return sg_id
                except Exception as create_error:
                    raise RuntimeError(f"Failed to create security group: {create_error}")
            else:
                raise RuntimeError(f"Error checking security group: {e}")
        except Exception as e:
            # Handle case where security group exists but couldn't be retrieved by name
            logger.warning(f"Error checking security group: {e}")
            logger.info(f"Creating security group '{group_name}'...")
            try:
                response = self.ec2.create_security_group(
                    GroupName=group_name,
                    Description=description
                )
                sg_id = response['GroupId']
                
                # Allow SSH from anywhere
                self.ec2.authorize_security_group_ingress(
                    GroupId=sg_id,
                    IpPermissions=[
                        {
                            'IpProtocol': 'tcp',
                            'FromPort': 22,
                            'ToPort': 22,
                            'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH'}]
                        }
                    ]
                )
                
                logger.info(f"✓ Security group created: {sg_id}")
                return sg_id
            except Exception as create_error:
                raise RuntimeError(f"Failed to create security group: {create_error}")
    
    def delete_security_group(self, group_name: str = "lerobot-training") -> bool:
        """
        Delete security group.
        
        Args:
            group_name: Security group name
            
        Returns:
            True if successful
        """
        try:
            response = self.ec2.describe_security_groups(GroupNames=[group_name])
            sg_id = response['SecurityGroups'][0]['GroupId']
            
            logger.info(f"Deleting security group '{group_name}'...")
            self.ec2.delete_security_group(GroupId=sg_id)
            logger.info(f"✓ Security group deleted")
            return True
        except Exception as e:
            logger.warning(f"Could not delete security group: {e}")
            return False
    
    def delete_key_pair(self, key_name: str = "lerobot-training-key") -> bool:
        """
        Delete EC2 key pair.
        
        Args:
            key_name: Key pair name
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Deleting key pair '{key_name}'...")
            self.ec2.delete_key_pair(KeyName=key_name)
            logger.info(f"✓ Key pair deleted")
            return True
        except Exception as e:
            logger.warning(f"Could not delete key pair: {e}")
            return False