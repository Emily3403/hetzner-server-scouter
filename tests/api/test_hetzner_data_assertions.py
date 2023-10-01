from typing import Any

from hetzner_server_scouter.utils import flat_map


def test_data_specials(data: dict[str, Any]) -> None:
    assert set(flat_map(lambda it: it["specials"], data["server"])) == {'IPv4', 'GPU', 'iNIC', 'ECC', 'HWR'}

# TODO: Datacenters
