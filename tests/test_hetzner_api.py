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

    async def download_servers(self, data: dict[str, Any], increasing: bool | None = True) -> list[list[Server]]:
        all_servers = []
        for env in self.environments:
            with MockProgramsArgs(**env):
                servers = await download_server_list(data)
                assert servers is not None
                all_servers.append(servers)

        # Check if the number of the servers per environment is always increasing
        if increasing is True:
            assert all(len(a) <= len(b) for a, b in zip(all_servers, all_servers[1:]))
        elif increasing is False:
            assert all(len(a) >= len(b) for a, b in zip(all_servers, all_servers[1:]))

        return all_servers


@pytest.mark.asyncio
async def test_download_servers_price(data: dict[str, Any]) -> None:
    servers = await HetznerTest([{"price": 50}, {"price": 100}]).download_servers(data)
    assert all(server.calculate_price() <= 50 for server in servers[0])
    assert all(server.calculate_price() <= 100 for server in servers[1])


@pytest.mark.asyncio
async def test_download_servers_cpu(data: dict[str, Any]) -> None:
    servers = await HetznerTest([{"cpu": "intel"}, {"cpu": "amd"}, {"cpu": "8700"}]).download_servers(data, increasing=None)
    assert all("intel" in server.cpu_name.lower() for server in servers[0])
    assert all("amd" in server.cpu_name.lower() for server in servers[1])
    assert all("8700" in server.cpu_name.lower() for server in servers[2])


@pytest.mark.asyncio
async def test_download_servers_datacenter(data: dict[str, Any]) -> None:
    servers = await HetznerTest([{"datacenter": "FSN"}, {"datacenter": ["FSN", "NBG"]}, {"datacenter": ["FSN", "NBG", "HEL"]}]).download_servers(data)
    assert all(server.datacenter == Datacenters.frankfurt for server in servers[0])
    assert all(server.datacenter in {Datacenters.frankfurt, Datacenters.nurnberg} for server in servers[1])
    assert all(server.datacenter in {Datacenters.frankfurt, Datacenters.nurnberg, Datacenters.helsinki} for server in servers[2])


@pytest.mark.asyncio
async def test_download_servers_ram(data: dict[str, Any]) -> None:
    servers = await HetznerTest([{"ram": 128}, {"ram": 64}, {"ram": 32}]).download_servers(data)
    assert all(server.ram_size >= 128 for server in servers[0])
    assert all(server.ram_size >= 64 for server in servers[1])
    assert all(server.ram_size >= 32 for server in servers[2])


@pytest.mark.asyncio
async def test_download_servers_disk_num(data: dict[str, Any]) -> None:
    servers = await HetznerTest([{"disk_num": 3}, {"disk_num": 2}, {"disk_num": 1}]).download_servers(data)
    assert all(len(server.hdd_disks) + len(server.sata_disks) + len(server.nvme_disks) >= 3 for server in servers[0])
    assert all(len(server.hdd_disks) + len(server.sata_disks) + len(server.nvme_disks) >= 2 for server in servers[1])
    assert all(len(server.hdd_disks) + len(server.sata_disks) + len(server.nvme_disks) >= 1 for server in servers[2])


@pytest.mark.asyncio
async def test_download_servers_fast_disk(data: dict[str, Any]) -> None:
    servers = await HetznerTest([{"disk_num_quick": 3}, {"disk_num_quick": 2}, {"disk_num_quick": 1}]).download_servers(data)
    assert all(len(server.sata_disks) + len(server.nvme_disks) >= 3 for server in servers[0])
    assert all(len(server.sata_disks) + len(server.nvme_disks) >= 2 for server in servers[1])
    assert all(len(server.sata_disks) + len(server.nvme_disks) >= 1 for server in servers[2])


@pytest.mark.asyncio
async def test_download_disk_size(data: dict[str, Any]) -> None:
    servers = await HetznerTest([{"disk_size": 8000}, {"disk_size": 5000}, {"disk_size": 4000}]).download_servers(data)
    assert all(all(disk >= 8000 for disk in server.hdd_disks + server.sata_disks + server.nvme_disks) for server in servers[0])
    assert all(all(disk >= 5000 for disk in server.hdd_disks + server.sata_disks + server.nvme_disks) for server in servers[1])
    assert all(all(disk >= 4000 for disk in server.hdd_disks + server.sata_disks + server.nvme_disks) for server in servers[2])


@pytest.mark.asyncio
async def test_download_disk_size_any(data: dict[str, Any]) -> None:
    servers = await HetznerTest([{"disk_size_any": 7000}, {"disk_size_any": 5000}, {"disk_size_any": 3000}]).download_servers(data)
    assert all(any(disk >= 7000 for disk in server.hdd_disks + server.sata_disks + server.nvme_disks) for server in servers[0])
    assert all(any(disk >= 5000 for disk in server.hdd_disks + server.sata_disks + server.nvme_disks) for server in servers[0])
    assert all(any(disk >= 3000 for disk in server.hdd_disks + server.sata_disks + server.nvme_disks) for server in servers[0])


@pytest.mark.asyncio
async def test_download_raid0_size(data: dict[str, Any]) -> None:
    servers = await HetznerTest([{"disk_size_raid0": 16000}, {"disk_size_raid0": 12000}, {"disk_size_raid0": 8000}]).download_servers(data)
    assert all(sum(server.hdd_disks + server.sata_disks + server.nvme_disks) >= 16000 for server in servers[0])
    assert all(sum(server.hdd_disks + server.sata_disks + server.nvme_disks) >= 12000 for server in servers[1])
    assert all(sum(server.hdd_disks + server.sata_disks + server.nvme_disks) >= 8000 for server in servers[2])


@pytest.mark.asyncio
async def test_download_raid1_size(data: dict[str, Any]) -> None:
    all_servers = await HetznerTest([{"disk_size_raid1": 16000}, {"disk_size_raid1": 12000}, {"disk_size_raid1": 8000}]).download_servers(data)
    for size, servers in zip([16000, 12000, 8000], all_servers):
        for server in servers:
            all_disks = server.hdd_disks + server.sata_disks + server.nvme_disks
            assert min(all_disks) * len(all_disks) // 2 >= size


@pytest.mark.asyncio
async def test_download_raid5_size(data: dict[str, Any]) -> None:
    all_servers = await HetznerTest([{"disk_size_raid5": 16000}, {"disk_size_raid5": 12000}, {"disk_size_raid5": 8000}]).download_servers(data)
    for size, servers in zip([16000, 12000, 8000], all_servers):
        for server in servers:
            all_disks = server.hdd_disks + server.sata_disks + server.nvme_disks
            assert min(all_disks) * (len(all_disks) - 1) >= size


@pytest.mark.asyncio
async def test_download_raid6_size(data: dict[str, Any]) -> None:
    all_servers = await HetznerTest([{"disk_size_raid6": 16000}, {"disk_size_raid6": 12000}, {"disk_size_raid6": 8000}]).download_servers(data)
    for size, servers in zip([16000, 12000, 8000], all_servers):
        for server in servers:
            all_disks = server.hdd_disks + server.sata_disks + server.nvme_disks
            assert min(all_disks) * (len(all_disks) - 2) >= size


@pytest.mark.asyncio
async def test_download_specials(data: dict[str, Any]) -> None:
    servers = await HetznerTest([{"ipv4": True}, {"ipv4": True, "gpu": True}, {"ipv4": True, "gpu": True, "inic": True}, {"ipv4": True, "gpu": True, "inic": True, "ecc": True}, {"ipv4": True, "gpu": True, "inic": True, "ecc": True, "hwr": True}, ]).download_servers(data, increasing=False)
    assert all(server.specials.has_IPv4 for server in servers[0])
    assert all(server.specials.has_IPv4 and server.specials.has_GPU for server in servers[1])
    assert all(server.specials.has_IPv4 and server.specials.has_GPU and server.specials.has_iNIC for server in servers[2])
    assert all(server.specials.has_IPv4 and server.specials.has_GPU and server.specials.has_iNIC and server.specials.has_ECC for server in servers[3])
    assert all(server.specials.has_IPv4 and server.specials.has_GPU and server.specials.has_iNIC and server.specials.has_ECC and server.specials.has_HWR for server in servers[4])


@pytest.mark.asyncio
async def test_download_specials_unordered(data: dict[str, Any]) -> None:
    servers = await HetznerTest([{"inic": True}, {"hwr": True}]).download_servers(data, increasing=None)
    assert all(server.specials.has_iNIC for server in servers[0])
    assert all(server.specials.has_HWR for server in servers[1])
