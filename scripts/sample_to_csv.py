#!/usr/local/bin/python3
import sys
import pickle

def convert_pickle_to_csv(input,output):
    f = open(input,"rb")
    o = open(output,"w")
    data = pickle.load(f)
    o.write("Wavelengths,Intensities\n")
    for i in range(0,len(data[0])):
        o.write(str(data[0][i]) + "," + str(data[1][i]) + "\n")
    o.close()
    f.close()

if len(sys.argv) == 2:
    print("Converting file: " + sys.argv[1])
    outname = input("Output filename: ")
    convert_pickle_to_csv(sys.argv[1],outname)

elif len(sys.argv) == 3:
    print("Converting file: " + sys.argv[1] + ", output as: " + sys.argv[2])
    convert_pickle_to_csv(sys.argv[1],sys.argv[2])
