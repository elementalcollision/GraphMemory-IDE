#!/usr/bin/env python3
"""Kestra decommission: excise the Kestra halves of tests/test_security.py."""
import sys
from pathlib import Path

ROOT = Path("/Users/dave/Claude_Primary/Graph_Memory")
p = ROOT / "tests/test_security.py"
t = p.read_text()

EDITS = [
    # container-name constant
    ('KESTRA_CONTAINER_NAME = f"{CONTAINER_PREFIX}-kestra-1"\n', ""),
    # class kestra fixture
    ('''    @pytest.fixture(scope="class")
    def kestra_container(self, docker_client) -> None:
        """Kestra container fixture"""
        try:
            return docker_client.containers.get(KESTRA_CONTAINER_NAME)
        except NotFound:
            pytest.skip(f"Container {KESTRA_CONTAINER_NAME} not found")
    
''', ""),
    # non-root
    ('''    def test_container_runs_as_non_root(self, mcp_container, kestra_container) -> None:
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
    ''',
     '''    def test_container_runs_as_non_root(self, mcp_container) -> None:
        """Test that containers run as non-root user"""
        # Test MCP server container
        result = mcp_container.exec_run("id -u")
        uid = int(result.output.decode().strip())
        assert uid != 0, f"MCP container should not run as root (UID 0), got UID {uid}"
        assert uid == 1000, f"MCP container should run as UID 1000, got UID {uid}"
    '''),
    # read-only fs
    ('''    def test_container_filesystem_readonly(self, mcp_container, kestra_container) -> None:
        """Test that container filesystem is read-only"""
        # Test MCP server container
        result = mcp_container.exec_run("touch /test-file")
        assert result.exit_code != 0, "MCP container root filesystem should be read-only"
        
        # Test Kestra container
        result = kestra_container.exec_run("touch /test-file")
        assert result.exit_code != 0, "Kestra container root filesystem should be read-only"
    ''',
     '''    def test_container_filesystem_readonly(self, mcp_container) -> None:
        """Test that container filesystem is read-only"""
        result = mcp_container.exec_run("touch /test-file")
        assert result.exit_code != 0, "MCP container root filesystem should be read-only"
    '''),
    # capabilities
    ('''    def test_container_capabilities_dropped(self, mcp_container, kestra_container) -> None:
        """Test that dangerous capabilities are dropped"""
        # Test MCP server container
        result = mcp_container.exec_run("cat /proc/self/status | grep CapEff")
        caps_output = result.output.decode()
        
        # Should have minimal capabilities (only NET_BIND_SERVICE = 0x400)
        assert "CapEff:\\t0000000000000000" in caps_output or \\
               "CapEff:\\t0000000000000400" in caps_output, \\
               f"MCP container should have minimal capabilities, got: {caps_output}"
        
        # Test Kestra container
        result = kestra_container.exec_run("cat /proc/self/status | grep CapEff")
        caps_output = result.output.decode()
        
        # Should have no capabilities
        assert "CapEff:\\t0000000000000000" in caps_output, \\
               f"Kestra container should have no capabilities, got: {caps_output}"
    ''',
     '''    def test_container_capabilities_dropped(self, mcp_container) -> None:
        """Test that dangerous capabilities are dropped"""
        result = mcp_container.exec_run("cat /proc/self/status | grep CapEff")
        caps_output = result.output.decode()
        
        # Should have minimal capabilities (only NET_BIND_SERVICE = 0x400)
        assert "CapEff:\\t0000000000000000" in caps_output or \\
               "CapEff:\\t0000000000000400" in caps_output, \\
               f"MCP container should have minimal capabilities, got: {caps_output}"
    '''),
    # security options
    ('''        assert 'NET_BIND_SERVICE' in host_config.get('CapAdd', []), \\
               "MCP container should add NET_BIND_SERVICE capability"
        
        # Test Kestra container
        kestra_inspect = docker_client.api.inspect_container(kestra_container.id)
        kestra_host_config = kestra_inspect['HostConfig']
        
        # Check read-only root filesystem
        assert kestra_host_config['ReadonlyRootfs'] is True, "Kestra container should have read-only root filesystem"
        
        # Check security options
        kestra_security_opts = kestra_host_config.get('SecurityOpt', [])
        assert any('no-new-privileges:true' in opt for opt in kestra_security_opts), \\
               "Kestra container should have no-new-privileges enabled"
    ''',
     '''        assert 'NET_BIND_SERVICE' in host_config.get('CapAdd', []), \\
               "MCP container should add NET_BIND_SERVICE capability"
    '''),
    ('def test_container_security_options(self, docker_client, mcp_container, kestra_container) -> None:',
     'def test_container_security_options(self, docker_client, mcp_container) -> None:'),
    # resource limits
    ('''        # Check CPU limit
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
    ''',
     '''        # Check CPU limit
        nano_cpus = host_config.get('NanoCpus', 0)
        if nano_cpus > 0:
            cpu_limit = nano_cpus / 1000000000  # Convert to CPU cores
            assert cpu_limit <= 0.5, f"MCP container CPU limit should be <= 0.5 cores, got {cpu_limit}"
    '''),
    ('def test_container_resource_limits(self, docker_client, mcp_container, kestra_container) -> None:',
     'def test_container_resource_limits(self, docker_client, mcp_container) -> None:'),
    # privileged mode
    ('''        assert not mcp_inspect['HostConfig'].get('Privileged', False), \\
               "MCP container should not run in privileged mode"
        
        # Test Kestra container
        kestra_inspect = docker_client.api.inspect_container(kestra_container.id)
        assert not kestra_inspect['HostConfig'].get('Privileged', False), \\
               "Kestra container should not run in privileged mode"
    ''',
     '''        assert not mcp_inspect['HostConfig'].get('Privileged', False), \\
               "MCP container should not run in privileged mode"
    '''),
    ('def test_container_no_privileged_mode(self, docker_client, mcp_container, kestra_container) -> None:',
     'def test_container_no_privileged_mode(self, docker_client, mcp_container) -> None:'),
    # health checks
    ('''        # Test Kestra container health
        kestra_container.reload()
        kestra_health_status = kestra_container.attrs['State'].get('Health', {}).get('Status')
        assert kestra_health_status in ['healthy', 'starting'], \\
               f"Kestra container should be healthy, got status: {kestra_health_status}"
''', ""),
    ('''f"MCP container should be healthy, got status: {health_status}"
        
''',
     '''f"MCP container should be healthy, got status: {health_status}"
'''),
    ('def test_container_health_checks(self, mcp_container, kestra_container) -> None:',
     'def test_container_health_checks(self, mcp_container) -> None:'),
    # docker socket exposure: re-point from the removed kestra container to the MCP container
    ('''    def test_no_docker_socket_exposure(self, docker_client, kestra_container) -> None:
        """Test that Docker socket is not exposed to containers"""
        # Check Kestra container mounts
        kestra_inspect = docker_client.api.inspect_container(kestra_container.id)
        mounts = kestra_inspect.get('Mounts', [])
        
        # Should not have Docker socket mounted
        docker_socket_mounted = any(
            mount.get('Source') == '/var/run/docker.sock' 
            for mount in mounts
        )
        assert not docker_socket_mounted, "Docker socket should not be mounted in Kestra container"''',
     '''    def test_no_docker_socket_exposure(self, docker_client, mcp_container) -> None:
        """Test that Docker socket is not exposed to containers"""
        # Check MCP container mounts (the no-socket property holds for every service)
        mcp_inspect = docker_client.api.inspect_container(mcp_container.id)
        mounts = mcp_inspect.get('Mounts', [])
        
        # Should not have Docker socket mounted
        docker_socket_mounted = any(
            mount.get('Source') == '/var/run/docker.sock' 
            for mount in mounts
        )
        assert not docker_socket_mounted, "Docker socket should not be mounted in MCP container"'''),
]

for old, new in EDITS:
    if old not in t:
        print(f"ABORT: pattern not found:\n  {old[:100]!r}")
        sys.exit(1)
    t = t.replace(old, new)

import re
assert not re.search(r"kestra", t, re.I), "residual kestra in test_security.py"
p.write_text(t)
print("OK  tests/test_security.py — kestra excised, socket test re-pointed to MCP container")
