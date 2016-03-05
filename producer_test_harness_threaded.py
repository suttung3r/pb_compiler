#!/usr/bin/env python3

import compile_lang
import pb_compiler_pb2
from compile_lang_enums import SUPPORTED_LANGUAGES
from compile_lang_test import SampleCProg
from threading import Thread

if __name__ == '__main__':
    producer = compile_lang.CompilerProducer()
    producer_thread = Thread(target=producer)
    producer_thread.start()
    producer.wait_for_worker(SUPPORTED_LANGUAGES.C)
    producer.dispatch_req(SUPPORTED_LANGUAGES.C, SampleCProg.code)
