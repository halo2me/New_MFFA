import sys
import argparse
import subprocess
import re
import threading
from fuzzer import Fuzzer
from utils import *
from triager import Triager
import shutil


def parse_argv(argv):
    parser = argparse.ArgumentParser(
        description="mffa use for fuzz android bin, and you should generate testcase before.\
                     use -h for more information",
        usage="python mffa.py [-d DIRECTOR] [-f LIST_DIRNAME] [-o OUTDIR] target_cmd ")
    parser.add_argument("-d", dest="diretory",
        help="This option specific the input directory of test-cases. You should use this "
             "option when you only have one device!")
    parser.add_argument("-f", dest="list_dirname",
        help="This option specific the filename of inputdirs. You should use this when "
             "you have multi-devices!")
    parser.add_argument("-o", dest="outdir", default="out",
                        help="The output dir you want")
   # parser.add_argument("-t",)
    parser.add_argument("-s", dest="device", default="", help="Use -s to specific device")
    parser.add_argument("target_cmd", nargs=argparse.REMAINDER,
        help="This is the cmd you use the bin on android ,and you should use \'@@\' "
             "instead of your input files ")
    return parser.parse_args(argv[1:])


def check_num_devices():
    print("Checking devices....")
    cmd = 'adb devices > devices.txt'
    run_subproc(cmd)
    with open('devices.txt', 'rw') as f1:
        devices = f1.readlines()
    count_devices = len(devices) - 2
    if count_devices < 1:
        print("Error, you should have one devices for fuzz")
        sys.exit(-1)
    dev = [None] * count_devices
    c = 0
    for i in range(1, len(devices) - 1):
        reg_device = re.compile('\S*\s')
        dev[c] = str(reg_device.findall(devices[i])[0])
        c = c + 1
    print("Finish Checking, find %d device" % count_devices)
    os.remove('devices.txt')
    return dev


def check_num_inputdir(list_dirname):
    print("Checking count of inputdirs....")
    with open(list_dirname, 'rw') as f:
        dirs = f.readlines()
    if dirs == None:
        print "You should specific one inputdir in your file"
        sys.exit(-1)
    for i in range(0, len(dirs)):
        dirs[i] = dirs[i].rstrip()
    return dirs


def fuzz(devs, dirs, cmd, logs_dir):

    '''for i in range(0, len(devs)):
        flush_log(devs[i])'''

    dir_num = 0
    threads = {}
    while True:
        for j in range(0, len(devs)):
            if dir_num >= len(dirs) :
                print 'All Fuzz Over !!!'
                return
            flush_log(devs[j])
            f = Fuzzer(dirs[dir_num], devs[j], cmd, logs_dir)
            threads[j] = threading.Thread(target=f.run)
            threads[j].start()
            dir_num += 1

        for j in range(0, len(threads)):
            threads[j].join()
            print ' Device ' + devs[j] + ' has finished fuzz round: ' + str(dir_num / len(devs) + 1)

        print '******* All devices have finished Fuzz round: ' + str(dir_num / len(devs) + 1)

        run_subproc('kill -9 $(pgrep -f logcat)')

        '''for i in range(0, len(devs)):
            flush_log(devs[i])'''


def triage(devs, target_cmd, logs_dir, issues_dir):
    logs = os.listdir(logs_dir)
    log_num = 0
    threads = {}
    while True:
        for j in range(0, len(devs)):
            if log_num >= len(logs):
                print 'All Triage Over !!!'
                return
            t=Triager(logs_dir + os.sep + logs[log_num],devs[j], target_cmd, issues_dir)
            log_num += 1
            if not t.dir_path:
                continue
            threads[j] = threading.Thread(target=t.run)
            threads[j].start()

        for j in range(0, len(threads)):
            threads[j].join()
            print ' Device ' + devs[j] + ' has finished triage round: ' + str(log_num / len(devs))

        print '******* All devices have finished Fuzz round: ' + str(log_num / len(devs))


def main(argv):
    if OS != 'Darwin' and OS != 'Linux':
        print 'Your system ' + OS + ' is not support!, Please use Mac OS or Linux to run it'
        sys.exit(-1)

    args = parse_argv(argv)

    if not args.target_cmd:
        print("you shold specific the android bin cmd, use -h for more help!")
        sys.exit(-1)

    if not (args.diretory or args.list_dirname):
        print("you shold specific at least one option of -d or -f, use -h for more help!")
        sys.exit(-1)

    if not args.device:
        devs = check_num_devices()
    elif os.system("adb -s " + args.device + " root") == 0:
        devs = [None] * 1
        devs[0] = args.device
    else:
        print ("Please specific an available device!!")
        sys.exit(-1)

    if os.path.isdir(args.outdir):
        shutil.rmtree(args.outdir)
    os.mkdir(args.outdir)

    logs_dir = args.outdir.rstrip(os.sep) + os.sep + 'logs'
    issues_dir = args.outdir.rstrip(os.sep) + os.sep + 'issues'

    if not os.path.isdir(logs_dir):
        os.mkdir(logs_dir)
    if not os.path.isdir(issues_dir):
        os.mkdir(issues_dir)


    if args.list_dirname :
        dirs = check_num_inputdir(args.list_dirname.rstrip(os.sep))
    else :
        dirs = [None] * 1;
        dirs[0] = args.diretory.rstrip(os.sep)

    fuzz(devs, dirs, args.target_cmd, logs_dir)

    devs = check_num_devices()
    triage(devs, args.target_cmd, logs_dir, issues_dir)


if __name__ == '__main__':
    main(sys.argv)