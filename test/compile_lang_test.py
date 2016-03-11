from compile_lang_enums import SUPPORTED_LANGUAGES

class CompilerTest:
    code = ''
    lang = SUPPORTED_LANGUAGES.NONE

class SampleCProg(CompilerTest):
    code = '#include "stdio.h"\nint main() { return 0;}'
    lang = SUPPORTED_LANGUAGES.C

class BadCProg(CompilerTest):
    code = '#include "stdio.h"\nint main() { return 0}'
    lang = SUPPORTED_LANGUAGES.C

class CPPToC(CompilerTest):
    code = 'using namespace std;\n#include <iostream>\nint main() {cout << "hello world" << endl;}'
    lang = SUPPORTED_LANGUAGES.C

class SampleCPP(CPPToC):
    lang = SUPPORTED_LANGUAGES.CPP

class RustProg(CompilerTest):
    code = 'fn main() {\nprintln!("Hello, world");\n}'
    lang = SUPPORTED_LANGUAGES.RUST
