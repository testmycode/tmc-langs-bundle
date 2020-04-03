import json, hashlib, os, pathlib, re, subprocess, platform
import resource_urls

def strip_timestamps(x):
    x = re.sub(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", "0000-00-00 00:00:00", x)
    x = re.sub(r"[0-9\.]+ s", "0.000s", x)
    x = re.sub(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+[0-9]{2}:[0-9]{2}", "0000-00-00T00:00:00+00:00", x)
    x = re.sub(r"\[Thread-[0-9]+\]", "[Thread-0]", x)
    x = re.sub(r"\tat .+\(((Native Method)|(Unknown Source)|(.+\.java:[0-9]+))\)+", "\t Traceback", x)
    x = re.sub(r"(\r?\n\t Traceback)+(\r?\n\t\.\.\. [0-9]+ more)?", "\n\tTraceback", x)
    return x

def call_original(x):
    stdout = open('resources/stdout_original', 'w')
    if platform.system() == "Windows":
        subprocess.call(['java', '-jar', 'resources/'+resource_urls.tmc_langs_name, *x.split(' ')],
                    stdout=stdout, stderr=stdout, shell=True)
    else:
        subprocess.call(['java -jar resources/'+resource_urls.tmc_langs_name+' '+x],
                    stdout=stdout, stderr=stdout, shell=True)
    stdout.close()
    stdout = open('resources/stdout_original')
    content = stdout.read()
    stdout.close()
    os.remove('resources/stdout_original')
    return content

def call_bundled(x):
    stdout = open('resources/stdout_bundled', 'w')
    if platform.system() == "Windows":
        subprocess.call(['bundle_out\\jre\\bin\\java.exe', '-jar', 'bundle_out/'+resource_urls.tmc_langs_name, *x.split(' ')], stdout=stdout,stderr=stdout, shell=True)
    else:
        subprocess.call(['bundle_out/jre/bin/java -jar bundle_out/'+resource_urls.tmc_langs_name+' '+x], stdout=stdout, stderr=stdout, shell=True)
    stdout.close()
    stdout = open('resources/stdout_bundled')
    content = stdout.read()
    stdout.close()
    os.remove('resources/stdout_bundled')
    return content

def run_tests(call_fn):
    output = {}
    if "tmp.json" in os.listdir("resources"):
        os.remove("resources/tmp.json")
    if "tmp.zip" in os.listdir("resources"):
        os.remove("resources/tmp.zip")
    for exercise in os.listdir("resources/exercises"):
        exercise_path = os.path.abspath("resources/exercises/"+exercise)
        
        test_out = strip_timestamps(call_fn("run-tests --exercisePath=./resources/exercises/{} --outputPath=./resources/tmp.json".format(exercise)))
        try:
            f = open("resources/tmp.json")
            t_json = json.loads(f.read())
            f.close()
            os.remove("resources/tmp.json")
            if "logs" in t_json:
                for t in t_json["logs"]:
                    t_json["logs"][t] = strip_timestamps(''.join(map(lambda x: chr(x), t_json["logs"][t])))
            test_result = json.dumps(t_json)
            
        except Exception as ex:
            test_result = str(ex)
        
        compress_out = strip_timestamps(call_fn("compress-project --exercisePath=./resources/exercises/{} --outputPath=./resources/tmp.zip".format(exercise)))
        try:
            f = open("resources/tmp.zip", 'rb')
            compress_result = len(f.read())
            f.close()
            os.remove("resources/tmp.zip")
        except OSError as ex:
            compress_result = str(ex)
        
        output[exercise] = {"test_out": test_out, "test_result": test_result, "compress_out": compress_out, "compress_result": compress_result}
    return output

def generate_reference_output():
    return run_tests(call_original)

def test_bundle(reference):
    return run_tests(call_bundled) == reference
