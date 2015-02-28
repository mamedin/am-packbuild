#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  packbuild.py
#  

import argparse
import os
import time
import logging
import subprocess 
import shlex
import re

def run_subprocess(command_string, cwd=None): 
    logging.info("Running: %s", command_string)
    logging.info("    cwd: %s", cwd)
    subprocess.check_call(shlex.split(command_string), cwd=cwd)
    return

def run_subprocess_co(command_string, cwd=None): 
    logging.info("Running: %s", command_string)
    logging.info("    cwd: %s", cwd)
    output = subprocess.check_output(shlex.split(command_string), cwd=cwd)
    return output


def main():

    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

    PROCESS_DIR = "/tmp/ampackbuilder"

    parser = argparse.ArgumentParser()

    #-ver CURRENT_VERSION -br BRANCH
    parser.add_argument("-r", "--repository", help="repository (am or ss)", required=True, choices=['am','ss'])
    parser.add_argument("-v", "--version", help="current version", required=True)
    parser.add_argument("-c", "--checkout", help="branch/commit/tag to checkout", required=True)
    parser.add_argument("-p", "--ppa", help="ppa to upload", required=True)
    parser.add_argument("-k", "--key", help="key for package signing", required=True)
    
    args = parser.parse_args()
    
    # create package version string

    build_time = time.gmtime() 

    utctime=time.strftime("%Y%m%d%H%M%S", build_time)
    checkout_alphanum= re.sub(r'[^a-zA-Z0-9]','', args.checkout)

    # create directory for the build
    dir_string = args.repository+"-"+args.version \
                        +"-"+utctime+"-"+checkout_alphanum 
    working_dir = os.path.join (PROCESS_DIR, dir_string)
    logging.info("Creating directory: %s", working_dir)

    os.makedirs(working_dir)

    if args.repository == "am":
        try:        
            #git clone 
            command_string = 'git clone https://github.com/artefactual/archivematica.git'
            run_subprocess(command_string, cwd=working_dir)

            #git checkout
            repo_dir = os.path.join(working_dir,"archivematica")
            command_string = 'git checkout '+args.checkout
            run_subprocess(command_string, cwd=repo_dir)

            #git submodule init
            command_string = 'git submodule init'
            run_subprocess(command_string, cwd=repo_dir)

            #git submodule update
            command_string = 'git submodule update'
            run_subprocess(command_string, cwd=repo_dir)

            #check the latest commit
            command_string = 'git rev-parse HEAD'
            commit_hash = run_subprocess_co(command_string, cwd=repo_dir)
            # need to convert output from byte to string
            commit_hash_str = commit_hash.decode("utf-8").strip()

            # package version string
            #package_ver_string = "1:%s+1SNAPSHOT%s-%s-%s"%(args.version, utctime, commit_hash[:6], checkout_alphanum)
            package_ver_string = "1:{0}+1SNAPSHOT{1}-{2}-{3}".format(args.version, utctime, commit_hash_str[:6], checkout_alphanum)
            package_ver_string_noepoch = "{0}+1SNAPSHOT{1}-{2}-{3}".format(args.version, utctime, commit_hash_str[:6], checkout_alphanum)
            logging.info("package version: %s", package_ver_string)

            # First modify changelog for precise

            # dict: package_name -> directory
            packagedir_dic = { "archivematica-common":"archivematicaCommon",
                               "archivematica-dashboard":"dashboard",  
                               "archivematica-mcp-client":"MCPClient",
                               "archivematica-mcp-server":"MCPServer",                               
                             }
 

            # dict: distribution -> numeric version
            distronum_dic = { "precise":"12.04",
                              "trusty":"14.04",
                            }


            # lines for the changelog
            
            chglog_maintainer = "Artefactual Systems <sysadmin@artefactual.com>"
            chglog_package_name = "archivematica-common"
            chglog_time = time.strftime("%a, %d %b %Y %H:%M:%S +0000", build_time)
            line = ["","","","","",""]
            line[2] = "  * commit: {0}".format(commit_hash_str)
            line[3] = "  * checkout: {0}".format(args.checkout)
            line[5] = " -- {0}  {1}".format(chglog_maintainer, chglog_time)

            # Iterate on distros
            for d in distronum_dic:
                # Iterate on packages
                for p in packagedir_dic:
                    line[0] = "{0} ({1}~{2}) {3}; urgency=high".format(p, package_ver_string, distronum_dic[d], d)
                    for l in line:
                        print(l)
                    print()

                    # write debian changelog file
                    package_dir = os.path.join(repo_dir, "src", packagedir_dic[p])
                    chglog_file = os.path.join(package_dir, "debian","changelog" )
                    logging.info("writing debian changelog in %s", chglog_file)

                    f = open(chglog_file, 'r')
                    temp = f.read()
                    f.close()

                    f = open(chglog_file, 'w')
                    for l in line:
                        f.write(l+'\n')
                    f.write(temp)
                    f.close()

                    # debuild
                    command_string = 'debuild --no-tgz-check -S -k{0} -I'.format(args.key)
                    run_subprocess(command_string, cwd=package_dir)

                    # dput
                    dput_dir = os.path.join(repo_dir, "src")
                    dput_filename = "{0}_{1}~{2}_source.changes".format(p, package_ver_string_noepoch, distronum_dic[d])
                    command_string = 'dput ppa:{0} {1}'.format(args.ppa, dput_filename)
                    run_subprocess(command_string, cwd=dput_dir)



        except subprocess.CalledProcessError as e:
            logging.error("Subprocess returned code %d", e.returncode)
        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise

    elif args.repository == "ss":
        print ("TODO")
    





    #package_string = args.repository+"-"+args.version \
    #                    +"+1SNAPSHOT"+utctime+"-"+checkout_alphanum 
    
    #logging.info ("package_string= %s", package_string)


"""
    os.makedirs(build_path)

    # clone corresponding git repo
    if args.repository == "ss":
        logging.info("Cloning git repo for Storage Service")

        command_string = 'git clone https://github.com/artefactual/archivematica-storage-service.git'
        logging.info("calling subprocess for: %s", command_string)
        p = subprocess.Popen(shlex.split(command_string), cwd=build_path )
        p.wait()

        command_string = 'git checkout -t '+args.branch
        logging.info("calling subprocess for: %s", command_string)
        p = subprocess.Popen(shlex.split(command_string), cwd=build_path )
        p.wait()

    return 0
"""

if __name__ == '__main__':
    main()

