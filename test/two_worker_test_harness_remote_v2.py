#!/usr/bin/env python3

import logging

import compile_lang
import RemoteCompilers
import pb_compiler_pb2
from threading import Thread

# Same as two_worker_test_harness_remote but uses RemoteCompiler object
# with different types

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    rc_C = RemoteCompilers.RemoteCompiler(pb_compiler_pb2.RegisterCompilerService.C)
    rc_RUST = RemoteCompilers.RemoteCompiler(pb_compiler_pb2.RegisterCompilerService.RUST)
    rc_C_Thread = Thread(target=rc_C.run_compiler)
    rc_RUST_Thread = Thread(target=rc_RUST.run_compiler)
    rc_C_Thread.start()
    print('remote C compiler running')
    rc_RUST_Thread.start()
    print('remote Rust compiler running')

