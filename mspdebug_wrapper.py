#!/usr/bin/python

import argparse
import logging
import os, os.path
import subprocess
import signal
import time

DOTFILE = '.mspdebug'

logger = logging.getLogger(__name__)
logger.propagate = False

def parse_args ():
    parser = argparse.ArgumentParser(description='mspdebug wrapper')
    parser.add_argument('executable', help='msp430 executable')
    parser.add_argument('-s', '--simulator', action='store_true',
            help='use simulator')
    parser.add_argument('-b', '--breakpoint', default='0xffff',
            help='breakpoint that means program has exited (default 0xffff)')
    parser.add_argument('-L', '--library-path',
            help='directory that contains libmsp430.so')
    parser.add_argument('-d', '--debug', action='store_true',
            help='show debugging output')
    return parser.parse_args()

def write_dotfile (breakaddr, executable):
    cmds = (
            'sym import {}'.format(executable),
            'prog {}'.format(executable),
            'delbreak', # clear all breakpoints
            'setbreak {}'.format(breakaddr),
            'run'
           )
    with open(DOTFILE, 'w') as dotfile:
        dotfile.write('\n'.join(cmds))
        dotfile.write('\n')

def run_mspdebug (simulator=False):
    # LD_LIBRARY_PATH=/usr/local/lib mspdebug -j tilib
    if simulator:
        cmd = 'mspdebug sim'
    else:
        cmd = 'mspdebug tilib'
    logger.debug('Starting {}'.format(cmd))
    proc = subprocess.Popen(cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    try:
        # read until a breakpoint reached.  catch register values
        while True:
            foo = proc.stdout.readline().strip()
            logger.debug('LINE: [{}]'.format(foo))
            if foo.startswith('( '):
                logger.info(foo)
            if foo == 'Press Ctrl+D to quit.':
                logger.debug('Got mspdebug prompt')
                break
        logger.debug('Exiting mspdebug...')
        proc.stdin.write('exit\n')
    except KeyboardInterrupt:
        logger.critical('caught interrupt; sending SIGINT to mspdebug')
        proc.send_signal(signal.SIGINT)
        time.sleep(0.2)
    finally:
        proc.wait()
        logger.debug('mspdebug process exited cleanly.')

def remove_dotfile ():
    os.unlink(DOTFILE)

if __name__ == '__main__':
    args = parse_args()

    logLevel = (args.debug and logging.DEBUG or logging.INFO)
    logHandler = logging.StreamHandler()
    logFormat = '%(levelname)s: %(message)s'
    logHandler.setFormatter(logging.Formatter(logFormat))
    logger.setLevel(logLevel)
    logger.addHandler(logHandler)

    if args.library_path:
        msplib = os.path.join(args.library_path, 'libmsp430.so')
        if not os.path.exists(msplib):
            logger.warn('{} does not exist'.format(msplib))
        try:
            libpath = os.environ['LD_LIBRARY_PATH'].split(os.pathsep)
        except KeyError:
            libpath = []
        libpath.append(args.library_path)
        os.environ['LD_LIBRARY_PATH'] = os.pathsep.join(libpath)

    write_dotfile(args.breakpoint, args.executable)
    run_mspdebug(args.simulator)
    remove_dotfile()
