"""Rebuild upstream Djoser with only its social-auth dependency cap widened.

Application code is unchanged. Verify the upstream wheel against PyPI's SHA256
before editing METADATA and regenerating RECORD. See vendor/README.md.
"""
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo


def main():
    filename = "djoser-2.3.4-py3-none-any.whl"
    with urlopen("https://pypi.org/pypi/djoser/2.3.4/json", timeout=30) as response:
        release = json.load(response)
    source = next(item for item in release["urls"] if item["filename"] == filename)
    with urlopen(source["url"], timeout=60) as response:
        payload = response.read()
    upstream_hash = hashlib.sha256(payload).hexdigest()
    expected = "251e4a8973f95d1d770413fd219599413a4affb6dcf04d1ea6479258a133a919"
    if upstream_hash != expected or upstream_hash != source["digests"]["sha256"]:
        raise ValueError("Upstream wheel checksum mismatch")
    with ZipFile(io.BytesIO(payload)) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    metadata_path = "djoser-2.3.4.dist-info/METADATA"
    original = b"Requires-Dist: social-auth-app-django<6.0.0,>=5.0.0"
    replacement = b"Requires-Dist: social-auth-app-django<7.0.0,>=6.1.0"
    if files[metadata_path].count(original) != 1:
        raise ValueError("Unexpected upstream dependency metadata")
    files[metadata_path] = files[metadata_path].replace(original, replacement)
    record_path = "djoser-2.3.4.dist-info/RECORD"
    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for name, contents in sorted(files.items()):
        if name == record_path:
            continue
        digest = base64.urlsafe_b64encode(hashlib.sha256(contents).digest()).rstrip(b"=").decode()
        writer.writerow([name, "sha256=" + digest, len(contents)])
    writer.writerow([record_path, "", ""])
    files[record_path] = record.getvalue().encode()
    target = Path(__file__).resolve().parents[1] / "vendor" / filename
    target.parent.mkdir(exist_ok=True)
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for name, contents in sorted(files.items()):
            info = ZipInfo(name, date_time=(2025, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, contents)
    print("Upstream SHA256:", upstream_hash)
    print("Patched wheel SHA256:", hashlib.sha256(target.read_bytes()).hexdigest())
    print("Only METADATA and RECORD changed; upstream code and license retained.")


if __name__ == "__main__":
    main()
