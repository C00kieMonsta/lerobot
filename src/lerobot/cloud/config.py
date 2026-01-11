from dataclasses import dataclass

@dataclass
class CloudTrainConfig:
    # AWS
    aws_profile: str = "default"
    aws_region: str = "us-east-1"
    
    # EC2
    instance_type: str = "g5.xlarge"
    ami_id: str = None  # Deep Learning AMI ID
    security_group: str = "lerobot-training"
    storage_gb: int = 50
    
    # Training
    dataset_repo_id: str = None
    policy_type: str = "act"
    batch_size: int = 32
    steps: int = 100000
    
    # Hugging Face
    hf_token: str = None
    push_to_hub: bool = True
