#!/usr/bin/env python3

import compile_lang
import RemoteCompilers
import pb_compiler_pb2
from threading import Thread

if __name__ == '__main__':
    print "OBE with RemoteCompiler object. see two_worker_test_harness_remote_v2"
    # rc_C = RemoteCompilers.RemoteCCompiler()
    # rc_RUST = RemoteCompilers.RemoteRustCompiler()
    # rc_C_Thread = Thread(target=rc_C.run_compiler)
    # rc_RUST_Thread = Thread(target=rc_RUST.run_compiler)
    # rc_C_Thread.start()
    # print('remote C compiler running')
    # rc_RUST_Thread.start()
    # print('remote Rust compiler running')
