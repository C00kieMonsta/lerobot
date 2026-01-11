class EC2Manager:
    def __init__(self, aws_client: AWSClient):
        self.aws_client = aws_client
    
    def launch_instance(self, instance_type: str, ami_id: str) -> str:
        """Launch EC2 instance, return instance_id"""
        pass
    
    def get_instance_status(self, instance_id: str) -> str:
        """Get instance status"""
        pass
    
    def get_instance_ip(self, instance_id: str) -> str:
        """Get public IP"""
        pass
    
    def terminate_instance(self, instance_id: str) -> bool:
        """Terminate instance"""
        pass
