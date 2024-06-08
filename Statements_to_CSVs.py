import os
import time
import RBC_Statement_to_CSV as rbc

def timer(func):
    """just curious how long it takes. want to have verboseness"""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        stop = time.time()
        delta = stop - start
        print(f"Time taken = {delta}")
        return result
    return wrapper

@timer
def apply(path):
    accounted = []
    if os.path.isfile(path):
        # accounted.append(path)
        print('processing: ', path)
        accounted.append(rbc.main(path))
    elif os.path.isdir(path):
        for name, dirs, files in os.walk(path):
            dirs.sort()
            files.sort()
            # if dirs != []:
            #     for dir in dirs:
            #         apply(os.path.join(name, dir))
            for file in files:
                full_name = os.path.join(name, file)
                apply(full_name)
                # accounted.append(full_name)
    # accounted.sort()
    return None

sfile = '../CC_Statements' # put particular statement here
output = apply(sfile)
# trdf, acctdf = apply(sfile)
