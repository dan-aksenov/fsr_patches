# for args and exit
import sys
import os
# for waiting
from time import sleep
import subprocess
import shutil
import os
import re
# stat for chmod
import stat

#Custom utilities
from utils import utils, linux, pgsql, colours
    
#c = PatchDatabase(patch_num, sunny_path, application_hosts, ansible_inventory, db_host, db_name, stage_dir, db_user, patch_table)    

class PatchDatabase:
    def __init__( self, jump_host, patch_num, sunny_path, application_hosts, ansible_inventory, db_host, db_name, stage_dir, db_user, patch_table ):
    #def __init__( self, jump_host, patch_num, self.sunny_path, application_hosts, ansible_inventory, patches_table ):
        # intermediate host with ansible installation.
        self.jump_host = jump_host
        self.patch_num = patch_num 
        self.db_host = db_host
        self.db_name = db_name
        self.db_user = db_user
        self.stage_dir = stage_dir
        self.sunny_path = sunny_path
        self.sunny_patch = self.sunny_path + self.patch_num + '/'
        # application hosts as writen in ansible invenrory
        self.application_hosts = application_hosts
        self.ansible_inventory = ansible_inventory
        #self.ansible_#cmd_template = 'ansible -i ' + ansible_inventory + ' '
        # patch_table - variable to hold db_patches_log(specific in different projects)
        self.patch_table = patch_table
        self.linux = linux.Deal_with_linux( ansible_inventory )
        # Send subprocess for database patching to null. Nothing interesting there anyway.
        self.dnull = open(os.devnull, 'w')
        self.db_patch_file = 'db_patch.sh'

    def patchdb( self ):
        '''
        Preparation
        '''
        # Check if patch exists on Sunny
        if os.path.isdir( self.sunny_patch ) != True:
            print( colours.Bcolors.FAIL + "ERROR: No such patch on Sunny!" + colours.Bcolors.ENDC )
            print( "\tNo such directory " + self.sunny_patch )
            sys.exit()

        # Clear temporary directory. May fall if somebody is "sitting" in it.
        try:
            utils.recreate_dir( self.stage_dir )
        except:
            print( colours.Bcolors.FAIL + "ERROR: Unable to recreate patch staging directory." + colours.Bcolors.ENDC )
            sys.exit()
    
        '''
        Database patching
        '''
        # Get list of already applied patches
        # Function postgres_exec returns list - tuples + row count, need only tuples here, so [0]
        patches_curr = pgsql.postgres_exec ( self.db_host, self.db_name,  'select name from '+ self.patch_table +' order by id desc;' )[0]
    
        # Get list of patches from from Sunny
        if os.path.isdir( self.sunny_patch + '/patches' ) != True:
            print( "NOTICE: No database patch found in build. Assume database patching not required. Current schema version is " + max( patches_curr ))
        else:
            patches_targ = [ name for name in os.listdir( self.sunny_patch + '/patches' ) ]
        
            # Compare installed patches with patches from Sunny.
            # If latest database patch version lower then on Sunny - install missing patches.
            print( "\nChecking database patch level:" )
            # To handle file name suffixes for directories like "db_0190_20171113_v2.19" additional variable declared to hold max(patches_targ)
            last_patch_targ = max( patches_targ )
            last_patch_targ_strip = re.findall('db_.*_[0-9]{8}', last_patch_targ)[0] # findall returns list
            if last_patch_targ_strip == max(patches_curr):
                print( "\tDatabase patch level: " + max(patches_curr) )
                print( "\tLatest patch on Sunny: " + last_patch_targ_strip )
                print( "\tNo database patch required.\n" )
            elif last_patch_targ_strip > max(patches_curr):
                print( "\tDatabase patch level: " + max(patches_curr) )
                print( "\tLatest patch on Sunny: " + last_patch_targ_strip )
                print( "\tDatabase needs patching.\n" )
                patches_miss = []
                for i in (set(patches_targ) - set(patches_curr)):
                    if i > max(patches_curr):
                        patches_miss.append(i)
    
                print( "Following database patches will be applied: " + ', '.join(sorted(patches_miss)) + "\n" )
                input("Press Enter to continue...")
                for i in patches_miss:
                # Copy needed patches from Sunny.
                    shutil.copytree(self.sunny_patch + '/patches/' + i, self.stage_dir + '/patches/' + i)
                # Place patch installer to patch subdirectories.
                    shutil.copy( './patch_database/' + self.db_patch_file , self.stage_dir + '/patches/' + i)
                    os.chmod( self.stage_dir + '/patches/' + i + '/' + self.db_patch_file , stat.S_IRWXU)
    
                # Stop tomcat.
                for application_host in self.application_hosts:
                    self.linux.deal_with_tomcat( application_host, 'tomcat', 'stopped' )

                # Apply database patches
                # Using sort to execute patches in right order.
                for i in sorted(patches_miss):    
                    print( "Applying database patch " + i + "..." )
                    # Output to null - nothing usefull there anyway. Result to be analyzed by reading log. 
                    subprocess.call( [ self.stage_dir + '/patches/' + i + '/' + self.db_patch_file, self.db_host, self.db_name, self.db_user ], stdout=self.dnull, stderr = self.dnull, shell = False, cwd = self.stage_dir + '/patches/' + i )
                    # Search logfile for "finish install patch ods objects
                    try:
                        logfile = open( self.stage_dir + '/patches/' + i + '/install_db_log.log' )
                    except:
                        print( colours.Bcolors.FAIL + "\tUnable to read logfile" + self.stage_dir + "/patches/" + i + "/install_db_log.log. Somethnig wrong with installation.\n" + colours.Bcolors.ENDC )
                        sys.exit()
                    loglines = logfile.read()
                    success_marker = loglines.find('finsih install patch')
                    if success_marker != -1:
                        print( colours.Bcolors.OKGREEN + "\tDone.\n" + colours.Bcolors.ENDC )
                    else:
                        print( colours.Bcolors.FAIL + "\tError installing database patch. Examine logfile " + self.stage_dir + "/patches/" + i + "/install_db_log.log for details\n" + colours.Bcolors.ENDC )
                        sys.exit()
                    logfile.close()
          
            else:
                print( "\tDatabase patch level: " + max(patches_curr) )
                print( "\t Latest patch on Sunny: " + last_patch_targ_strip )
                print( colours.Bcolors.FAIL + "ERROR: Something wrong with database patching!\n" + colours.Bcolors.ENDC )
                sys.exit()
