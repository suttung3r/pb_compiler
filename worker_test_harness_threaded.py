#!/usr/bin/env python3

import compile_lang
import pb_compiler_pb2
from threading import Thread

if __name__ == '__main__':
    worker = compile_lang.CompilerWorker(pb_compiler_pb2.RegisterCompilerService.C)
    worker_thread = Thread(target=worker)
    worker.connect()
    worker_thread.start()
