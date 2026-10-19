from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import stat
import zipfile

from PIL import Image, ImageDraw, ImageFont
import pytest

from deploy.repair_pack_assets import repair_pack_assets
from server.settings import Settings
from server.store import DemoStore


JID = '0123456789abcdef0123456789abcdef'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def pack(tmp_path, monkeypatch):
    # Production uses EMJO_FONT_PATH/the existing server font; tests need no host font.
    monkeypatch.setattr('server.imaging.font', lambda size: ImageFont.load_default(size=size))
    settings = Settings(data_dir=tmp_path / 'data')
    store = DemoStore()
    folder = settings.data_dir / 'jobs' / JID
    folder.mkdir(parents=True)
    source = Image.new('RGB', (600, 600), 'white')
    alpha = Image.new('L', source.size, 0)
    rgb_draw, alpha_draw = ImageDraw.Draw(source), ImageDraw.Draw(alpha)
    for row in range(3):
        for col in range(3):
            box = (col * 200 + 40, row * 200 + 35, col * 200 + 160, row * 200 + 165)
            rgb_draw.rectangle(box, fill=(120 + col * 20, 80 + row * 20, 50))
            # Include an opaque white garment inside each subject.
            rgb_draw.rectangle((box[0] + 10, box[1] + 65, box[2] - 10, box[3]), fill='white')
            alpha_draw.rectangle(box, fill=255)
    source.save(folder / 'provider-output.png')
    repaired = source.convert('RGBA');repaired.putalpha(alpha)
    mask = tmp_path / 'approved.png';repaired.save(mask)
    (folder / 'stickers.zip').write_bytes(b'previous-delivery-zip')
    (folder / 'style-output.png').write_bytes(b'original-style-sheet')
    (folder / 'style-reference-1.jpg').write_bytes(b'original-selected-style')
    (folder / 'sticker-1.png.zip').write_bytes(b'stale-single-cache')
    job = {'id': JID, 'state': 'READY', 'captions': True, 'user_id': 'private-owner',
           'session_id': 'private-session', 'unlocked': True, 'free': True,
           'selected': [1, 2], 'expires': 1234567890, 'created': 1234500000,
           'asset_revision': 2, 'style': 'style-1'}
    with store.transaction() as tx:
        tx.put('jobs', JID, job)
        tx.put('orders', 'original-order', {'id': 'original-order', 'state': 'PAID'})
        tx.put('mail', 'original-mail', {'id': 'original-mail', 'state': 'SENT'})
        tx.put('grants', 'original-grant', {'id': 'original-grant', 'available': 3})
    return settings, store, folder, mask, job


def repair(pack, **kwargs):
    settings, store, _, mask, _ = pack
    return repair_pack_assets(JID, mask, digest(mask), settings=settings, store=store,
                              clock=lambda: 1792382400.123456, **kwargs)


def test_rgb_changes_are_rejected_without_touching_original_zip(pack):
    _, store, folder, mask, job = pack
    original = (folder / 'stickers.zip').read_bytes()
    with Image.open(mask) as image:
        changed = image.copy()
    changed.putpixel((50, 50), (1, 2, 3, 255));changed.save(mask)
    with pytest.raises(ValueError, match='RGB'):
        repair(pack)
    assert (folder / 'stickers.zip').read_bytes() == original
    assert not (folder.parent.parent / 'asset-repairs').exists()
    with store.transaction() as tx:
        assert tx.get('jobs', JID) == job


def test_reviewed_alpha_only_repair_reexports_and_preserves_original_backup(pack):
    settings, store, folder, mask, job = pack
    original_files = {p.name: p.read_bytes() for p in folder.iterdir()}
    before = json.loads(json.dumps(store.data))
    receipt = repair(pack)
    backup = Path(receipt['backup_path'])
    assert stat.S_IMODE(backup.stat().st_mode) == 0o700
    assert {p.name: p.read_bytes() for p in backup.iterdir()} == original_files
    assert (folder / 'provider-output.png').read_bytes() == original_files['provider-output.png']
    assert (folder / 'style-output.png').read_bytes() == original_files['style-output.png']
    assert (folder / 'style-reference-1.jpg').read_bytes() == original_files['style-reference-1.jpg']
    assert not list(folder.glob('sticker-*.zip'))
    with zipfile.ZipFile(folder / 'stickers.zip') as archive:
        assert len(archive.namelist()) == 47
        assert len([n for n in archive.namelist() if n.startswith('GIF-240/')]) == 9
        assert len([n for n in archive.namelist() if n.startswith('WebP-512/')]) == 9
    assert receipt['old_zip_sha256'] == hashlib.sha256(original_files['stickers.zip']).hexdigest()
    assert receipt['new_zip_sha256'] == digest(folder / 'stickers.zip')
    assert receipt['mask_sha256'] == digest(mask)
    assert json.loads((folder / 'asset-repair-receipt.json').read_text()) == receipt
    receipts = list((settings.data_dir / 'asset-repairs').glob('*-receipt.json'))
    assert len(receipts) == 1 and json.loads(receipts[0].read_text()) == receipt
    with store.transaction() as tx:
        assert tx.get('jobs', JID) == {**job, 'asset_revision': 3,
                                      'asset_repaired_at': 1792382400.123456}
    assert {k: v for k, v in store.data.items() if k != 'jobs'} == {k: v for k, v in before.items() if k != 'jobs'}


def test_incorrect_review_hash_is_rejected(pack):
    settings, store, folder, mask, _ = pack
    with pytest.raises(ValueError, match='SHA-256'):
        repair_pack_assets(JID, mask, '0' * 64, settings=settings, store=store)
    assert (folder / 'stickers.zip').read_bytes() == b'previous-delivery-zip'


def test_transaction_commit_failure_restores_original_directory(pack):
    settings, real_store, folder, mask, _ = pack
    original_files = {p.name: p.read_bytes() for p in folder.iterdir()}
    class CommitFailure:
        calls = 0
        @contextmanager
        def transaction(self):
            self.calls += 1
            with real_store.transaction() as tx:
                yield tx
                if self.calls == 2:
                    raise RuntimeError('simulated commit failure')
    with pytest.raises(RuntimeError, match='commit failure'):
        repair_pack_assets(JID, mask, digest(mask), settings=settings, store=CommitFailure())
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == original_files
    assert not list((settings.data_dir / 'asset-repairs').iterdir())
    assert not list(folder.parent.glob('.asset-repair-*'))


def test_changed_job_state_during_export_prevents_swap(pack, monkeypatch):
    import deploy.repair_pack_assets as tool
    settings, store, folder, _, job = pack
    original_files = {p.name: p.read_bytes() for p in folder.iterdir()}
    export = tool.prepare_pack
    def change_state(*args, **kwargs):
        result = export(*args, **kwargs)
        with store.transaction() as tx:
            current = tx.get('jobs', JID);current['unlocked'] = False
            tx.put('jobs', JID, current)
        return result
    monkeypatch.setattr(tool, 'prepare_pack', change_state)
    with pytest.raises(ValueError, match='关键字段已变化'):
        repair(pack)
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == original_files
    assert not list((settings.data_dir / 'asset-repairs').iterdir())
    with store.transaction() as tx:
        assert tx.get('jobs', JID) == {**job, 'unlocked': False}


def test_repeated_repair_retains_both_originals_and_receipts(pack):
    settings, store, folder, mask, _ = pack
    first = repair(pack)
    previous = {p.name: p.read_bytes() for p in folder.iterdir()}
    second = repair_pack_assets(JID, mask, digest(mask), settings=settings, store=store,
                                 clock=lambda: 1792382401.123456)
    assert second['asset_revision'] == 4
    assert {p.name: p.read_bytes() for p in Path(second['backup_path']).iterdir()} == previous
    assert Path(first['backup_path']).is_dir()
    assert len(list((settings.data_dir / 'asset-repairs').glob('*-receipt.json'))) == 2
