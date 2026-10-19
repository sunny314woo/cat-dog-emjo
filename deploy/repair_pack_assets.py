"""Re-export an existing READY pack from an explicitly reviewed alpha-only repair.

Run with the service's existing environment and Python interpreter. This command
does not call an image provider, change payment entitlements, or send mail.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
import zipfile

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image
from server.imaging import prepare_pack
from server.settings import Settings
from server.store import MySQLStore


KEY_FIELDS = ('id', 'state', 'captions', 'user_id', 'session_id', 'created',
              'unlocked', 'free', 'selected', 'grant_id', 'expires', 'style',
              'workflow', 'style_index', 'prompt_version', 'asset_revision',
              'asset_repaired_at')


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def _private_json(path, value):
    # Exclusive creation prevents overwriting another repair's audit trail.
    with path.open('x', encoding='utf-8') as handle:
        os.chmod(path, 0o600)
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def repair_pack_assets(job_id, mask, mask_sha256, *, settings=None, store=None,
                       clock=time.time):
    """Repair one pack; injected settings/store allow isolated DemoStore tests."""
    if not re.fullmatch(r'[0-9a-f]{32}', job_id):
        raise ValueError('job_id 必须是 32 位小写十六进制标识')
    if not re.fullmatch(r'[0-9a-fA-F]{64}', mask_sha256):
        raise ValueError('必须提供已审核文件的完整 SHA-256')
    mask_sha256 = mask_sha256.lower()
    settings = settings or Settings()
    if store is None:
        if settings.mode != 'live':
            raise ValueError('请加载现有 live 服务环境后运行返修工具')
        store = MySQLStore()
    data_dir = Path(settings.data_dir)
    folder = data_dir / 'jobs' / job_id
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError('原作品目录不存在或不是独立目录')
    if any(path.is_symlink() for path in folder.rglob('*')):
        raise ValueError('作品目录含符号链接，拒绝返修')
    with store.transaction() as tx:
        original_job = tx.get('jobs', job_id)
    if not original_job or original_job.get('state') != 'READY':
        raise ValueError('仅能返修 READY 作品')
    if not original_job.get('user_id'):
        raise ValueError('作品必须已有邮箱账户归属')
    if type(original_job.get('captions')) is not bool:
        raise ValueError('作品缺少明确的原始配字选项')
    revision = original_job.get('asset_revision', 0)
    if type(revision) is not int or revision < 0:
        raise ValueError('作品素材版本无效')

    source = (folder / 'provider-output.png').read_bytes()
    old_zip_hash = sha256((folder / 'stickers.zip').read_bytes())
    repaired = Path(mask).read_bytes()
    if sha256(repaired) != mask_sha256:
        raise ValueError('更正母图与已审核 SHA-256 不一致')
    with Image.open(BytesIO(source)) as original:
        original.load()
        original_size = original.size
        source_rgb = original.convert('RGB').tobytes()
    with Image.open(BytesIO(repaired)) as approved:
        if approved.format != 'PNG' or approved.mode != 'RGBA' or getattr(approved, 'n_frames', 1) != 1:
            raise ValueError('更正母图必须是静态 RGBA PNG，仅允许修改 alpha')
        approved.load()
        if approved.size != original_size or approved.convert('RGB').tobytes() != source_rgb:
            raise ValueError('更正母图尺寸或 RGB 像素已改变，拒绝替换原作品')

    repaired_at = clock()
    stamp = datetime.fromtimestamp(repaired_at, timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    repairs = data_dir / 'asset-repairs'
    repairs.mkdir(mode=0o700, parents=True, exist_ok=True)
    repairs.chmod(0o700)
    backup = repairs / f'{stamp}-{job_id}-original'
    receipt_path = repairs / f'{stamp}-{job_id}-receipt.json'
    if backup.exists() or receipt_path.exists():
        raise ValueError('该时间标识已有返修记录，请重新运行')
    stage = Path(tempfile.mkdtemp(prefix=f'.asset-repair-{job_id}-', dir=folder.parent))
    moved_original = False
    swapped = False
    receipt_written = False
    try:
        shutil.copytree(folder, stage, dirs_exist_ok=True, symlinks=True)
        stage.chmod(0o700)
        if any(path.is_symlink() for path in stage.rglob('*')):
            raise ValueError('作品目录含符号链接，拒绝返修')
        if sha256((stage / 'provider-output.png').read_bytes()) != sha256(source):
            raise ValueError('原始生成母图已发生变化，请重新审核')
        for cached in stage.glob('sticker-*.zip'):
            cached.unlink()
        # This always uses the existing server font and never invokes rembg.
        prepare_pack(repaired, stage, captions=original_job['captions'],
                     background_mode='alpha_only', strict_boundaries=True)
        with zipfile.ZipFile(stage / 'stickers.zip') as archive:
            if len(archive.namelist()) != 47 or archive.testzip() is not None:
                raise ValueError('重新导出的整套 ZIP 未通过完整性检查')
        receipt = {'job_id': job_id, 'timestamp': repaired_at,
                   'timestamp_utc': stamp, 'asset_revision': revision + 1,
                   'old_zip_sha256': old_zip_hash,
                   'new_zip_sha256': sha256((stage / 'stickers.zip').read_bytes()),
                   'mask_sha256': mask_sha256,
                   'source_rgb_sha256': sha256(source_rgb),
                   'source_file_sha256': sha256(source),
                   'backup_path': str(backup)}
        (stage / 'asset-repair-mask.png').write_bytes(repaired)
        (stage / 'asset-repair-receipt.json').unlink(missing_ok=True)
        _private_json(stage / 'asset-repair-receipt.json', receipt)
        _private_json(receipt_path, receipt)
        receipt_written = True
        with store.transaction() as tx:
            current = tx.get('jobs', job_id)
            if not current or any(current.get(k) != original_job.get(k) for k in KEY_FIELDS):
                raise ValueError('作品状态或归属等关键字段已变化，返修未应用')
            if folder.is_symlink() or sha256((folder / 'provider-output.png').read_bytes()) != sha256(source):
                raise ValueError('原始生成母图已变化，返修未应用')
            if sha256((folder / 'stickers.zip').read_bytes()) != old_zip_hash:
                raise ValueError('原交付 ZIP 已变化，返修未应用')
            folder.rename(backup)
            moved_original = True
            backup.chmod(0o700)
            stage.rename(folder)
            swapped = True
            current.update(asset_revision=revision + 1, asset_repaired_at=repaired_at)
            tx.put('jobs', job_id, current)
        return receipt
    except BaseException:
        # Includes transaction commit errors: restore the complete original tree.
        if swapped:
            folder.rename(stage)
            swapped = False
        if moved_original:
            backup.rename(folder)
            moved_original = False
        if receipt_written:
            receipt_path.unlink(missing_ok=True)
        raise
    finally:
        if stage.exists() and not moved_original:
            shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job_id')
    parser.add_argument('--mask', required=True, type=Path)
    parser.add_argument('--mask-sha256', required=True)
    args = parser.parse_args()
    try:
        receipt = repair_pack_assets(args.job_id, args.mask, args.mask_sha256)
    except Exception:
        # Do not print database exceptions, environment values, or owner details.
        parser.exit(1, '返修失败，原文件已保留；请检查审核文件、作品状态及私有返修目录。\n')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
