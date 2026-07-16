"""Test const module."""
from custom_components.bwt_perla.const import DOMAIN


def test_domain_constant():
    """Test that DOMAIN constant is defined."""
    assert DOMAIN == "bwt_perla"
