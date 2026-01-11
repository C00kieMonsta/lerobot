"""Training orchestration on remote EC2 instances."""

import logging
import json
import time
from pathlib import Path
from typing import Optional
from lerobot.cloud.ssh_tunnel import SSHTunnel

logger = logging.getLogger(__name__)


class TrainingRunner:
    """Orchestrates training on a remote EC2 instance."""
    
    def __init__(self, ssh_tunnel: SSHTunnel):
        """
        Initialize training runner.
        
        Args:
            ssh_tunnel: Connected SSHTunnel instance
        """
        self.ssh = ssh_tunnel
    
    def setup_instance(self) -> bool:
        """
        Install LeRobot and dependencies on EC2 instance.
        
        Returns:
            True if successful
        """
        logger.info("Setting up EC2 instance...")
        
        # Update system packages
        logger.info("Updating system packages...")
        exit_code, _, _ = self.ssh.execute_command(
            "sudo apt-get update && sudo apt-get upgrade -y",
            stream_output=False
        )
        if exit_code != 0:
            logger.error("Failed to update system packages")
            return False
        
        # Install Python and pip
        logger.info("Installing Python dependencies...")
        exit_code, _, _ = self.ssh.execute_command(
            "sudo apt-get install -y python3.10 python3.10-venv python3-pip git",
            stream_output=False
        )
        if exit_code != 0:
            logger.error("Failed to install Python")
            return False
        
        # Create virtual environment
        logger.info("Creating Python virtual environment...")
        exit_code, _, _ = self.ssh.execute_command(
            "python3.10 -m venv ~/venv_lerobot",
            stream_output=False
        )
        if exit_code != 0:
            logger.error("Failed to create virtual environment")
            return False
        
        # Install LeRobot
        logger.info("Installing LeRobot (this may take several minutes)...")
        exit_code, stdout, stderr = self.ssh.execute_command(
            "source ~/venv_lerobot/bin/activate && pip install lerobot --timeout 600 2>&1 | tail -20",
            stream_output=True
        )
        if exit_code != 0:
            logger.error(f"Failed to install LeRobot. stdout: {stdout}, stderr: {stderr}")
            return False
        
        logger.info("✓ Instance setup complete")
        return True
    
    def run_training(
        self,
        dataset_repo_id: str,
        policy_type: str = "act",
        batch_size: int = 32,
        steps: int = 100000,
        hf_token: Optional[str] = None,
        policy_repo_id: Optional[str] = None,
    ) -> bool:
        """
        Run training on remote instance.
        
        Args:
            dataset_repo_id: Hugging Face dataset repo ID
            policy_type: Policy type (act, diffusion, etc.)
            batch_size: Training batch size
            steps: Number of training steps
            hf_token: Hugging Face API token
            policy_repo_id: Where to save trained model
            
        Returns:
            True if successful
        """
        logger.info(f"Starting training: {dataset_repo_id}")
        
        # Prepare training command arguments
        train_args = [
            f"--dataset.repo_id={dataset_repo_id}",
            f"--policy.type={policy_type}",
            f"--batch_size={batch_size}",
            f"--steps={steps}",
            f"--output_dir=outputs/train/{policy_type}_{dataset_repo_id.split('/')[-1]}",
            f"--job_name={policy_type}_{dataset_repo_id.split('/')[-1]}",
            "--policy.device=cuda",
            "--wandb.enable=false",
            "--dataset.video_backend=pyav",
            "--policy.push_to_hub=false",
        ]
        
        if hf_token:
            train_args.append(f'--hf_token="{hf_token}"')
        
        if policy_repo_id:
            train_args.append(f"--policy.repo_id={policy_repo_id}")
        else:
            # Use dataset repo id as default for policy repo
            train_args.append(f"--policy.repo_id={dataset_repo_id.rsplit('/', 1)[0]}/{policy_type}_{dataset_repo_id.split('/')[-1]}")
        
        # Build complete command with activation and training
        train_args_str = " ".join(train_args)
        training_cmd = f"source ~/venv_lerobot/bin/activate && lerobot-train {train_args_str}"
        
        # Run training
        logger.info("Running training (this may take hours)...")
        exit_code, stdout, stderr = self.ssh.execute_command(
            training_cmd,
            stream_output=True  # Stream logs in real-time
        )
        
        if exit_code == 0:
            logger.info("✓ Training completed successfully")
            return True
        else:
            logger.error(f"Training failed with exit code {exit_code}")
            return False
    
    def download_checkpoint(
        self,
        remote_checkpoint_dir: str,
        local_output_dir: str = "outputs/train",
    ) -> bool:
        """
        Download trained model from EC2 instance.
        
        Args:
            remote_checkpoint_dir: Path on EC2 instance
            local_output_dir: Local output directory
            
        Returns:
            True if successful
        """
        logger.info(f"Downloading checkpoint from {remote_checkpoint_dir}...")
        
        # Create local directory
        Path(local_output_dir).mkdir(parents=True, exist_ok=True)
        
        # Download via SCP (using SSH tunnel)
        # Note: paramiko's sftp.get() is recursive
        try:
            self.ssh.download_file(remote_checkpoint_dir, local_output_dir)
            logger.info("✓ Checkpoint downloaded")
            return True
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False
    
    def get_training_status(self) -> dict:
        """
        Get current training status from remote instance.
        
        Returns:
            Dictionary with status information
        """
        # Check if training process is running
        exit_code, stdout, _ = self.ssh.execute_command(
            "ps aux | grep lerobot-train | grep -v grep",
            stream_output=False
        )
        
        is_running = exit_code == 0 and stdout.strip() != ""
        
        return {
            "is_running": is_running,
            "timestamp": time.time(),
        }