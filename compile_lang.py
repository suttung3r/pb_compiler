#! /usr/bin/env python3

import os
import queue
import subprocess
from subprocess import CalledProcessError
import tempfile
from threading import Thread
import time
import zmq

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
        self.worker_lists = []
        self.result_q = queue.Queue()

    def listen(self):
        address, message = self.socket.recv_multipart()
        for worker_list_name in self.worker_lists:
            if address in getattr(self, worker_list_name):
                resp_msg = pb_compiler_pb2.CompileResult()
                ret = resp_msg.MergeFromString(message)
                self._put_compile_result(resp_msg.success)
                return
        reg_msg = pb_compiler_pb2.RegisterCompilerService()
        print('msg recv\'d {}'.format(message))
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
    def _put_compile_result(self, result):
        self.result_q.put(result)

    def get_compile_result(self):
        return self.result_q.get()
 
    def _add_compiler(self, reg_msg, address):
        lang = reg_msg.Language.Name(reg_msg.lang)
        worker_list_name = '{}'.format(lang) + '_Workers'
        try:
            getattr(self, worker_list_name).append(address)
            print('Adding {} worker'.format(lang))
        except AttributeError as e:
            print('Adding {} worker list'.format(lang))
            setattr(self, worker_list_name, [])
            getattr(self, worker_list_name).append(address)
            self.worker_lists.append(worker_list_name)

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
        self.codeq = queue.Queue()
        self.socket = self.context.socket(zmq.DEALER)

    def connect(self):
        self.socket.connect('tcp://{addr}:{port}'.format(addr=self.addr, port=CompilerProducer.PORT))
        reg = pb_compiler_pb2.RegisterCompilerService()
        reg.lang = self.lang_type
        reg.procarch = self.procarch
        reg.version = self.compiler_version
        self.socket.send(reg.SerializeToString())

    def wait_for_req(self):
        message = self.socket.recv()
        self.codeq.put(message)

    def get_compile_req(self):
        return self.codeq.get()

    def send_response(self, bytes_in):
          self.socket.send(bytes_in)

    def __call__(self):
        while True:
            self.wait_for_req()

class RemoteCCompiler():
    def __init__(self, compiler_version='noversion', procarch='noarch',
                 addr='localhost'):
        self.worker = CompilerWorker(pb_compiler_pb2.RegisterCompilerService.C, compiler_version=compiler_version, procarch=procarch, addr=addr)
        self.worker.connect()
        self.worker_thread = Thread(target=self.worker)
        self.worker_thread.start()

    def run_compiler(self):
        while True:
            print('waiting for request')
            comp_req = pb_compiler_pb2.CompileRequest()
            msg = self.worker.get_compile_req()
            comp_req.MergeFromString(msg)
            print(comp_req.code)
            compiler = C_Compiler(code=comp_req.code)
            comp_res = pb_compiler_pb2.CompileResult()
            comp_res.success = False
            try:
                compiler.compile_code()
                comp_res.success = True
                print('Compiler succeeded.')
            except CompilerException as e:
                print('Something failed')
            self.worker.send_response(comp_res.SerializeToString())
            print('Waiting for next req')

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
