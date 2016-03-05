#!/usr/bin/env python3

import compile_lang
import pb_compiler_pb2
from threading import Thread

if __name__ == '__main__':
    rc = compile_lang.RemoteCCompiler(pb_compiler_pb2.RegisterCompilerService.C)
    rc.run_compiler()
