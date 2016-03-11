from threading import Thread

from compile_lang import CompileWorker, C_Compiler
import pb_compiler_pb2

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
