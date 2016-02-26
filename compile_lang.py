#! /usr/bin/env python3

import os
import tempfile
import subprocess
import zmq

from subprocess import CalledProcessError
# import pb_compiler as pb_compiler_pb2
import pb_compiler_pb2, compile_lang_test
from compile_lang_enums import SUPPORTED_LANGUAGES


class CompilerException(Exception):

  def __init__(self, ret, text, output):
      self.ret = ret
      self.text = text
      self.output = output

  def __str__(self):
      return repr(self)

class CompilerBase(object):

  def __init__(self, code='', tempdir='/tmp', *args, **kwargs):
      self.code = code
      self.tempdir = tempdir

  def compile_code(self):
      """Return standard unix return code"""
      return 0

class C_Compiler(CompilerBase):
    COMPILER = 'gcc'
    SUFFIX = '.c'

    def __init__(self, out_fname='b.out', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.out_fname = out_fname

    def compile_code(self, rm_exe=True):
        with tempfile.NamedTemporaryFile(suffix=self.__class__.SUFFIX, dir=self.tempdir) as f:
            f.write(bytes(self.code, 'UTF-8'))
            f.flush()
            f.seek(0)
            output_fname = os.path.join(self.tempdir, self.out_fname)
            try:
                subprocess.check_output([self.__class__.COMPILER, f.name, '-o', output_fname],
                                        stderr=subprocess.STDOUT)
                if rm_exe is True:
                    os.remove(output_fname)
            except CalledProcessError as e:
                raise CompilerException(e.returncode, self.code, e.output)

class CPP_Compiler(C_Compiler):
    COMPILER = 'g++'
    SUFFIX = '.cpp'

    def __init__(self, out_fname='b.out', *args, **kwargs):
        super().__init__(*args, **kwargs)


class Rust_Compiler(C_Compiler):
    COMPILER = 'rustc'
    SUFFIX = '.rs'

    def __init__(self, out_fname='out', *args, **kwargs):
        super().__init__(*args, **kwargs)


class CompilerProducer():
    PORT = 9002

    def __init__(self, addr='127.0.0.1'):
        print('inited')
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        self.addr = addr
        self.socket.bind('tcp://{addr}:{port}'.format(addr=self.addr, port=CompilerProducer.PORT))

    def listen(self):
        print('started')
        reg_msg = pb_compiler_pb2.RegisterCompilerService()
        address, empty, message = self.socket.recv_multipart()
        print(message)
        ret = reg_msg.MergeFromString(message)
        print(reg_msg)

    def dispatch_req(self, code, language):
        pass

    def __call__(self):
        print('called')
        while True:
            self.listen()
            pass


class CompilerWorker():

    def __init__(self, lang_type, compiler_version='noversion',
                 procarch='novalue', addr='localhost'):
        self.context = zmq.Context()
        self.addr = addr
        self.lang_type = lang_type
        self.compiler_version = compiler_version
        self.procarch = procarch
        self.socket = self.context.socket(zmq.REQ)

    def connect(self):
        self.socket.connect('tcp://{addr}:{port}'.format(addr=self.addr, port=CompilerProducer.PORT))
        reg = pb_compiler_pb2.RegisterCompilerService()
        reg.lang = self.lang_type
        reg.procarch = self.procarch
        reg.version = self.compiler_version
        self.socket.send(reg.SerializeToString())

def try_messages():
    clnt = CompilerWorker()

def run_compiler(lang, text):

    compiler = CompilerBase(text)
    if lang == SUPPORTED_LANGUAGES.C:
        compiler = C_Compiler(code=text)
    elif lang == SUPPORTED_LANGUAGES.CPP:
        compiler = CPP_Compiler(code=text)
    elif lang == SUPPORTED_LANGUAGES.RUST:
        compiler = Rust_Compiler(code=text)
    return compiler.compile_code()

def main():
    run_compiler(compile_lang_test.SampleCProg.lang, compile_lang_test.SampleCProg.code)
    print('ran C compiler successfully')
    # Missing semi-colon after return
    try:
        run_compiler(compile_lang_test.BadCProg.lang, compile_lang_test.BadCProg.code)
    except CompilerException as e:
        print('ran C compiler with result {} output {}'.format(e.ret, e.output))

    # verify breakage with c++
    try:
        res = run_compiler(compile_lang_test.CPPToC.lang, compile_lang_test.CPPToC.code)
    except CompilerException as e:
        print('ran C compiler with result {} output {}'.format(e.ret, e.output))

    res = run_compiler(compile_lang_test.SampleCPP.lang, compile_lang_test.SampleCPP.code)
    print('ran CPP compiler successfully {}')

    res = run_compiler(compile_lang_test.RustProg.lang, compile_lang_test.RustProg.code)
    print('ran Rust compiler successfully {}')

if __name__ == '__main__':
    main()
