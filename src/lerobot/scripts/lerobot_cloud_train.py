import typer
from lerobot.cloud.aws_client import AWSClient
from lerobot.cloud.ec2_manager import EC2Manager
from lerobot.cloud.ssh_tunnel import SSHTunnel

app = typer.Typer()

@app.command()
def launch(
    instance_type: str = typer.Option("g5.xlarge"),
    profile: str = typer.Option("default"),
):
    """Launch EC2 instance"""
    client = AWSClient(profile)
    client.login()
    manager = EC2Manager(client)
    instance_id = manager.launch_instance(instance_type, ami_id="ami-xxxxx")
    print(f"Instance launched: {instance_id}")

@app.command()
def train(
    instance_id: str = typer.Option(...),
    dataset_repo_id: str = typer.Option(...),
    policy_type: str = typer.Option("act"),
    steps: int = typer.Option(100000),
):
    """Run training on EC2 instance"""
    pass

@app.command()
def terminate(instance_id: str = typer.Option(...)):
    """Terminate EC2 instance"""
    pass

if __name__ == "__main__":
    app()
