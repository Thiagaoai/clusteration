import unittest

from app.services.proxmox import ProxmoxClient, ProxmoxError, disk_size_gb_from_resource


class FakeProxmoxClient(ProxmoxClient):
    def __init__(self, resources=None, config=None, cluster_error=None, config_error=None):
        self.resources = resources or []
        self.config = config or {}
        self.cluster_error = cluster_error
        self.config_error = config_error
        self.config_calls = 0

    async def cluster_resources(self, resource_type: str = "vm"):
        if self.cluster_error:
            raise self.cluster_error
        return self.resources

    async def vm_config(self, node: str, vmid: int):
        self.config_calls += 1
        if self.config_error:
            raise self.config_error
        return self.config


class ProxmoxClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_template_node_prefers_cluster_resources(self):
        client = FakeProxmoxClient(
            resources=[{"vmid": 9001, "node": "pve2", "template": 1}],
            config={"template": 1},
        )

        node = await client.resolve_template_node("pve1", 9001)

        self.assertEqual(node, "pve2")
        self.assertEqual(client.config_calls, 0)

    async def test_resolve_template_node_falls_back_to_config(self):
        client = FakeProxmoxClient(
            cluster_error=ProxmoxError("cluster resources denied"),
            config={"template": 1},
        )

        node = await client.resolve_template_node("pve1", 9001)

        self.assertEqual(node, "pve1")
        self.assertEqual(client.config_calls, 1)

    async def test_vm_disk_size_uses_cluster_maxdisk_before_config(self):
        client = FakeProxmoxClient(
            resources=[{"vmid": 9001, "node": "pve1", "template": 1, "maxdisk": 36 * 1024**3}],
            config={"scsi0": "local-lvm:vm-9001-disk-0,size=12G"},
        )

        disk_gb = await client.vm_disk_size_gb("pve1", 9001)

        self.assertEqual(disk_gb, 36)
        self.assertEqual(client.config_calls, 0)

    async def test_vm_disk_size_falls_back_to_config(self):
        client = FakeProxmoxClient(config={"scsi0": "local-lvm:vm-9001-disk-0,size=12G"})

        disk_gb = await client.vm_disk_size_gb("pve1", 9001)

        self.assertEqual(disk_gb, 12)
        self.assertEqual(client.config_calls, 1)

    async def test_vm_disk_size_returns_none_when_config_is_denied(self):
        client = FakeProxmoxClient(
            resources=[{"vmid": 9001, "node": "pve1", "template": 1}],
            config_error=ProxmoxError("Proxmox recusou GET /nodes/pve1/qemu/9001/config"),
        )

        disk_gb = await client.vm_disk_size_gb("pve1", 9001)

        self.assertIsNone(disk_gb)
        self.assertEqual(client.config_calls, 1)


class ResourceDiskSizeTests(unittest.TestCase):
    def test_disk_size_gb_from_resource_rounds_up(self):
        self.assertEqual(disk_size_gb_from_resource({"maxdisk": 12 * 1024**3 + 1}), 13)

    def test_disk_size_gb_from_resource_ignores_missing_values(self):
        self.assertIsNone(disk_size_gb_from_resource({}))
        self.assertIsNone(disk_size_gb_from_resource({"maxdisk": 0}))


if __name__ == "__main__":
    unittest.main()
