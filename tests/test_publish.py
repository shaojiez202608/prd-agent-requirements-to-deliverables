"""Distribution step: local (mock) and S3 (fake client) publishing with a validation gate."""

import io

import pytest

from prd_agent.publish import PublishRefused, fetch, publish


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body):
        self.objects[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}


def test_local_publish_and_fetch(generated, tmp_path):
    m = publish(generated, str(tmp_path / "dist"), "demo-v1")
    assert (tmp_path / "dist" / "demo-v1" / "MANIFEST.json").is_file()
    assert any(f["path"] == "thing-model.json" for f in m["files"])
    got = fetch(str(tmp_path / "dist"), "demo-v1", tmp_path / "back")
    assert len(got["files"]) == len(m["files"])
    with pytest.raises(PublishRefused):
        publish(generated, str(tmp_path / "dist"), "demo-v1")  # immutable bundle names


def test_s3_publish_with_fake_client(generated, tmp_path):
    s3 = FakeS3()
    publish(generated, "s3://bucket-x/bundles", "demo-v1", s3_client=s3)
    assert ("bucket-x", "bundles/demo-v1/MANIFEST.json") in s3.objects
    assert ("bucket-x", "bundles/demo-v1/device-demo/dp_table.h") in s3.objects
    fetch("s3://bucket-x/bundles", "demo-v1", tmp_path / "back", s3_client=s3)
    assert (tmp_path / "back" / "PRD.md").read_bytes() == (generated / "PRD.md").read_bytes()


def test_publish_refused_when_inconsistent(generated, tmp_path):
    p = generated / "PRD.md"
    p.write_text(p.read_text(encoding="utf-8").replace("| `timer_task` | 5 |", "| `timer_task` | 7 |"), encoding="utf-8")
    with pytest.raises(PublishRefused, match="id_mismatch"):
        publish(generated, str(tmp_path / "dist"), "demo-v1")


def test_fetch_detects_tampering(generated, tmp_path):
    s3 = FakeS3()
    publish(generated, "s3://b/p", "v1", s3_client=s3)
    s3.objects[("b", "p/v1/PRD.md")] = b"tampered"
    with pytest.raises(ValueError, match="checksum mismatch"):
        fetch("s3://b/p", "v1", tmp_path / "back", s3_client=s3)
