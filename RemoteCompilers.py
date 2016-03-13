import logging
import tempfile
from threading import Thread

from compile_lang import CompilerWorker, C_Compiler, Rust_Compiler, \
  CPP_Compiler, CompilerException
import pb_compiler_pb2


class RemoteCompiler():
    """
    This class instantiates a CompilerWorker object and associated Compiler

    Associations are mapped in CompilerEnumToType

    This class is intended for multi threaded use. The instantiating thread
    will block waiting for compiler requests from the Compiler worker. The other
    thread will run the CompilerWorker object which will wait for requests from
    the remote producer.
    """
    CompilerEnumToType = {
        pb_compiler_pb2.RegisterCompilerService.C: C_Compiler,
        pb_compiler_pb2.RegisterCompilerService.CPP: CPP_Compiler,
        pb_compiler_pb2.RegisterCompilerService.RUST: Rust_Compiler
    }

    def __init__(self, lang, compiler_version='noversion', procarch='noarch',
                 addr='localhost'):
        self.worker = CompilerWorker(lang, compiler_version=compiler_version, procarch=procarch, addr=addr)
        self.worker_thread = Thread(target=self.worker)
        self.worker_thread.start()
        self.lang = lang

    def run_compiler(self):
        self.worker.connect()
        while True:
            logging.info('waiting for request')
            comp_req = pb_compiler_pb2.CompileRequest()
            msg = self.worker.get_compile_req()
            comp_req.MergeFromString(msg)
            tempdir = tempfile.mkdtemp()
            compiler = RemoteCompiler.CompilerEnumToType[self.lang](code=comp_req.code, tempdir=tempdir)
            comp_res = pb_compiler_pb2.CompileResult()
            comp_res.success = False
            try:
                compiler.compile_code()
                comp_res.success = True
            except CompilerException as e:
                logging.info('Compilation failed')
            self.worker.send_response(comp_res.SerializeToString())

    def log(self, *args, **kwargs):
        print('{}: '.format(pb_compiler_pb2.RegisterCompilerService.Language.Name(self.lang)) + ''.format(args, kwargs))
