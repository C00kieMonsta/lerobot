# Handle AWS authentication and basic operations
class AWSClient:
    def __init__(self, profile_name: str, region: str = "us-east-1"):
        self.profile_name = profile_name
        self.region = region
        self.session = None
        self.ec2_client = None
    
    def login(self) -> bool:
        """Verify AWS SSO login"""
        pass
    
    def get_account_id(self) -> str:
        """Get AWS account ID"""
        pass
