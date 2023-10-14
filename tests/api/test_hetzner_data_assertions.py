from typing import Any

from hetzner_server_scouter.utils import flat_map, get_hetzner_ipv4_price


def test_data_specials(data: dict[str, Any]) -> None:
    assert set(flat_map(lambda it: it["specials"], data["server"])) == {'IPv4', 'GPU', 'iNIC', 'ECC', 'HWR'}


def test_ipv4_price() -> None:
    price = get_hetzner_ipv4_price()
    assert price is not None
    assert 1 < price < 10

# TODO: Datacenters
