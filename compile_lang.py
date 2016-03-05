#! /usr/bin/env python3

import os
import tempfile
import subprocess
import time
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
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        self.addr = addr
        self.socket.bind('tcp://{addr}:{port}'.format(addr=self.addr, port=CompilerProducer.PORT))

    def listen(self):
        reg_msg = pb_compiler_pb2.RegisterCompilerService()
        address, message = self.socket.recv_multipart()
        ret = reg_msg.MergeFromString(message)
        self._add_compiler(reg_msg, address)

    def dispatch_req(self, language, code):
        worker_list = []
        try:
            worker_list_name = '{}'.format(language.name) + '_Workers'
            print(worker_list_name)
            worker_list = getattr(self, worker_list_name)
        except AttributeError as e:
            print('no worker support for {}'.format(language.name))
        req = pb_compiler_pb2.CompileRequest()
        req.code = code
        self.socket.send_multipart([worker_list[0], req.SerializeToString()])

    def _add_compiler(self, reg_msg, address):
        try:
            lang = reg_msg.Language.Name(reg_msg.lang)
            worker_list_name = '{}'.format(lang) + '_Workers'
            getattr(self, worker_list_name).append(address)
            print('Adding {} worker'.format(lang))
        except AttributeError as e:
            print('Adding {} worker list'.format(lang))
            setattr(self, worker_list_name, [])
            getattr(self, worker_list_name).append(address)

    def wait_for_worker(self, language):
        worker_list_name = '{}'.format(language.name) + '_Workers'
        while not hasattr(self, worker_list_name):
            time.sleep(1)
            pass
        
    def __call__(self):
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
        self.codeq = Queue()
        self.socket = self.context.socket(zmq.DEALER)

    def connect(self):
        self.socket.connect('tcp://{addr}:{port}'.format(addr=self.addr, port=CompilerProducer.PORT))
        reg = pb_compiler_pb2.RegisterCompilerService()
        reg.lang = self.lang_type
        reg.procarch = self.procarch
        reg.version = self.compiler_version
        self.socket.send(reg.SerializeToString())

    def wait_for_req(self):
        request = pb_compiler_pb2.CompileRequest()
        message = self.socket.recv()
        ret = request.MergeFromString(message)
        self.codeq.put(message)
        print('req recv\'d {} ret {}'.format(request, ret))

    def get_compile_req(self):
        return self.codeq.get()

    def __call__(self):
        while True:
            self.wait_for_req()

class RemoteCCompiler():
    def __init__(self):
        self.worker = CompilerWorker(pb_compiler_pb2.RegisterCompilerService.C)
        self.worker.connect()
        self.worker_thread = Thread(target=worker)
        self.worker_thread.start()

    def run_compiler(self):
        while True:
            msg = self.worker.get_compile_req()
            print(msg)

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
