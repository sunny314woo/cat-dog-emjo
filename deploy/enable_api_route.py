"""Enable only the Sticker route in the existing API vhost; run with sudo."""
from pathlib import Path
import os, subprocess, time, sys
if os.geteuid()!=0:sys.exit('Use sudo with this script.')
p=Path('/etc/nginx/sites-available/m2-m4')
if not p.exists():sys.exit('Expected API vhost is missing; no changes made.')
original=p.read_text()
anchor='    server_name api.wisteriasoftware.uk account.wisteriasoftware.uk;'
if original.count(anchor)!=1:sys.exit('API vhost is ambiguous; no changes made.')
marker='    # BEGIN EMJO STICKER API'
fragment='''
    # BEGIN EMJO STICKER API
    location ^~ /sticker/api/ {
        client_max_body_size 48m;
        proxy_read_timeout 240s;
        proxy_pass http://127.0.0.1:8013;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    # END EMJO STICKER API
'''
if marker not in original:
    backup=Path('/home/wisteria/emjo/shared')/('nginx-m2-m4-'+str(int(time.time()))+'.backup')
    backup.write_text(original);backup.chmod(0o600)
    p.write_text(original.replace(anchor,anchor+'\n'+fragment,1))
    try:subprocess.run(['nginx','-t'],check=True)
    except Exception:p.write_text(original);raise
    subprocess.run(['systemctl','reload','nginx'],check=True)
else:subprocess.run(['nginx','-t'],check=True)
subprocess.run(['systemctl','restart','emjo.service'],check=True)
subprocess.run(['curl','--fail','--silent','--retry-connrefused','--retry','5','--retry-delay','2','--output','/dev/null','http://127.0.0.1:8013/sticker/api/catalog'],check=True)
print('Sticker API route enabled. Only emjo restarted; existing APIs retained.')
