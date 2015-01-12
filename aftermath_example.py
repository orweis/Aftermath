__author__ = 'OW'
from aftermath import Aftermath

if __name__ == "__main__":

    def sub_test():
        x = 2
        raise ValueError()

    # Test will create an aftermath file set upon exception,
    #  which will be stored under 'debug' folder
    @Aftermath.guard("debug")
    def test():
        y = 2
        sub_test()


    test()

