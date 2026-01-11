class SSHTunnel:
    def __init__(self, host: str, username: str = "ubuntu", key_path: str = None):
        self.host = host
        self.username = username
        self.key_path = key_path
    
    def connect(self) -> bool:
        """Connect to EC2 instance"""
        pass
    
    def execute_command(self, command: str) -> tuple[int, str, str]:
        """Run command, return (exit_code, stdout, stderr)"""
        pass
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload file to instance"""
        pass
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file from instance"""
        pass
    
    def close(self):
        """Disconnect"""
        pass
