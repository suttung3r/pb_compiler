#!/usr/bin/env python3

import compile_lang
import pb_compiler_pb2

if __name__ == '__main__':
    worker1 = compile_lang.CompilerWorker(pb_compiler_pb2.RegisterCompilerService.C)
    worker2 = compile_lang.CompilerWorker(pb_compiler_pb2.RegisterCompilerService.CPP)
    worker1.connect()
    worker2.connect()


