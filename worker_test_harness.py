#!/usr/bin/env python3

import compile_lang
import pb_compiler_pb2

if __name__ == '__main__':
    producer = compile_lang.CompilerWorker(pb_compiler_pb2.RegisterCompilerService.CPP)
    producer.connect()

