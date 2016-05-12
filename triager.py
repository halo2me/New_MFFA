import re
import os
from utils import *
import random


class Triager():

    def __init__(self, log_name, dev, target_cmd, issues_dir):
        regex_path = re.compile("(\S*)_stagefright")
        dir_path = regex_path.findall(os.path.basename(log_name))
        if dir_path:
            self.dir_path = str(dir_path[0])
        else:
            print log_name + ' is not a log file!'
            self.dir_path = None
            return
        self.log_name = log_name
        self.dev = dev
        self.target_cmd = " ".join(target_cmd)
        self.issues_dir = issues_dir
        self.new_crashes = {}

    def run(self):

        log_density = 8
        crash_count = 1

        regex_filename = re.compile("Filename:(\S*)")
        regex_address = re.compile("pc\s(\S*)")
        regex_signal = re.compile("Fatal signal \d \((SIG[A-Z]+)\)")

        print 'Current devices is %s, and Current dir is %s' % (self.dev, self.dir_path)

        f = open(self.log_name, "r")
        lines = f.readlines()

        for count in range(0, len(lines)):
            signal = regex_signal.findall(lines[count])
            if signal:
                signal = str(signal[0])
                check_no_lines = count - log_density
                if check_no_lines < 0:
                    diff = log_density - count
                    check_no_lines = log_density - diff
                else:
                    check_no_lines = log_density
                for crash_line in range(1, check_no_lines):
                    if "Filename:" in lines[count - crash_line]:
                        filename = regex_filename.findall(lines[count - crash_line])
                        filename = str(filename[0])
                        break

                cmd = "adb -s %s push %s /data/Music " % (self.dev, self.dir_path + os.sep + filename)
                run_subproc(cmd)

                cmd = "adb -s %s shell rm /data/tombstones/tombstone* " % self.dev
                run_subproc(cmd)

                target_cmd = self.target_cmd.replace(' @@', ' /data/Music/' + filename)
                if OS == 'Darwin':
                    cmd = 'gtimeout 15 adb -s %s shell %s' % (self.dev, target_cmd)
                elif OS == 'Linux':
                    cmd = 'timeout 15 adb -s %s shell %s' % (self.dev, target_cmd)
                run_subproc(cmd)

                cmd = "adb -s %s shell rm /data/Music/* " % self.dev
                run_subproc(cmd)

                try:

                    tid = str(random.random())
                    tmp_tomb_name = self.issues_dir + os.sep + 'tombstone' + tid
                    cmd = "adb -s %s pull /data/tombstones/tombstone_00 %s" % \
                          (self.dev, tmp_tomb_name)
                    run_subproc(cmd)

                    f = open(tmp_tomb_name, "r")
                    traces = f.readlines()
                    pc_check = 0
                    for x in range(0, len(traces)):
                        if "backtrace:" in traces[x]:
                            # get the pc address from the next line
                            pc_address = regex_address.findall(traces[x + 1])
                            pc_address = str(pc_address[0])
                            print str(crash_count) + " -- PC address: " + pc_address
                            crash_count += 1
                            pc_check = 1
                            break
                    if pc_check == 0:
                        pc_address = "00000000"

                    if pc_address not in self.new_crashes.keys():
                        self.new_crashes[pc_address] = filename
                        print "**NEW**" + pc_address

                        # create a new folder that will contain the tombstone
                        # and the file that generated the crash
                        signal_dir = self.issues_dir + os.sep + signal
                        if not os.path.isdir(signal_dir):
                            os.mkdir(signal_dir)
                        os.mkdir(signal_dir + os.sep + pc_address)

                        # copy the tombstone in the new issue folder

                        cmd = "cp %s %s" % (tmp_tomb_name, signal_dir + os.sep + pc_address)
                        run_subproc(cmd)

                        # save the file that caused the crash in the corresponding issue folder
                        # result: all the files that caused a crash are saved

                        cmd = "cp %s %s" % (self.dir_path + os.sep + filename, signal_dir + os.sep + pc_address)
                        run_subproc(cmd)

                        # delete the gathered tombstone

                    cmd = "rm %s" % tmp_tomb_name
                    run_subproc(cmd)
                    f.close()

                except IOError:
                    print "The file did not generate a tombstone..false positive"
                    continue
