#! /usr/bin/env python3

import os
import tempfile
import subprocess

from subprocess import CalledProcessError

class CompilerException(Exception):

  def __init__(self, ret, text, output):
      self.ret = ret
      self.text = text
      self.output = output

  def __str__(self):
      return repr(self)

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
        with tempfile.NamedTemporaryFile(suffix=C_Compiler.SUFFIX, dir=CompilerBase.DIR) as f:
            f.write(bytes(self.code, 'UTF-8'))
            f.flush()
            f.seek(0)
            try:
                subprocess.check_output([C_Compiler.COMPILER, f.name], stderr=subprocess.STDOUT)
            except CalledProcessError as e:
                raise CompilerException(e.returncode, self.code, e.output)

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
    try:
        bad_c_prog = '#include "stdio.h"\nint main() { return 0}';
        res = run_compiler('C', bad_c_prog)
    except CompilerException as e:
        print('ran compiler with result {} output {}'.format(e.ret, e.output))
