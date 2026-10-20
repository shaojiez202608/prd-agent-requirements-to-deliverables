"""Distribution step: local (mock) and S3 (fake client) publishing with a validation gate."""

import io

import pytest
from botocore.exceptions import ClientError

from prd_agent.publish import PublishRefused, fetch, publish


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, IfNoneMatch=None):
        if IfNoneMatch == "*" and (Bucket, Key) in self.objects:  # S3 conditional write semantics
            raise ClientError({"Error": {"Code": "PreconditionFailed", "Message": "At least one of the pre-conditions "
                                         "you specified did not hold"}}, "PutObject")
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


def test_s3_bundle_names_are_immutable(generated):
    s3 = FakeS3()
    publish(generated, "s3://b/p", "v1", s3_client=s3)
    before = dict(s3.objects)
    prd = generated / "PRD.md"
    prd.write_text(prd.read_text(encoding="utf-8") + "\nA later edit.\n", encoding="utf-8")
    with pytest.raises(PublishRefused, match="already exists; bundles are immutable"):
        publish(generated, "s3://b/p", "v1", s3_client=s3)
    assert s3.objects == before  # nothing overwritten


def test_other_s3_errors_are_not_swallowed(generated):
    class Denied(FakeS3):
        def put_object(self, **kwargs):
            raise ClientError({"Error": {"Code": "AccessDenied", "Message": "denied"}}, "PutObject")

    with pytest.raises(ClientError):
        publish(generated, "s3://b/p", "v1", s3_client=Denied())
