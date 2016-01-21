#! /usr/bin/env python3

import os
import tempfile
import subprocess

from subprocess import CalledProcessError

class CompilerBase(object):

  DIR = '/tmp'

  def __init__(self, code=''):
      self.code = code

  def compile_code(self):
      """Return standard unix return code"""
      return 0

class C_Compiler(CompilerBase):
    COMPILER = 'gcc'
    SUFFIX = '.c'

    def __init__(self, code):
        super().__init__(code)

    def compile_code(self):
        ret = -1
        with tempfile.NamedTemporaryFile(suffix=C_Compiler.SUFFIX, dir=CompilerBase.DIR) as f:
            f.write(bytes(self.code, 'UTF-8'))
            f.flush()
            f.seek(0)
            try:
                ret = subprocess.check_call([C_Compiler.COMPILER, f.name])
            except CalledProcessError as e:
                ret = e.returncode
        return ret

def run_compiler(lang, text):

    compiler = CompilerBase(text)
    if lang == 'C':
        compiler = C_Compiler(text)
    return compiler.compile_code()

if __name__ == '__main__':
    sample_c_prog = '#include "stdio.h"\nint main() { return 0;}';
    res = run_compiler('C', sample_c_prog)
    print('ran compiler with result {}'.format(res))
    # Missing semi-colon after return
    bad_c_prog = '#include "stdio.h"\nint main() { return 0}';
    res = run_compiler('C', bad_c_prog)
    print('ran compiler with result {}'.format(res))
