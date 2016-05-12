import time
from os import listdir
import subprocess
from utils import *
import platform


class Fuzzer():

    def __init__(self, dirname, dev, targetcmd, logs_dir):
        self.dirname = dirname
        self.dev = dev
        self.targetcmd = ' '.join(targetcmd)
        self.logs_dir = logs_dir


    def run(self):
        cmd = 'adb -s %s logcat -v time *:F > %s ' % (self.dev, self.logs_dir + os.sep \
                                                      + self.dirname + '_stagefright_' + str(self.dev))
        subprocess.Popen([cmd], shell=True)

        seedfiles = listdir(self.dirname)
        if '.DS_Store' in seedfiles:
            seedfiles.remove('.DS_Store')

        for i in range(0, len(seedfiles)):
            targetcmd = self.targetcmd.replace(' @@', ' /data/Music/' + seedfiles[i])
            print '***** Sending file: ' + str(i) + ' - ' + seedfiles[i]
            cmd = 'adb -s ' + self.dev + ' push ' \
                  + "'" + self.dirname + '/' \
                  + seedfiles[i] + "'" \
                  + " '/data/Music/" + seedfiles[i] \
                  + "'"
            run_subproc(cmd)

            #should change the log
            cmd = 'adb -s ' + self.dev \
                  + " shell log -p F -t Stagefright - sp_stagefright '----- " \
                  + str(i) + " - Filename:'" + seedfiles[i]
            run_subproc(cmd)

            if OS == 'Darwin':
                cmd = 'gtimeout 15 adb -s %s shell %s' % (self.dev, targetcmd)
            elif OS == 'Linux':
                cmd = 'timeout 15 adb -s %s shell %s' % (self.dev, targetcmd)

            run_subproc(cmd)

            cmd = 'adb -s ' + self.dev \
                  + ' shell rm /data/Music/*'
            run_subproc(cmd)

        return