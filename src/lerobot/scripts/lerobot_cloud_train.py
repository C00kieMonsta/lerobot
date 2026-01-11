"""LeRobot cloud training command-line interface."""

import typer
from lerobot.cloud.aws_client import AWSClient
from lerobot.cloud.ec2_manager import EC2Manager
from typing import Optional
import sys

app = typer.Typer(help="Train LeRobot policies on cloud GPUs using AWS")


@app.command()
def quickstart():
    """Interactive quickstart guide for cloud training."""
    typer.echo("""
╭─────────────────────────────────────────────────────────────────────╮
│              LeRobot Cloud Training - Quickstart Guide              │
╰─────────────────────────────────────────────────────────────────────╯

This guide will help you set up and run training on AWS EC2 in 5 steps:

1️⃣  LAUNCH EC2 INSTANCE
   lerobot-cloud-train launch [OPTIONS]
   
   Example:
   $ lerobot-cloud-train launch --profile dev --region us-east-1
   
   Note: You'll get an instance ID (e.g., i-0123456789abcdef0)

2️⃣  RUN TRAINING
   lerobot-cloud-train train \\
     --instance-id <your-instance-id> \\
     --dataset-repo-id <hugging-face-repo> \\
     --policy-type act \\
     --batch-size 4 \\
     --steps 100000 \\
     --profile dev
     
   Example:
   $ lerobot-cloud-train train \\
     --instance-id i-0123456789abcdef0 \\
     --dataset-repo-id C00kieMonsta/so101_stack_green_goblets_v1 \\
     --policy-type act \\
     --batch-size 4 \\
     --steps 100000

3️⃣  MONITOR TRAINING (in another terminal)
   lerobot-cloud-train status --instance-id <your-instance-id> --profile dev
   
   Or view logs in real-time:
   lerobot-cloud-train logs --instance-id <your-instance-id> --follow

4️⃣  DOWNLOAD RESULTS (after training completes)
   lerobot-cloud-train download \\
     --instance-id <your-instance-id> \\
     --output-dir ./results \\
     --profile dev

5️⃣  TERMINATE INSTANCE (when done)
   lerobot-cloud-train terminate \\
     --instance-id <your-instance-id> \\
     --profile dev \\
     --cleanup
     
   Note: --cleanup removes security group and SSH key pair

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 PROVEN CONFIGURATION (Tested & Working):
  • Instance: g5.xlarge (A10G 24GB, $1.21/hr)
  • Batch size: 4 (MAXIMUM for ACT - do NOT increase)
  • Steps: 10,000 for test (2.5 hrs, $3)
  • Steps: 100,000 for production (24 hrs, $30)

⚠️  CRITICAL WARNINGS:
  • batch_size > 4 WILL cause OOM on A10G
  • After OOM: Must terminate & launch fresh instance
  • Set phone timer to avoid forgetting to terminate
  • GPU charges continue until you terminate

💡 RECOMMENDED WORKFLOW:
  • Start with 10k steps test run ($3)
  • Monitor with: logs --follow
  • Download immediately when "End of training" appears
  • Terminate immediately after download

📖 FOR MORE HELP:
  $ lerobot-cloud-train <command> --help
    """)


@app.command()
def help_config():
    """Show training configuration recommendations."""
    typer.echo("""
╭─────────────────────────────────────────────────────────────────────╮
│            LeRobot Cloud Training - Configuration Guide             │
╰─────────────────────────────────────────────────────────────────────╯

✅ PROVEN WORKING CONFIGURATION (g5.xlarge A10G):

  --batch-size 4         (Do NOT increase - causes OOM)
  --num-workers 0        (Auto-set, required for video)
  --policy.use_amp=true  (Auto-set, reduces memory)
  --dataset.video_backend=pyav  (Auto-set, reliable)

⚠️  CRITICAL: For ACT policy with video data on A10G (24GB):
    • batch_size=4 is MAXIMUM (tested and proven)
    • batch_size=8 or 16 WILL cause OOM errors
    • After OOM: Must terminate and launch fresh instance
    • GPU memory is NOT released between failed attempts

TIME & COST (batch_size=4, g5.xlarge @ $1.21/hr):

  Steps     Time      Cost    Use Case
  ──────────────────────────────────────────
  2,500     40 min    $0.80   Quick validation
  10,000    2.5 hrs   $3.00   Test run
  50,000    12 hrs    $15.00  Good model
  100,000   24 hrs    $30.00  Full training (best practices)

RECOMMENDED WORKFLOW:

  1. Test with 10k steps first ($3, 2.5 hrs)
  2. If results look good, run 100k steps ($30, 24 hrs)
  3. Set phone timer for expected completion time
  4. Monitor with: lerobot-cloud-train logs --follow
  5. Download results immediately when done
  6. Terminate instance immediately to stop charges

EXAMPLE COMMANDS:

  Test run (10k steps):
  $ lerobot-cloud-train train \\
      --instance-id i-xxx \\
      --dataset-repo-id user/dataset \\
      --batch-size 4 \\
      --steps 10000 \\
      --profile dev

  Full training (100k steps):
  $ lerobot-cloud-train train \\
      --instance-id i-xxx \\
      --dataset-repo-id user/dataset \\
      --batch-size 4 \\
      --steps 100000 \\
      --profile dev

COMMON MISTAKES:

  ❌ Using batch_size > 4
     → Causes OOM on A10G with ACT policy
  
  ❌ Reusing instance after OOM
     → GPU memory stays allocated
     → Must terminate and launch fresh
  
  ❌ Forgetting to terminate
     → Ongoing charges accumulate
     → Set timer and terminate immediately
    """)


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
    num_workers: int = typer.Option(0, help="DataLoader num_workers (use 0 to avoid multiprocessing issues)"),
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
                num_workers=num_workers,
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


@app.command()
def download(
    instance_id: str = typer.Option(..., help="EC2 instance ID"),
    output_dir: str = typer.Option("outputs/cloud_training", help="Local output directory"),
    download_logs: bool = typer.Option(True, help="Download training logs"),
    download_checkpoints: bool = typer.Option(True, help="Download model checkpoints"),
    profile: str = typer.Option("default", help="AWS SSO profile"),
):
    """Download training results from EC2 instance."""
    try:
        from pathlib import Path
        from lerobot.cloud.ssh_tunnel import SSHTunnel
        
        key_path = str(Path.home() / ".ssh" / "lerobot-training-key.pem")
        
        # Get instance IP
        client = AWSClient(profile_name=profile)
        if not client.login():
            typer.echo("❌ Failed to login to AWS", err=True)
            raise typer.Exit(1)
        
        manager = EC2Manager(client)
        ip_address = manager.get_instance_ip(instance_id)
        
        if not ip_address:
            typer.echo(f"❌ Could not get IP for instance {instance_id}", err=True)
            raise typer.Exit(1)
        
        # Connect and download
        ssh = SSHTunnel(host=ip_address, username="ubuntu", key_path=key_path)
        if not ssh.connect():
            typer.echo("❌ Failed to connect via SSH", err=True)
            raise typer.Exit(1)
        
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            if download_logs:
                typer.echo("Downloading training logs...")
                exit_code, stdout, _ = ssh.execute_command(
                    "tar -czf ~/training_logs.tar.gz ~/training.log ~/setup.log 2>/dev/null && ls -lh ~/training_logs.tar.gz || echo 'No logs found'",
                    stream_output=False
                )
                if "training_logs.tar.gz" in stdout:
                    ssh.download_file("~/training_logs.tar.gz", f"{output_dir}/training_logs.tar.gz")
                    typer.echo(f"✓ Logs downloaded to {output_dir}/training_logs.tar.gz")
            
            if download_checkpoints:
                typer.echo("Downloading model checkpoints...")
                exit_code, stdout, _ = ssh.execute_command(
                    "ls -d ~/outputs/train/* 2>/dev/null | head -1",
                    stream_output=False
                )
                if stdout.strip():
                    checkpoint_dir = stdout.strip()
                    typer.echo(f"Found checkpoint at: {checkpoint_dir}")
                    ssh.download_file(checkpoint_dir, f"{output_dir}/checkpoint")
                    typer.echo(f"✓ Checkpoint downloaded to {output_dir}/checkpoint")
                else:
                    typer.echo("⚠ No checkpoints found on instance")
                    
        finally:
            ssh.close()
            
    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def logs(
    instance_id: str = typer.Option(..., help="EC2 instance ID"),
    follow: bool = typer.Option(False, help="Follow logs in real-time (Ctrl+C to exit)"),
    lines: int = typer.Option(50, help="Number of recent lines to show"),
    profile: str = typer.Option("default", help="AWS SSO profile"),
):
    """View training logs from EC2 instance."""
    try:
        from pathlib import Path
        from lerobot.cloud.ssh_tunnel import SSHTunnel
        import time
        
        key_path = str(Path.home() / ".ssh" / "lerobot-training-key.pem")
        
        # Get instance IP
        client = AWSClient(profile_name=profile)
        if not client.login():
            typer.echo("❌ Failed to login to AWS", err=True)
            raise typer.Exit(1)
        
        manager = EC2Manager(client)
        ip_address = manager.get_instance_ip(instance_id)
        
        if not ip_address:
            typer.echo(f"❌ Could not get IP for instance {instance_id}", err=True)
            raise typer.Exit(1)
        
        # Connect and tail logs
        ssh = SSHTunnel(host=ip_address, username="ubuntu", key_path=key_path)
        if not ssh.connect():
            typer.echo("❌ Failed to connect via SSH", err=True)
            raise typer.Exit(1)
        
        try:
            if follow:
                typer.echo(f"Following logs from {instance_id} (Ctrl+C to exit)...")
                try:
                    while True:
                        exit_code, stdout, _ = ssh.execute_command(
                            f"tail -{lines} ~/training.log 2>/dev/null || echo 'No log yet'",
                            stream_output=False
                        )
                        # Clear screen and print
                        print("\033[2J\033[H")  # Clear screen
                        typer.echo(stdout)
                        time.sleep(2)  # Update every 2 seconds
                except KeyboardInterrupt:
                    typer.echo("\nLog following stopped")
            else:
                exit_code, stdout, _ = ssh.execute_command(
                    f"tail -{lines} ~/training.log 2>/dev/null || echo 'No log yet'",
                    stream_output=False
                )
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


