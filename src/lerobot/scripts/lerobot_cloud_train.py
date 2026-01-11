"""LeRobot cloud training command-line interface."""

import typer
from lerobot.cloud.aws_client import AWSClient
from lerobot.cloud.ec2_manager import EC2Manager
from typing import Optional

app = typer.Typer(help="Train LeRobot policies on cloud GPUs using AWS")


@app.command()
def launch(
    instance_type: str = typer.Option(
        "g5.xlarge",
        help="AWS EC2 instance type (g5.xlarge, g5.2xlarge, p3.2xlarge)"
    ),
    profile: str = typer.Option(
        "default",
        help="AWS SSO profile name"
    ),
    region: str = typer.Option(
        "us-east-1",
        help="AWS region"
    ),
):
    """Launch an EC2 instance for training."""
    typer.echo(f"Launching {instance_type} in {region}...")
    
    try:
        # Step 1: Login to AWS
        client = AWSClient(profile_name=profile, region=region)
        if not client.login():
            typer.echo("❌ Failed to login to AWS", err=True)
            raise typer.Exit(1)
        
        typer.echo(f"✓ Logged in successfully")
        
        # Step 2: Launch instance
        manager = EC2Manager(client)
        instance_id = manager.launch_instance(instance_type)
        
        typer.echo(f"✓ Instance launched: {instance_id}")
        typer.echo(f"Run 'lerobot-cloud-train train --instance-id {instance_id}' to start training")
        
    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def terminate(
    instance_id: str = typer.Option(..., help="EC2 instance ID to terminate"),
    profile: str = typer.Option("default", help="AWS SSO profile name"),
    cleanup: bool = typer.Option(True, help="Delete security group and key pair"),
):
    """Terminate an EC2 instance and optionally cleanup resources."""
    typer.echo(f"Terminating instance {instance_id}...")
    
    try:
        client = AWSClient(profile_name=profile)
        if not client.login():
            typer.echo("❌ Failed to login to AWS", err=True)
            raise typer.Exit(1)
        
        manager = EC2Manager(client)
        manager.terminate_instance(instance_id)
        typer.echo(f"✓ Instance terminated")
        
        if cleanup:
            typer.echo("Cleaning up resources...")
            client.delete_security_group("lerobot-training")
            client.delete_key_pair("lerobot-training-key")
            typer.echo("✓ Cleanup complete")
        
    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def train(
    instance_id: str = typer.Option(..., help="EC2 instance ID"),
    dataset_repo_id: str = typer.Option(..., help="Hugging Face dataset repo ID"),
    policy_type: str = typer.Option("act", help="Policy type (act, diffusion, etc.)"),
    batch_size: int = typer.Option(32, help="Training batch size"),
    steps: int = typer.Option(100000, help="Number of training steps"),
    policy_repo_id: Optional[str] = typer.Option(None, help="Model repo ID on Hugging Face"),
    profile: str = typer.Option("default", help="AWS SSO profile"),
    region: str = typer.Option("us-east-1", help="AWS region"),
    setup: bool = typer.Option(True, help="Setup instance before training"),
):
    """Run training on EC2 instance."""
    try:
        # Step 1: Get instance details
        client = AWSClient(profile_name=profile, region=region)
        if not client.login():
            typer.echo("❌ Failed to login to AWS", err=True)
            raise typer.Exit(1)
        
        manager = EC2Manager(client)
        
        typer.echo(f"Getting instance details for {instance_id}...")
        status = manager.get_instance_status(instance_id)
        ip_address = manager.get_instance_ip(instance_id)
        
        if status != "running":
            typer.echo(f"❌ Instance is not running (status: {status})", err=True)
            raise typer.Exit(1)
        
        if not ip_address:
            typer.echo("❌ Could not get instance IP address", err=True)
            raise typer.Exit(1)
        
        typer.echo(f"✓ Instance {instance_id} is running at {ip_address}")
        
        # Step 2: Connect via SSH
        typer.echo("Connecting via SSH...")
        from pathlib import Path
        from lerobot.cloud.ssh_tunnel import SSHTunnel
        from lerobot.cloud.training_runner import TrainingRunner
        
        key_path = str(Path.home() / ".ssh" / "lerobot-training-key.pem")
        ssh = SSHTunnel(host=ip_address, username="ubuntu", key_path=key_path)
        if not ssh.connect():
            typer.echo("❌ Failed to connect via SSH", err=True)
            raise typer.Exit(1)
        
        typer.echo("✓ SSH connected")
        
        try:
            # Step 3: Setup instance
            runner = TrainingRunner(ssh)
            
            if setup:
                typer.echo("\nSetting up instance...")
                if not runner.setup_instance():
                    typer.echo("❌ Instance setup failed", err=True)
                    raise typer.Exit(1)
                typer.echo("✓ Instance setup complete")
            
            # Step 4: Run training
            typer.echo(f"\nStarting training...")
            if not runner.run_training(
                dataset_repo_id=dataset_repo_id,
                policy_type=policy_type,
                batch_size=batch_size,
                steps=steps,
                policy_repo_id=policy_repo_id,
            ):
                typer.echo("❌ Training failed", err=True)
                raise typer.Exit(1)
            
            typer.echo("✓ Training completed!")
            
        finally:
            ssh.close()
            
    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def status(
    instance_id: str = typer.Option(..., help="EC2 instance ID"),
    profile: str = typer.Option("default", help="AWS SSO profile"),
):
    """Check training status on instance."""
    try:
        from pathlib import Path
        from lerobot.cloud.ssh_tunnel import SSHTunnel
        
        key_path = str(Path.home() / ".ssh" / "lerobot-training-key.pem")
        
        # Get instance IP
        from lerobot.cloud.aws_client import AWSClient
        from lerobot.cloud.ec2_manager import EC2Manager
        
        client = AWSClient(profile_name=profile)
        if not client.login():
            typer.echo("❌ Failed to login to AWS", err=True)
            raise typer.Exit(1)
        
        manager = EC2Manager(client)
        ip_address = manager.get_instance_ip(instance_id)
        
        if not ip_address:
            typer.echo(f"❌ Could not get IP for instance {instance_id}", err=True)
            raise typer.Exit(1)
        
        # Connect and check
        ssh = SSHTunnel(host=ip_address, username="ubuntu", key_path=key_path)
        if not ssh.connect():
            typer.echo("❌ Failed to connect via SSH", err=True)
            raise typer.Exit(1)
        
        try:
            # Check if training is running
            exit_code, stdout, _ = ssh.execute_command(
                "ps aux | grep 'lerobot-train' | grep -v grep",
                stream_output=False
            )
            
            if exit_code == 0 and stdout.strip():
                typer.echo("✓ Training is running")
                # Show recent log lines
                exit_code, stdout, _ = ssh.execute_command(
                    "tail -20 ~/training.log 2>/dev/null || echo 'No log yet'",
                    stream_output=False
                )
                typer.echo("\n--- Recent logs ---")
                typer.echo(stdout)
            else:
                typer.echo("⏸ Training is not running")
                # Show last log
                exit_code, stdout, _ = ssh.execute_command(
                    "tail -20 ~/training.log 2>/dev/null || echo 'No log yet'",
                    stream_output=False
                )
                typer.echo("\n--- Last logs ---")
                typer.echo(stdout)
        finally:
            ssh.close()
            
    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()


