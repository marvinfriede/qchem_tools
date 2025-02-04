#!/usr/bin/env python3
# coding: utf-8

import os
import sys
import glob
import argparse


def main():
  args = init_argparser()

  # init lists
  data = []
  failed = []

  # get all files
  filelist = getFileList()
  print(f"Going to check {len(filelist)} files...")

  for i, filename in enumerate(filelist):
    rem = False
    rem_dict = {}
    count_criter = 0
    num_jobs = 1

    with open(filename, errors='ignore') as f:
      for line in f:

        # only entered if previous line was start of rem block
        if rem is True:
          # turn false again if end encountered, otherwise do stuff
          if line.startswith("$end"):
            rem = False
          else:
            rem_dict[line.strip().split()[0]] = line.strip().split()[1]

        # turns true if rem block is hit
        if line.startswith("$rem"):
          rem = True
          continue

        # get number of jobs in multijob file
        if line.startswith("User input:") and "of" in line:
          num_jobs = int(line.strip().split()[-1])
          continue

        if "Convergence criterion met" in line:
          count_criter += 1
          continue

        if "shells" in line and "basis functions" in line:
          nbas = line.split("shells and")[1].split("basis functions")[0].strip()
          continue

        if line.startswith(" SCF time:   CPU"):
          walltime = line.split("wall")[1].strip()
          walltime = walltime[:-1]
          continue

        # append data in line furthest down
        if " Total energy in the final basis set =" in line:
          energy = line.split("=")[1].strip()

          # THIS IS A HOT FIX!!
          # first job has no scf guess -> first list shorter
          if "scf_guess" not in rem_dict:
            rem_dict["scf_guess"] = "default"

          # append everything and stop going through file
          data.append([filename, energy, nbas, walltime] +
                      list(rem_dict.values()))
          continue

      # check convergence for my multijob
      if count_criter != num_jobs:
        failed.append(filename)

    progress(i+1, len(filelist))

  print("\nFinished!\n")
  if len(failed) == 0:
    print("All jobs successful!!")
  else:
    print("WARNING!!! Convergence not reached in:")
    for i in failed:
      print(i)

  ########################################
  ## data collection (outside of loop!) ##
  ########################################

  cols = ["filename", "energy", "nbas", "time"] + list(rem_dict.keys())

  try:
    import pandas as pd

    df = pd.DataFrame(columns=cols, data=data)

    # print to console
    if args.verbose is not None:
      if args.verbose == 0:
        pd.set_option('display.max_rows', df.shape[0] + 1)
        print(df)
      else:
        print(df.head(args.verbose))
    else:
      print(df)

    # save
    if args.save:
      save_loc = os.path.join(os.path.realpath("."), args.save)
      df.to_csv(save_loc, index=False)
      print("\nSaved data to {}.".format(save_loc))

  except ModuleNotFoundError:
    # fallback: using numpy for saving data to csv
    try:
      import numpy as np

      # add col names to list
      data.insert(0, cols)

      # print to console
      print("")
      if args.verbose is not None:
        if args.verbose != 0:
          data = data[:(args.verbose + 1)]
        print('\n'.join(' '.join(str(x) for x in row) for row in data))
      else:
        print('\n'.join(' '.join(str(x) for x in row) for row in data[:10]))

      # save
      if args.save:
        save_loc = os.path.join(os.path.realpath("."), args.save)
        np.savetxt(save_loc, data, fmt='%s', delimiter="\t")
        print("\nSaved data to {}.".format(save_loc))

    except ModuleNotFoundError:
      print("Modules 'pandas' and 'numpy' not found. Data will not be saved.")


def init_argparser():
  parser = argparse.ArgumentParser(
      description='Q-CHEM JOB INFO\nSearch recursively for all .out files and get general info.')
  parser.add_argument("-v", '--verbose', nargs='?', const=0, type=int,
                      help="Print more. Number of rows optional. 0 prints everything")
  parser.add_argument("-s", "--save", nargs='?', const="data.csv", type=str,
                      help="Save output. Name is optional. Defaults to 'data.csv'.")
  return parser.parse_args()


def getFileList():
  filelist = []
  for file in glob.glob('./**/job.out', recursive=True):
    filelist.append(file)

  if len(filelist) == 0:
    sys.exit("No '.out' files found.")

  return filelist


def progress(count, total, status=''):
  bar_len = 60
  filled_len = int(round(bar_len * count / float(total)))

  percents = round(100.0 * count / float(total), 1)
  bar = '=' * filled_len + '-' * (bar_len - filled_len)

  sys.stdout.write('[%s] %s%s %s\r' % (bar, percents, '%', status))
  sys.stdout.flush()


if __name__ == '__main__':
  main()
