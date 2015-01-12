"""
Enable 'freezing' interpreter state upon exception, and reviewing it post crash.
"""

__author__ = 'Or Weis'

import pickle
import os
import sys
import time
import inspect



QUICK_LOADER = """
import os
import sys
import pickle

sys.path.extend(%s)

data = None
with open(__file__[:-3], "rb") as src:
    data = pickle.load(src)
"""


class Aftermath():

    @staticmethod
    def traceback_iterator(tb):
        current_tb = tb
        while current_tb is not None:
            yield current_tb
            current_tb = current_tb.tb_next

    @staticmethod
    def can_pickle(obj):
        if inspect.isbuiltin(obj) or inspect.ismodule(obj) or\
                inspect.istraceback(obj):
            return False
        elif not inspect.isclass(obj) and obj.__class__ == Ellipsis.__class__:
            return False
        #For now ignore functions for slimness and decorator issues
        elif inspect.isfunction(obj):
            return False
        elif getattr(obj, "__aftermath__", None) == "ignore":
            return False
        else:
            try:
                pickle.dumps(obj)
            except:
                return False
            return True

    @staticmethod
    def extract_stack(tb):
        stack = []
        for trace in Aftermath.traceback_iterator(tb):
            entry = {
                "name": trace.tb_frame.f_code.co_name,
                "globals": {},
                "locals": {},
            }
            # Pickle current trace's globals
            for k, v in trace.tb_frame.f_globals.iteritems():
                if Aftermath.can_pickle(v):
                    entry["globals"][k] = v
            # Pickle current trace's locals
            for k, v in trace.tb_frame.f_locals.iteritems():
                if Aftermath.can_pickle(v):
                    entry["locals"][k] = v
            stack.append(entry)
        return stack

    @staticmethod
    def create_quick_loader(dump_file_path):
        with open(dump_file_path + ".py", "wb") as q:
            q.write(QUICK_LOADER % unicode(sys.path))

    @staticmethod
    def save_stack_to_file(tb, dir_path, name=None):
        stack = Aftermath.extract_stack(tb)
        if name is None:
            name = stack[-1]["name"]
        path = os.path.join(dir_path, name + time.strftime("_%Y_%m_%d_%H_%M_%S") + "_aftermath")
        try:
            os.makedirs(dir_path)
            #Ignore LEAF already exists
        except os.error:
            pass
        with open(path, "wb") as dest:
            pickle.dump(stack, dest)
        Aftermath.create_quick_loader(path)
        return stack


    @staticmethod
    def guard(dir_path):
        def argAftermathwrapper(func):
            def AftermathGuard(*args, **kwargs):
                try:
                   return func(*args, **kwargs)
                except Exception, e:
                    tb = sys.exc_info()[-1]
                    #Save current stack to file
                    Aftermath.save_stack_to_file(tb, dir_path)
                    #Re-raise once done
                    raise
            setattr(AftermathGuard, "__aftermath__", "ignore")
            return AftermathGuard
        return argAftermathwrapper




