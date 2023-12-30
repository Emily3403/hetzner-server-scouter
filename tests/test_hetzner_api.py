from typing import Any

import pytest

from conftest import MockProgramsArgs
from hetzner_server_scouter.db.crud import download_server_list
from hetzner_server_scouter.db.models import Server
from hetzner_server_scouter.settings import Datacenters
from hetzner_server_scouter.utils import flat_map, get_hetzner_ipv4_price


def test_data_specials(data: dict[str, Any]) -> None:
    assert set(flat_map(lambda it: it["specials"], data["server"])) == {'IPv4', 'GPU', 'iNIC', 'ECC', 'HWR'}


def test_ipv4_price() -> None:
    price = get_hetzner_ipv4_price()
    assert price is not None
    assert 1 < price < 10


def test_data_datacenters(data: dict[str, Any]) -> None:
    assert set(flat_map(lambda it: [it["datacenter"][:3]], data["server"])) == {"FSN", "NBG", "HEL"}


class HetznerTest:
    def __init__(self, environments: list[dict[str, Any]]) -> None:
        self.environments = environments

    async def download_servers(self) -> list[list[Server]]:
        all_servers = []
        for env in self.environments:
            with MockProgramsArgs(**env):
                servers = await download_server_list()
                assert servers is not None
                all_servers.append(servers)

        # Check if the number of the servers per environment is always increasing
        assert all(len(a) <= len(b) for a, b in zip(all_servers, all_servers[1:]))
        return all_servers


@pytest.mark.asyncio
async def test_download_servers_price(data: dict[str, Any]) -> None:
    servers = await HetznerTest([{"price": 50}, {"price": 100}]).download_servers()
    assert all(server.calculate_price() <= 50 for server in servers[0])
    assert all(server.calculate_price() <= 100 for server in servers[1])


@pytest.mark.asyncio
async def test_download_servers__datacenter(data: dict[str, Any]) -> None:
    servers = await HetznerTest([{"datacenter": "FSN"}, {"datacenter": ["FSN", "NBG"]}, {"datacenter": ["FSN", "NBG", "HEL"]}]).download_servers()
    assert all(server.datacenter == Datacenters.frankfurt for server in servers[0])
    assert all(server.datacenter in {Datacenters.frankfurt, Datacenters.nurnberg} for server in servers[1])
    assert all(server.datacenter in {Datacenters.frankfurt, Datacenters.nurnberg, Datacenters.helsinki} for server in servers[2])


@pytest.mark.asyncio
async def test_download_servers_datacenter(data: dict[str, Any]) -> None:
    with MockProgramsArgs(datacenter="FSN"):
        servers1 = await download_server_list(data)
        assert servers1 is not None
        assert all(server.datacenter == Datacenters.frankfurt for server in servers1)

    with MockProgramsArgs(datacenter=["FSN", "NBG"]):
        servers2 = await download_server_list(data)
        assert servers2 is not None
        assert all(server.datacenter in {Datacenters.frankfurt, Datacenters.nurnberg} for server in servers2)

    assert len(servers1) < len(servers2)
