"""
Security Test Suite for GraphMemory-IDE

This module contains comprehensive security tests for container hardening,
mTLS implementation, and security configurations.
"""

import pytest
import ssl
import socket
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import docker
    from docker.errors import NotFound
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    NotFound = Exception
    DOCKER_AVAILABLE = False

# Test configuration
CONTAINER_PREFIX = "docker"
MCP_CONTAINER_NAME = f"{CONTAINER_PREFIX}-mcp-server-1"
KESTRA_CONTAINER_NAME = f"{CONTAINER_PREFIX}-kestra-1"
MTLS_PORT = 50051
HTTP_PORT = 8080
CERT_DIR = Path("./certs")


class TestContainerSecurity:
    """Test container security hardening features"""
    
    @pytest.fixture(scope="class")
    def docker_client(self) -> None:
        """Docker client fixture"""
        if not DOCKER_AVAILABLE or docker is None:
            pytest.skip("Docker library not available")
        return docker.from_env()
    
    @pytest.fixture(scope="class")
    def mcp_container(self, docker_client) -> None:
        """MCP server container fixture"""
        try:
            return docker_client.containers.get(MCP_CONTAINER_NAME)
        except NotFound:
            pytest.skip(f"Container {MCP_CONTAINER_NAME} not found")
    
    @pytest.fixture(scope="class")
    def kestra_container(self, docker_client) -> None:
        """Kestra container fixture"""
        try:
            return docker_client.containers.get(KESTRA_CONTAINER_NAME)
        except NotFound:
            pytest.skip(f"Container {KESTRA_CONTAINER_NAME} not found")
    
    def test_container_runs_as_non_root(self, mcp_container, kestra_container) -> None:
        """Test that containers run as non-root user"""
        # Test MCP server container
        result = mcp_container.exec_run("id -u")
        uid = int(result.output.decode().strip())
        assert uid != 0, f"MCP container should not run as root (UID 0), got UID {uid}"
        assert uid == 1000, f"MCP container should run as UID 1000, got UID {uid}"
        
        # Test Kestra container
        result = kestra_container.exec_run("id -u")
        uid = int(result.output.decode().strip())
        assert uid != 0, f"Kestra container should not run as root (UID 0), got UID {uid}"
        assert uid == 1001, f"Kestra container should run as UID 1001, got UID {uid}"
    
    def test_container_filesystem_readonly(self, mcp_container, kestra_container) -> None:
        """Test that container filesystem is read-only"""
        # Test MCP server container
        result = mcp_container.exec_run("touch /test-file")
        assert result.exit_code != 0, "MCP container root filesystem should be read-only"
        
        # Test Kestra container
        result = kestra_container.exec_run("touch /test-file")
        assert result.exit_code != 0, "Kestra container root filesystem should be read-only"
    
    def test_container_writable_volumes(self, mcp_container) -> None:
        """Test that designated writable volumes work"""
        # Test writable log directory
        result = mcp_container.exec_run("touch /var/log/mcp/test.log")
        assert result.exit_code == 0, "Should be able to write to log directory"
        
        # Test writable temp directory
        result = mcp_container.exec_run("touch /tmp/mcp/test.tmp")
        assert result.exit_code == 0, "Should be able to write to temp directory"
        
        # Clean up
        mcp_container.exec_run("rm -f /var/log/mcp/test.log /tmp/mcp/test.tmp")
    
    def test_container_capabilities_dropped(self, mcp_container, kestra_container) -> None:
        """Test that dangerous capabilities are dropped"""
        # Test MCP server container
        result = mcp_container.exec_run("cat /proc/self/status | grep CapEff")
        caps_output = result.output.decode()
        
        # Should have minimal capabilities (only NET_BIND_SERVICE = 0x400)
        assert "CapEff:\t0000000000000000" in caps_output or \
               "CapEff:\t0000000000000400" in caps_output, \
               f"MCP container should have minimal capabilities, got: {caps_output}"
        
        # Test Kestra container
        result = kestra_container.exec_run("cat /proc/self/status | grep CapEff")
        caps_output = result.output.decode()
        
        # Should have no capabilities
        assert "CapEff:\t0000000000000000" in caps_output, \
               f"Kestra container should have no capabilities, got: {caps_output}"
    
    def test_container_security_options(self, docker_client, mcp_container, kestra_container) -> None:
        """Test container security options"""
        # Test MCP server container
        mcp_inspect = docker_client.api.inspect_container(mcp_container.id)
        host_config = mcp_inspect['HostConfig']
        
        # Check read-only root filesystem
        assert host_config['ReadonlyRootfs'] is True, "MCP container should have read-only root filesystem"
        
        # Check security options
        security_opts = host_config.get('SecurityOpt', [])
        assert any('no-new-privileges:true' in opt for opt in security_opts), \
               "MCP container should have no-new-privileges enabled"
        assert any('seccomp:' in opt for opt in security_opts), \
               "MCP container should have seccomp profile applied"
        
        # Check capabilities
        assert host_config['CapDrop'] == ['ALL'], "MCP container should drop all capabilities"
        assert 'NET_BIND_SERVICE' in host_config.get('CapAdd', []), \
               "MCP container should add NET_BIND_SERVICE capability"
        
        # Test Kestra container
        kestra_inspect = docker_client.api.inspect_container(kestra_container.id)
        kestra_host_config = kestra_inspect['HostConfig']
        
        # Check read-only root filesystem
        assert kestra_host_config['ReadonlyRootfs'] is True, "Kestra container should have read-only root filesystem"
        
        # Check security options
        kestra_security_opts = kestra_host_config.get('SecurityOpt', [])
        assert any('no-new-privileges:true' in opt for opt in kestra_security_opts), \
               "Kestra container should have no-new-privileges enabled"
    
    def test_container_resource_limits(self, docker_client, mcp_container, kestra_container) -> None:
        """Test container resource limits"""
        # Test MCP server container
        mcp_inspect = docker_client.api.inspect_container(mcp_container.id)
        host_config = mcp_inspect['HostConfig']
        
        # Check memory limit (1GB = 1073741824 bytes)
        memory_limit = host_config.get('Memory', 0)
        assert memory_limit > 0, "MCP container should have memory limit set"
        assert memory_limit <= 1073741824, f"MCP container memory limit should be <= 1GB, got {memory_limit}"
        
        # Check CPU limit
        nano_cpus = host_config.get('NanoCpus', 0)
        if nano_cpus > 0:
            cpu_limit = nano_cpus / 1000000000  # Convert to CPU cores
            assert cpu_limit <= 0.5, f"MCP container CPU limit should be <= 0.5 cores, got {cpu_limit}"
        
        # Test Kestra container
        kestra_inspect = docker_client.api.inspect_container(kestra_container.id)
        kestra_host_config = kestra_inspect['HostConfig']
        
        # Check memory limit (2GB = 2147483648 bytes)
        kestra_memory_limit = kestra_host_config.get('Memory', 0)
        assert kestra_memory_limit > 0, "Kestra container should have memory limit set"
        assert kestra_memory_limit <= 2147483648, f"Kestra container memory limit should be <= 2GB, got {kestra_memory_limit}"
    
    def test_container_no_privileged_mode(self, docker_client, mcp_container, kestra_container) -> None:
        """Test that containers are not running in privileged mode"""
        # Test MCP server container
        mcp_inspect = docker_client.api.inspect_container(mcp_container.id)
        assert not mcp_inspect['HostConfig'].get('Privileged', False), \
               "MCP container should not run in privileged mode"
        
        # Test Kestra container
        kestra_inspect = docker_client.api.inspect_container(kestra_container.id)
        assert not kestra_inspect['HostConfig'].get('Privileged', False), \
               "Kestra container should not run in privileged mode"
    
    def test_container_health_checks(self, mcp_container, kestra_container) -> None:
        """Test that containers have health checks configured"""
        # Wait for health checks to complete
        time.sleep(10)
        
        # Test MCP server container health
        mcp_container.reload()
        health_status = mcp_container.attrs['State'].get('Health', {}).get('Status')
        assert health_status in ['healthy', 'starting'], \
               f"MCP container should be healthy, got status: {health_status}"
        
        # Test Kestra container health
        kestra_container.reload()
        kestra_health_status = kestra_container.attrs['State'].get('Health', {}).get('Status')
        assert kestra_health_status in ['healthy', 'starting'], \
               f"Kestra container should be healthy, got status: {kestra_health_status}"


class TestMTLSImplementation:
    """Test mTLS implementation and certificate management"""
    
    def test_certificate_files_exist(self) -> None:
        """Test that certificate files exist if mTLS is enabled"""
        if not os.getenv("MTLS_ENABLED", "false").lower() == "true":
            pytest.skip("mTLS not enabled")
        
        # Check required certificate files
        required_files = [
            CERT_DIR / "ca-cert.pem",
            CERT_DIR / "server-cert.pem",
            CERT_DIR / "server-key.pem",
            CERT_DIR / "client-cert.pem",
            CERT_DIR / "client-key.pem"
        ]
        
        for cert_file in required_files:
            assert cert_file.exists(), f"Required certificate file not found: {cert_file}"
    
    def test_certificate_permissions(self) -> None:
        """Test certificate file permissions"""
        if not os.getenv("MTLS_ENABLED", "false").lower() == "true":
            pytest.skip("mTLS not enabled")
        
        # Check private key permissions (should be 400)
        private_keys = [
            CERT_DIR / "ca-key.pem",
            CERT_DIR / "server-key.pem",
            CERT_DIR / "client-key.pem"
        ]
        
        for key_file in private_keys:
            if key_file.exists():
                stat = key_file.stat()
                permissions = stat.st_mode & 0o777
                assert permissions == 0o400, \
                       f"Private key {key_file} should have 400 permissions, got {oct(permissions)}"
        
        # Check certificate permissions (should be 444)
        certificates = [
            CERT_DIR / "ca-cert.pem",
            CERT_DIR / "server-cert.pem",
            CERT_DIR / "client-cert.pem"
        ]
        
        for cert_file in certificates:
            if cert_file.exists():
                stat = cert_file.stat()
                permissions = stat.st_mode & 0o777
                assert permissions == 0o444, \
                       f"Certificate {cert_file} should have 444 permissions, got {oct(permissions)}"
    
    def test_certificate_validation(self) -> None:
        """Test certificate chain validation"""
        if not os.getenv("MTLS_ENABLED", "false").lower() == "true":
            pytest.skip("mTLS not enabled")
        
        # Validate server certificate
        result = subprocess.run([
            "openssl", "verify", "-CAfile", str(CERT_DIR / "ca-cert.pem"),
            str(CERT_DIR / "server-cert.pem")
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Server certificate validation failed: {result.stderr}"
        assert "OK" in result.stdout, "Server certificate should be valid"
        
        # Validate client certificate
        result = subprocess.run([
            "openssl", "verify", "-CAfile", str(CERT_DIR / "ca-cert.pem"),
            str(CERT_DIR / "client-cert.pem")
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Client certificate validation failed: {result.stderr}"
        assert "OK" in result.stdout, "Client certificate should be valid"
    
    def test_mtls_port_accessibility(self) -> None:
        """Test mTLS port accessibility"""
        if not os.getenv("MTLS_ENABLED", "false").lower() == "true":
            pytest.skip("mTLS not enabled")
        
        # Test that mTLS port is listening
        try:
            with socket.create_connection(("localhost", MTLS_PORT), timeout=5):
                pass  # Connection successful
        except (ConnectionRefusedError, socket.timeout):
            pytest.fail(f"mTLS port {MTLS_PORT} is not accessible")
    
    def test_mtls_connection_with_client_cert(self) -> None:
        """Test mTLS connection with client certificate"""
        if not os.getenv("MTLS_ENABLED", "false").lower() == "true":
            pytest.skip("mTLS not enabled")
        
        # Create SSL context with client certificate
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_cert_chain(
            str(CERT_DIR / "client-cert.pem"),
            str(CERT_DIR / "client-key.pem")
        )
        context.load_verify_locations(str(CERT_DIR / "ca-cert.pem"))
        
        # Test connection
        try:
            with socket.create_connection(("localhost", MTLS_PORT), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname="mcp-server") as ssock:
                    peer_cert = ssock.getpeercert()
                    assert peer_cert is not None, "Should receive server certificate"
                    
                    # Verify server certificate subject
                    subject = {x[0][0]: x[0][1] for x in peer_cert['subject']}
                    assert subject.get('commonName') == 'mcp-server', \
                           f"Server certificate CN should be 'mcp-server', got {subject.get('commonName')}"
        except Exception as e:
            pytest.fail(f"mTLS connection failed: {e}")
    
    def test_mtls_connection_without_client_cert_fails(self) -> None:
        """Test that mTLS connection fails without client certificate"""
        if not os.getenv("MTLS_ENABLED", "false").lower() == "true":
            pytest.skip("mTLS not enabled")
        
        # Create SSL context without client certificate
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(str(CERT_DIR / "ca-cert.pem"))
        
        # Test connection should fail
        with pytest.raises(Exception):  # Can be SSLError or ConnectionResetError
            with socket.create_connection(("localhost", MTLS_PORT), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname="mcp-server") as ssock:
                    ssock.getpeercert()


class TestNetworkSecurity:
    """Test network security configurations"""
    
    def test_http_endpoint_accessible(self) -> None:
        """Test that HTTP endpoint is accessible"""
        try:
            import requests
            response = requests.get(f"http://localhost:{HTTP_PORT}/docs", timeout=10)
            assert response.status_code == 200, f"HTTP endpoint should be accessible, got status {response.status_code}"
        except ImportError:
            pytest.skip("requests library not available")
        except Exception as e:
            pytest.fail(f"HTTP endpoint not accessible: {e}")
    
    def test_container_network_isolation(self, docker_client) -> None:
        """Test container network isolation"""
        # Get network information
        networks = docker_client.networks.list(names=["docker_memory-net"])
        assert len(networks) > 0, "memory-net network should exist"
        
        memory_net = networks[0]
        network_config = memory_net.attrs['IPAM']['Config'][0]
        
        # Verify network subnet
        assert 'Subnet' in network_config, "Network should have subnet configured"
        subnet = network_config['Subnet']
        assert subnet.startswith('172.20.'), f"Network should use 172.20.x.x subnet, got {subnet}"
    
    def test_no_docker_socket_exposure(self, docker_client, kestra_container) -> None:
        """Test that Docker socket is not exposed to containers"""
        # Check Kestra container mounts
        kestra_inspect = docker_client.api.inspect_container(kestra_container.id)
        mounts = kestra_inspect.get('Mounts', [])
        
        # Should not have Docker socket mounted
        docker_socket_mounted = any(
            mount.get('Source') == '/var/run/docker.sock' 
            for mount in mounts
        )
        assert not docker_socket_mounted, "Docker socket should not be mounted in Kestra container"


class TestSecurityMonitoring:
    """Test security monitoring and logging"""
    
    def test_security_monitoring_script_exists(self) -> None:
        """Test that security monitoring script exists and is executable"""
        monitor_script = Path("monitoring/resource-monitor.sh")
        assert monitor_script.exists(), "Resource monitor script should exist"
        
        # Check if script is executable
        stat = monitor_script.stat()
        assert stat.st_mode & 0o111, "Resource monitor script should be executable"
    
    def test_security_monitoring_script_runs(self) -> None:
        """Test that security monitoring script runs successfully"""
        monitor_script = Path("monitoring/resource-monitor.sh")
        if not monitor_script.exists():
            pytest.skip("Resource monitor script not found")
        
        # Run the monitoring script
        result = subprocess.run([str(monitor_script)], capture_output=True, text=True, timeout=30)
        
        # Script should complete successfully
        assert result.returncode == 0, f"Monitoring script failed: {result.stderr}"
        
        # Should contain expected output sections
        output = result.stdout
        assert "Container Resource Usage" in output, "Should show container resource usage"
        assert "Container Security Status" in output, "Should show security status"
        assert "Volume Usage" in output, "Should show volume usage"
    
    def test_log_file_creation(self) -> None:
        """Test that monitoring creates log files"""
        # Run monitoring script to create logs
        monitor_script = Path("monitoring/resource-monitor.sh")
        if monitor_script.exists():
            subprocess.run([str(monitor_script)], capture_output=True, timeout=30)
        
        # Check if log file was created
        log_file = Path("/tmp/resource-monitor.log")
        if log_file.exists():
            assert log_file.stat().st_size > 0, "Log file should not be empty"


# Test configuration and utilities
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment() -> None:
    """Setup test environment"""
    # Ensure Docker is available
    if not DOCKER_AVAILABLE or docker is None:
        pytest.skip("Docker library not available")
    
    try:
        docker.from_env().ping()
    except Exception:
        pytest.skip("Docker not available")
    
    # Make monitoring script executable
    monitor_script = Path("monitoring/resource-monitor.sh")
    if monitor_script.exists():
        monitor_script.chmod(0o755)


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"]) 