# tmc-langs-bundle

Creates a stripped down JRE to be used with `tmc-langs-cli` on systems where Java is not installed.
Creating a bundled JRE requires a well-configured system matching the target platform, e.g. to create a bundle capable of
running Python 3 exercise tests via `tmc-langs-cli` on x86-64 Windows, a matching Windows system with Python 3 and JRE 8 installed
is required. 

The size of the bundle is approximately 50 MB, depending on the target platform and JDK variant.

The bundling process has been tested on 64-bit Linux system and a Windows 10 VM, but not on OS X yet.
Only the `compress-project` and `run-tests` commands are tested, using the `tmc-testcourse` exercises
(excluding non-maven Java exercises). 

## Instructions

To run:

`python3 bundle.py`

The script will download some required files and libraries, including the test exercises, `tmc-langs-cli` and an OpenJDK 8 build.
The bundling process will take a fair amount of time.
