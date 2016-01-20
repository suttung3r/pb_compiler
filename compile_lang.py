#! /usr/bin/env python3

import os
import tempfile
import subprocess

class CompilerBase(object):

  DIR = '/tmp'

  def __init__(self, code=''):
      self.code = str(code)

  def compile_code(self):
      print('doing nothing')
      pass

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
            subprocess.call([C_Compiler.COMPILER, f.name])

def run_compiler(lang, text):

    compiler = CompilerBase(text)
    if lang == 'C':
        compiler = C_Compiler(text)
    compiler.compile_code()

if __name__ == '__main__':
  print('we\'re good')
