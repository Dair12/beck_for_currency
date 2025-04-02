"""
WSGI config for mysite project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

application = get_wsgi_application()
print("dskmjcmwdsdcmj")
import subprocess

sync_script = '/home/Dair12/sync.sh'

# Проверим, существует ли файл, и выполним его
if os.path.exists(sync_script):
    subprocess.call([sync_script])
    print("dskmjcmwdsdcmj")