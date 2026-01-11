"""SSH tunnel for remote command execution on EC2 instances."""

import logging
import time
import paramiko
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class SSHTunnel:
    """SSH client for executing commands on EC2 instances."""
    
    def __init__(
        self,
        host: str,
        username: str = "ubuntu",
        key_path: Optional[str] = None,
        port: int = 22,
        timeout: int = 30,
    ):
        """
        Initialize SSH tunnel.
        
        Args:
            host: EC2 instance IP or hostname
            username: SSH username (default: ubuntu for AWS AMIs)
            key_path: Path to private SSH key
            port: SSH port (default: 22)
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.username = username
        self.key_path = key_path or str(Path.home() / ".ssh" / "id_rsa")
        self.port = port
        self.timeout = timeout
        self.client = None
        self.sftp = None
    
    def connect(self, max_retries: int = 5, retry_delay: int = 5) -> bool:
        """
        Connect to EC2 instance via SSH.
        
        Args:
            max_retries: Number of connection attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            True if successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                logger.info(f"Connecting to {self.host}:{self.port} (attempt {attempt + 1}/{max_retries})")
                
                self.client.connect(
                    hostname=self.host,
                    username=self.username,
                    key_filename=self.key_path,
                    port=self.port,
                    timeout=self.timeout,
                    banner_timeout=self.timeout,
                )
                
                logger.info(f"✓ Connected to {self.host}")
                self.sftp = self.client.open_sftp()
                return True
                
            except (paramiko.ssh_exception.NoValidConnectionsError, 
                    paramiko.ssh_exception.SSHException,
                    ConnectionRefusedError,
                    OSError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection failed: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to connect after {max_retries} attempts: {e}")
                    return False
        
        return False
    
    def execute_command(
        self,
        command: str,
        stream_output: bool = True,
    ) -> Tuple[int, str, str]:
        """
        Execute command on remote instance.
        
        Args:
            command: Command to execute
            stream_output: If True, print output as it arrives
            
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if self.client is None:
            raise RuntimeError("Not connected. Call connect() first.")
        
        logger.info(f"Executing: {command}")
        
        stdin, stdout, stderr = self.client.exec_command(command, timeout=None)
        
        stdout_text = ""
        stderr_text = ""
        
        # Read output in real-time
        for line in stdout:
            line_str = line.rstrip('\n')
            stdout_text += line + '\n'
            if stream_output:
                print(line_str)
        
        for line in stderr:
            line_str = line.rstrip('\n')
            stderr_text += line + '\n'
            if stream_output:
                print(f"[ERROR] {line_str}")
        
        exit_code = stdout.channel.recv_exit_status()
        
        if exit_code != 0:
            logger.warning(f"Command failed with exit code {exit_code}")
        
        return exit_code, stdout_text, stderr_text
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        Upload file to remote instance.
        
        Args:
            local_path: Local file path
            remote_path: Remote file path
            
        Returns:
            True if successful
        """
        if self.sftp is None:
            raise RuntimeError("Not connected. Call connect() first.")
        
        try:
            logger.info(f"Uploading {local_path} → {remote_path}")
            self.sftp.put(local_path, remote_path)
            logger.info("✓ Upload complete")
            return True
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Download file from remote instance.
        
        Args:
            remote_path: Remote file path
            local_path: Local file path
            
        Returns:
            True if successful
        """
        if self.sftp is None:
            raise RuntimeError("Not connected. Call connect() first.")
        
        try:
            logger.info(f"Downloading {remote_path} → {local_path}")
            self.sftp.get(remote_path, local_path)
            logger.info("✓ Download complete")
            return True
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False
    
    def close(self):
        """Close SSH connection."""
        if self.sftp:
            self.sftp.close()
        if self.client:
            self.client.close()
        logger.info("SSH connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()