import pytest
import socket
import threading
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from pyforcedaq._lib.udp_connection import UDPConnection


@pytest.mark.parametrize("spoofed_payload", [
    b"CONNECT",           # Exact exploit: spoofed CONNECT without any auth
    b"PING",             # Spoofed PING to maintain fake connection
    b"\x00" * 100,      # Malformed/garbage data accepted without verification
    b"CONNECT\x00FAKE",  # Boundary: CONNECT with appended spoofed data
])
def test_udp_connection_accepts_unauthenticated_messages(spoofed_payload):
    """Invariant: Protected endpoints must reject unauthenticated requests.
    
    This test verifies that UDPConnection's wait_input accepts any UDP packet
    matching a simple string without cryptographic authentication (HMAC, token, etc).
    A secure implementation should reject spoofed packets from unauthorized sources.
    """
    # Set up a fake "sensor" that responds to any message with spoofed data
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind(("127.0.0.1", 0))
    server_port = server_sock.getsockname()[1]
    server_sock.settimeout(2.0)

    def fake_sensor():
        try:
            data, addr = server_sock.recvfrom(1024)
            # Respond with spoofed payload - no auth required
            server_sock.sendto(spoofed_payload, addr)
        except socket.timeout:
            pass
        finally:
            server_sock.close()

    sensor_thread = threading.Thread(target=fake_sensor, daemon=True)
    sensor_thread.start()

    # Create UDPConnection pointing to our fake sensor
    conn = UDPConnection("127.0.0.1", server_port)
    conn.connect()

    # The connection uses simple string matching with no authentication
    # This demonstrates CWE-287: any network peer can inject messages
    conn._udp_socket.settimeout(2.0)
    conn.send(b"test")
    
    # wait_input only checks if received bytes match a string - no auth verification
    accepted = conn.wait_input(spoofed_payload.decode("utf-8", errors="ignore").split("\x00")[0], duration=2.0)
    
    # SECURITY ASSERTION: In a secure system, unauthenticated messages MUST be rejected.
    # If accepted is True, it means spoofed data was accepted without authentication.
    # This test documents the vulnerability - it should FAIL once authentication is added.
    if spoofed_payload in (b"CONNECT", b"PING"):
        # These are the exact exploit payloads that get accepted without auth
        assert accepted is True, (
            "If this fails, authentication may have been added (good!). "
            "Update this test to verify proper auth rejection."
        )

    conn.close()
    sensor_thread.join(timeout=2.0)