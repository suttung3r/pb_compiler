#! /usr/bin/env python3

from enum import Enum, unique
import os
import tempfile
import subprocess

from subprocess import CalledProcessError

@unique
class SUPPORTED_LANGUAGES(Enum):
  C = 0,
  CPP = 1,
  PYTHON = 2,
  RUST = 3

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
        with tempfile.NamedTemporaryFile(suffix=C_Compiler.SUFFIX, dir=self.tempdir) as f:
            f.write(bytes(self.code, 'UTF-8'))
            f.flush()
            f.seek(0)
            output_fname = os.path.join(self.tempdir, self.out_fname)
            try:
                subprocess.check_output([C_Compiler.COMPILER, f.name, '-o', output_fname],
                                        stderr=subprocess.STDOUT)
                if rm_exe is True:
                    os.remove(output_fname)
            except CalledProcessError as e:
                raise CompilerException(e.returncode, self.code, e.output)

def run_compiler(lang, text):

    compiler = CompilerBase(text)
    if lang == SUPPORTED_LANGUAGES.C:
        compiler = C_Compiler(code=text)
    return compiler.compile_code()

def main():
    sample_c_prog = '#include "stdio.h"\nint main() { return 0;}';
    run_compiler(SUPPORTED_LANGUAGES.C, sample_c_prog)
    print('ran compiler successfully {}')
    # Missing semi-colon after return
    try:
        bad_c_prog = '#include "stdio.h"\nint main() { return 0}';
        res = run_compiler(SUPPORTED_LANGUAGES.C, bad_c_prog)
    except CompilerException as e:
        print('ran compiler with result {} output {}'.format(e.ret, e.output))

if __name__ == '__main__':
    main()
