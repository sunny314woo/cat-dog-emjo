"""Fail closed before starting production. Print names only, never values."""
import os
import sys
required = ['EMJO_SESSION_SIGNING_SECRET','EMJO_MYSQL_HOST','EMJO_MYSQL_DATABASE',
 'EMJO_MYSQL_USER','EMJO_MYSQL_PASSWORD','EMJO_PUBLIC_URL','VOLCENGINE_API_KEY',
 'VOLCENGINE_MODEL_ID','VOLCENGINE_FINAL_SIZE','PADDLE_API_KEY','PADDLE_CLIENT_TOKEN',
 'PADDLE_PRODUCT_ID','PADDLE_PRICE_FIRST_PACK_UNLOCK_ID','PADDLE_PRICE_PACK_1_ID',
 'RESEND_API_KEY','MAIL_FROM']
missing = [k for k in required if not os.getenv(k) or 'PLACEHOLDER' in os.getenv(k, '')]
if os.getenv('EMJO_MODE') != 'live': missing.append('EMJO_MODE=live')
if missing:
 print('Configuration pending: ' + ', '.join(missing)); sys.exit(1)
print('Required production configuration present; external integrations still need validation.')
