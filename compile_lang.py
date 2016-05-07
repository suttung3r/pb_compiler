#! /usr/bin/env python3

import hashlib
import logging
import os
import queue
import subprocess
from subprocess import CalledProcessError
import tempfile
import time
import zmq

import pb_compiler_pb2
from test import compile_lang_test
from compile_lang_enums import SUPPORTED_LANGUAGES


class CompilerException(Exception):

  def __init__(self, ret, text, output):
      self.ret = ret
      self.text = text
      self.output = output

  def __str__(self):
      return repr(self)

class CompilerBase(object):
  """
  Base object for compilers

  Note tempdir constructor arg - this is one method of separating
  outputs from different compilers running on the same host
  """
  def __init__(self, code='', tempdir='/tmp', *args, **kwargs):
      self.code = code
      self.tempdir = tempdir

  def compile_code(self):
      """Return standard unix return code"""
      return 0

  def get_version(self):
      """Return None. Meant to be overridden."""
      return None

class C_Compiler(CompilerBase):
    """
    C Compiler object. Wraps gcc by default

    out_fname constructor arg allows specification of output filename
    default is b.out to avoid conflict with standard gcc output
    """
    COMPILER = 'gcc'
    SUFFIX = '.c'

    def __init__(self, out_fname='b.out', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.out_fname = out_fname

    def get_version(self):
        res = subprocess.check_output([self.__class__.COMPILER, '--version'],
                                      stderr=subprocess.STDOUT)
        # gcc useful version output is first line
        return res.splitlines()[0]

    def compile_code(self, rm_exe=True):
        logging.debug('{} compiling {}'.format(self.__class__.__name__, self.code))
        with tempfile.NamedTemporaryFile(suffix=self.__class__.SUFFIX, dir=self.tempdir) as f:
            f.write(bytes(self.code, 'UTF-8'))
            f.flush()
            f.seek(0)
            output_fname = os.path.join(self.tempdir, self.out_fname)
            try:
                subprocess.check_output([self.__class__.COMPILER, f.name, '-o', output_fname],
                                        stderr=subprocess.STDOUT)
                if rm_exe is True:
                    logging.debug('{} removing output of {}'.format(self.__class__.__name__, self.code))
                    os.remove(output_fname)
            except CalledProcessError as e:
                print('compilation failed')
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
    """
    Producer object for compile jobs

    Workers connect over ZMQ Router socket with language/version/processor arch info

    ZMQ manages Producer/Worker relationship by assigning a unique address to each
    worker that connects, even from the same host. These addresses are stored in a 
    list of available workers.

    Workers perform compile jobs atomically. So a result from a given worker is
    guaranteed to be that of the least-recently dispatched job.
    """
    PORT = 9002

    def __init__(self, addr='127.0.0.1'):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        self.addr = addr
        self.socket.bind('tcp://{addr}:{port}'.format(addr=self.addr, port=CompilerProducer.PORT))
        self.worker_lists = []
        self.result_q = queue.Queue()
        self.worker_q_set = {}

    def listen(self):
        address, message = self.socket.recv_multipart()
        for worker_list_name in self.worker_lists:
            if address in getattr(self, worker_list_name):
                resp_msg = pb_compiler_pb2.CompileResult()
                print('res msg recv\'d {} address {}'.format(message, address))
                ret = resp_msg.MergeFromString(message)
                self._put_compile_result((self.worker_q_set[address].pop(0), resp_msg.success))
                return
        reg_msg = pb_compiler_pb2.RegisterCompilerService()
        print('reg msg recv\'d {} address {}'.format(message, address))
        ret = reg_msg.MergeFromString(message)
        self._add_compiler(reg_msg, address)

    def dispatch_req(self, language, code):
        """
        Dispatch a compile request

        Returns the md5 sum of the message sent and the worker address. This is
        for client management of the requests. In theory, some sort of caching
        could be performed if the same request is going to the same client frequently
        enough.

        Returns -1 if no worker of the desired type is available
        """
        worker_list = []
        try:
            worker_list_name = '{}'.format(language.name) + '_Workers'
            worker_list = getattr(self, worker_list_name)
        except AttributeError as e:
            print('no worker support for {}'.format(language.name))
            return -1
        req = pb_compiler_pb2.CompileRequest()
        req.code = code
        msg = req.SerializeToString()
        self.socket.send_multipart([worker_list[0], msg])
        m = hashlib.md5(worker_list[0] + msg).hexdigest()
        self.worker_q_set[worker_list[0]].append(m)
        return m

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
            self.worker_q_set[address] = []

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

    """
    Remote worker objects for CompilerProducer

    Handles socket management. Performs initial connection request upon calling
    connect method. Then waits for jobs from producer object in separate thread.
    Received requests are placed on queue for consumption by client.
    """

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
    run_compiler(compile_lang_test.SampleCProg2.lang, compile_lang_test.SampleCProg2.code)
    print('ran C compiler successfully again w/stdlib')
    # Missing semi-colon after return
    try:
        run_compiler(compile_lang_test.BadCProg.lang, compile_lang_test.BadCProg.code)
    except CompilerException as e:
        print('C compiler failed with result {}'.format(e.ret))

    # verify breakage with c++
    try:
        res = run_compiler(compile_lang_test.CPPToC.lang, compile_lang_test.CPPToC.code)
    except CompilerException as e:
        print('C compiler failed with result {}'.format(e.ret))

    res = run_compiler(compile_lang_test.SampleCPP.lang, compile_lang_test.SampleCPP.code)
    print('ran CPP compiler successfully')

    res = run_compiler(compile_lang_test.RustProg.lang, compile_lang_test.RustProg.code)
    print('ran Rust compiler successfully')

if __name__ == '__main__':
    main()
