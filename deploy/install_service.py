"""Run as root after the owner fills API settings. Never modify other services."""
from pathlib import Path
import os
import secrets
import subprocess
import sys
from dotenv import dotenv_values
import pymysql
BASE=Path('/home/wisteria/emjo')
config=BASE/'shared/server.env'
if os.geteuid()!=0: sys.exit('Run through install.sh with sudo.')
values=dict(dotenv_values(config))
for key in ('EMJO_SESSION_SIGNING_SECRET','EMJO_MYSQL_PASSWORD'):
    if not values.get(key): values[key]=secrets.token_urlsafe(40)
# Isolated names are fixed to prevent accidental schema changes in other products.
values.update(EMJO_MYSQL_HOST='127.0.0.1',EMJO_MYSQL_DATABASE='emjo_stickers',
              EMJO_MYSQL_USER='emjo_stickers',EMJO_DATA_DIR=str(BASE/'shared/data'))
os.environ.update({k:v for k,v in values.items() if v is not None})
subprocess.run([sys.executable,str(BASE/'current/deploy/check_config.py')],check=True)
config.write_text('\n'.join(k+"='"+str(v or '').replace("'", "\\'")+"'" for k,v in values.items())+'\n')
config.chmod(0o600)
import pwd
owner=pwd.getpwnam('wisteria');os.chown(config,owner.pw_uid,owner.pw_gid)
connection=pymysql.connect(user='root',unix_socket='/var/run/mysqld/mysqld.sock',autocommit=True)
try:
    with connection.cursor() as cur:
        cur.execute('CREATE DATABASE IF NOT EXISTS emjo_stickers CHARACTER SET utf8mb4')
        cur.execute("CREATE USER IF NOT EXISTS 'emjo_stickers'@'127.0.0.1' IDENTIFIED BY %s",(values['EMJO_MYSQL_PASSWORD'],))
        cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE, CREATE ON emjo_stickers.* TO 'emjo_stickers'@'127.0.0.1'")
finally: connection.close()
connection=pymysql.connect(host='127.0.0.1',user='emjo_stickers',password=values['EMJO_MYSQL_PASSWORD'],database='emjo_stickers',autocommit=True)
try:
    schema=(BASE/'current/server/schema.sql').read_text()
    schema='\n'.join(l for l in schema.splitlines() if not l.lstrip().startswith('--'))
    with connection.cursor() as cur:
        for statement in schema.split(';'):
            if statement.strip(): cur.execute(statement)
finally: connection.close()
target=Path('/etc/systemd/system/emjo.service')
if target.exists() and '/home/wisteria/emjo' not in target.read_text(): sys.exit('Existing emjo service belongs to another app; stopped.')
target.write_text((BASE/'current/deploy/emjo.service').read_text())
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','emjo.service'],check=True)
subprocess.run(['systemctl','restart','emjo.service'],check=True)
# No Nginx mutation: this host has no verified main-domain server block.
subprocess.run(['curl','--fail','--retry-connrefused','--retry','5','--retry-delay','2','--silent','--output','/dev/null','http://127.0.0.1:8013/sticker/'],check=True)
print('EMJO listening on 127.0.0.1:8013. Main-domain path proxy remains to be enabled separately.')
