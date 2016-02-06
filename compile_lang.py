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
    sample_c_prog = '#include "stdio.h"\nint main() { return 0;}';
    run_compiler(SUPPORTED_LANGUAGES.C, sample_c_prog)
    print('ran C compiler successfully {}')
    # Missing semi-colon after return
    try:
        bad_c_prog = '#include "stdio.h"\nint main() { return 0}';
        res = run_compiler(SUPPORTED_LANGUAGES.C, bad_c_prog)
    except CompilerException as e:
        print('ran C compiler with result {} output {}'.format(e.ret, e.output))

    cpp_prog = 'using namespace std;\n#include <iostream>\nint main() {cout << "hello world" << endl;}'
    # verify breakage with c++
    try:
        res = run_compiler(SUPPORTED_LANGUAGES.C, cpp_prog)
    except CompilerException as e:
        print('ran C compiler with result {} output {}'.format(e.ret, e.output))

    res = run_compiler(SUPPORTED_LANGUAGES.CPP, cpp_prog)
    print('ran CPP compiler successfully {}')

    rust_prog = 'fn main() {\nprintln!("Hello, world");\n}'
    res = run_compiler(SUPPORTED_LANGUAGES.RUST, rust_prog)
    print('ran Rust compiler successfully {}')

if __name__ == '__main__':
    main()
