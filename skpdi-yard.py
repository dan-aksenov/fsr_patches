from application_update import application_update
from patch_database import patch_database
import utils
from skpdi_web import skpdi_web

from getopt import getopt
import sys
import os

# Get patch number and target environment from parameters n and t
try:
    opts, args = getopt(sys.argv[1:], 'n:')
except StandardError:
    print("-n for patch number")
    sys.exit()

for opt, arg in opts:
    if opt in ('-n'):
        patch_num = arg
    else:
        print("-n for patch number")
        sys.exit()

# Variables
jump_host = "oemcc.fors.ru"
# application hosts as writen in ansible invenrory
application_hosts = ['gudhskpdi-app-03', 'gudhskpdi-rcod-app-03']
sunny_path = '//sunny/builds/odsxp/'
application_path = '/opt/tomcat/webapps/'
tomcat_name = 'tomcat'
ansible_inventory = '~/ansible-hosts/skpdi_yard'
wars = [
    ['skpdi-' + patch_num + '.war', 'dt'],
    ['ext-' + patch_num + '.war', 'ext-dt']
    ]

db_host = 'gudhskpdi-db-03'
db_name = 'ods_yard'
db_user = 'ods'
patch_table = 'parameter.fdc_patches_log'
stage_dir = '/tmp/skpdi_patch'

d = patch_database.PatchDatabase(
    jump_host,
    patch_num,
    sunny_path,
    application_hosts,
    ansible_inventory,
    db_host,
    db_name,
    stage_dir,
    db_user,
    patch_table
    )

d.patchdb()

a = application_update.ApplicationUpdate(
    jump_host,
    patch_num,
    sunny_path,
    application_hosts,
    application_path,
    tomcat_name,
    ansible_inventory,
    wars
    )

a.application_update()

print("Chekcking application version:")
for host in application_hosts:
    for app in wars:
        skpdi_web.check_webpage(patch_num, host, app[1])
