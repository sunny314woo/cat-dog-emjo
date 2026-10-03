from dataclasses import dataclass, field
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]

@dataclass
class Settings:
    mode: str = field(default_factory=lambda: os.getenv('EMJO_MODE', 'demo'))
    data_dir: Path = field(default_factory=lambda: Path(os.getenv('EMJO_DATA_DIR') or ROOT / '.local-data'))
    secret: str = field(default_factory=lambda: os.getenv('EMJO_SESSION_SIGNING_SECRET', 'local-demo-only-do-not-deploy'))
    api_prefix: str = '/sticker/api'
    public_url: str = field(default_factory=lambda: os.getenv('EMJO_PUBLIC_URL', 'http://127.0.0.1:4173'))
    asset_url: str = field(default_factory=lambda: os.getenv('EMJO_ASSET_URL', ''))
    ttl_hours: int = field(default_factory=lambda: int(os.getenv('EMJO_FREE_ASSET_TTL_HOURS') or 24))
    paid_ttl_hours: int = field(default_factory=lambda: int(os.getenv('EMJO_PAID_DELIVERY_TTL_HOURS') or 24))
    calibration_enabled: bool = field(default_factory=lambda: os.getenv('EMJO_CALIBRATION_ENABLED') == 'true')
    calibration_limit: int = field(default_factory=lambda: int(os.getenv('EMJO_CALIBRATION_MAX_CASES') or 100))
    calibration_days: int = field(default_factory=lambda: int(os.getenv('EMJO_CALIBRATION_RETENTION_DAYS') or 30))
    upload_bytes: int = 15 * 1024 * 1024
    upload_pixels: int = 40_000_000
    max_edge: int = 2048
    demo_code: str = '123456'

    def validate(self):
        if self.mode not in ('demo', 'live'):
            raise RuntimeError('EMJO_MODE must be demo or live')
        if self.mode == 'live':
            required = ['EMJO_SESSION_SIGNING_SECRET', 'EMJO_MYSQL_HOST', 'EMJO_MYSQL_DATABASE',
                        'EMJO_MYSQL_USER', 'EMJO_MYSQL_PASSWORD']
            missing = [key for key in required if not os.getenv(key)]
            if missing:
                raise RuntimeError('Missing server configuration: ' + ', '.join(missing))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.chmod(0o700)
