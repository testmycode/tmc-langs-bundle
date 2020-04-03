import glob, json, os, pathlib, platform, re, shutil, sys, tarfile
from zipfile import ZipFile
from urllib.request import urlretrieve
import resource_urls, test_bundle

target_platform = {"Linux": "linux", "Darwin": "mac", "Windows": "windows"}[platform.system()]
if target_platform != "mac":
    target_platform += {"x86_64": "64", "AMD64": "64", "i386": "32", "x86": "32"}[platform.machine()]

print("Detected platform:", target_platform)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

if "resources" not in os.listdir():
    os.mkdir("resources")

if resource_urls.packr_name not in os.listdir("resources"):
    print("Downloading packr...", end='', flush=True)
    urlretrieve(resource_urls.packr_url, "resources/"+resource_urls.packr_name)
    print("Done!")
    
jre_archive = "jre8_"+target_platform+".zip"

if jre_archive not in os.listdir("resources"):
    if target_platform not in resource_urls.openjdk_builds:
        print("Java RE for platform '{}' unavailable.")
        sys.exit(1)
    print("Downloading JRE from {}...".format(resource_urls.openjdk_builds[target_platform]), end='', flush=True)
    if resource_urls.openjdk_builds[target_platform].endswith('.tar.gz'):
        urlretrieve(resource_urls.openjdk_builds[target_platform], "resources/temp.tar.gz")
        with tarfile.open("resources/temp.tar.gz") as tf:
            with ZipFile("resources/"+jre_archive, "w") as zf:
                for member in tf:
                    ef = tf.extractfile(member)
                    if ef:
                        zf.writestr(member.name, ef.read())
        os.remove("resources/temp.tar.gz")
    else:
        urlretrieve(resource_urls.openjdk_builds[target_platform], "resources/"+jre_archive)
    print("Done!")

if resource_urls.tmc_langs_name not in os.listdir("resources"):
    print("Downloading {}...".format(resource_urls.tmc_langs_name), end='', flush=True)
    urlretrieve(resource_urls.tmc_langs_url, "resources/"+resource_urls.tmc_langs_name)
    print("Done!")
    
if "exercises" not in os.listdir("resources"):
    if resource_urls.test_course_name not in os.listdir("resources"):
        print("Downloading test course archive...", end='', flush=True)
        urlretrieve(resource_urls.test_course_url, "resources/"+resource_urls.test_course_name)
        print("Done!")
    with ZipFile("resources/"+resource_urls.test_course_name) as zf:
        zf.extractall("resources", [i for i in zf.namelist() if i.count('/') >= 2 and i.split('/')[1] not in
            {'private', 'scripts',
             'most_errors', 'arith_funcs', 'java_gui', 'trivial', 'trivial_with_code_review'}]) # Ignore ant-based java exercises
        os.rename("resources/tmc-testcourse-master", "resources/exercises")
    os.remove("resources/"+resource_urls.test_course_name)
    
if "reference_output.json" not in os.listdir("resources"):
    print("Generating reference output using system JRE...", end='', flush=True)
    _ = test_bundle.generate_reference_output() # First run tends to have different output
    reference_output = test_bundle.generate_reference_output()
    with open("resources/reference_output.json", 'w') as file:
        json.dump(reference_output, file)
    print("Done!")

with open("resources/reference_output.json", 'r') as file:
    reference = json.load(file)

if "bundle_out" not in os.listdir():
    packr_options = {"platform": target_platform, "jdk": "resources/"+jre_archive, "executable": "tmc-langs-cli",
                 "classpath": "resources/"+resource_urls.tmc_langs_name,
                 "mainclass": "fi.helsinki.cs.tmc.langs.cli.Main",
                 "output": "bundle_out", "minimizejre": "resources/packr_minimize.json", "verbose": ""}
    with open("resources/packr_minimize.json", "w") as file:
        json.dump({"reduce": [{"archive": "jre/lib/rt.jar", "paths": [
            "com/sun/corba", "com/sun/jndi", "com/sun/media", "com/sun/naming",
            "com/sun/rowset", "com/sun/script", "sun/applet", "sun/corba", "sun/management"
            ]}], "remove": []}, file)
    os.system('java -jar resources/packr.jar ' + ' '.join('--'+i+' '+j for i, j in packr_options.items()))
    if platform.system() == 'Linux':
        os.chmod("bundle_out/jre/bin/java", 0b0111000000)

if not test_bundle.test_bundle(reference):
    print("Initial bundle test failed")
    sys.exit(1)

all_files = [(str(i), i.name, i.stat().st_size) for i in pathlib.Path("bundle_out/jre").glob('**/*') if i.is_file()]
removed_files = []
kept_files = []

if platform.system() == "Linux":
    keep_set = {"bin/java", "lib/rt.jar", "lib/amd64/libjava.so", "lib/amd64/libzip.so",
                "lib/amd64/libnio.so", "lib/amd64/libnet.so", "lib/amd64/server/libjvm.so",
                "lib/amd64/libverify.so", "lib/amd64/jli/libjli.so", "lib/amd64/jvm.cfg",
                "lib/tzdb.dat", "lib/currency.data"}
    keep_set = set(map(lambda x: "bundle_out/jre/"+x, keep_set))
elif platform.system() == "Windows":
    keep_set = {"bin/java.exe", "bin/nio.dll", "bin/net.dll", "bin/verify.dll", "bin/zip.dll",
                "bin/java.dll", "bin/server/jvm.dll", "bin/msvcr120.dll", "lib/tzdb.dat",
                "lib/currency.data", "lib/tzmappings", "lib/rt.jar", "lib/amd64/jvm.cfg"}
    keep_set = set(map(lambda x: "bundle_out\\jre\\"+x.replace('/', '\\'), keep_set))
else:
    keep_set = set()
probably_remove = []
probably_keep = []

for i in all_files:
    if i[0] in keep_set:
        probably_keep.append(i)
    else:
        probably_remove.append(i)
        
if "stash" in os.listdir():
    shutil.rmtree("stash")
os.mkdir("stash")

current_files = probably_remove + probably_keep

file_stack = [[i] for i in probably_keep] + [list(probably_remove)]
iteration = 0

while file_stack:
    file_list = file_stack.pop()
    for num, (path, name, size) in enumerate(file_list):
        os.rename(path, "stash/"+str(num))
    if test_bundle.test_bundle(reference):
        for num, file in enumerate(file_list):
            os.remove("stash/"+str(num))
            removed_files.append(file)
            current_files.remove(file)
    else:
        if len(file_list) == 1:
            for num, file in enumerate(file_list):
                os.rename("stash/"+str(num), file[0])
                kept_files.append(file)
                current_files.remove(file)
        elif len(file_list) == 2:
            os.rename("stash/0", file_list[0][0])
            if test_bundle.test_bundle(reference):
                os.remove("stash/1")
                removed_files.append(file_list[1])
                kept_files.append(file_list[0])
            else:
                os.rename("stash/1", file_list[1][0])
                kept_files.append(file_list[1])
                os.rename(file_list[0][0], "stash/0")
                if test_bundle.test_bundle(reference):
                    removed_files.append(file_list[0])
                    os.remove("stash/0")
                else:
                    os.rename("stash/0", file_list[0][0])
                    kept_files.append(file_list[0])
            current_files.remove(file_list[0])
            current_files.remove(file_list[1])
        else:
            for num, (path, name, size) in enumerate(file_list):
                os.rename("stash/"+str(num), path)
            file_stack.append(file_list[:len(file_list)//2])
            file_stack.append(file_list[len(file_list)//2:])
    print("Iteration {}: Checked {}, Kept/Removed/Undetermined ({}/{}/{})".format(iteration, len(file_list), len(kept_files), len(removed_files), len(current_files)))
    iteration += 1

for directory, _, _ in os.walk('bundle_out/jre'):
    try:
        os.removedirs(directory)
    except OSError:
        pass

if test_bundle.test_bundle(reference):
    print("Final bundle test passed, {} files totaling {} bytes kept".format(len(kept_files), sum(map(lambda x: x[2], kept_files))))
else:
    print("Final bundle test failed!")
