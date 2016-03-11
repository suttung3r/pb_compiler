#!/usr/bin/env python3

import compile_lang
import pb_compiler_pb2

if __name__ == '__main__':
    producer = compile_lang.CompilerProducer()
    producer.listen()
