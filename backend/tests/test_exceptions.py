"""
test_exceptions.py
"""
from ateme.um_backend.exceptions import CheckRemoteIPInvalid


def test_check_remote_ip_invalid():
    """Test CheckRemoteIPInvalid exception
    """
    exception = CheckRemoteIPInvalid("John", "local", "127.0.0.1", "172.29.3.27")
    assert str(exception) == "remote ip invalid: 127.0.0.1 != 172.29.3.27"
    assert exception.activity_message == "wrong remote IP address 127.0.0.1 (expected 172.29.3.27)"
    assert exception.activity_extra == {"user": "John:local"}
