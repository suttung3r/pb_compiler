from threading import Thread

from compile_lang import CompilerWorker, C_Compiler, Rust_Compiler
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
            print('waiting for request')
            comp_req = pb_compiler_pb2.CompileRequest()
            msg = self.worker.get_compile_req()
            comp_req.MergeFromString(msg)
            print(comp_req.code)
            compiler = RemoteCompiler.CompilerEnumToType[self.lang](code=comp_req.code)
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
