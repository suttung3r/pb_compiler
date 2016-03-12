#!/usr/bin/env python3

import compile_lang
import RemoteCompilers
import pb_compiler_pb2
from threading import Thread

if __name__ == '__main__':
    rc = RemoteCompilers.RemoteCCompiler()
    print('remote compiler running')
    rc.run_compiler()
