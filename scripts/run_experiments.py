################################################################################
 # Copyright (c) 2017 Dan Iorga, Tyler Sorenson, Alastair Donaldson

 # Permission is hereby granted, free of charge, to any person obtaining a copy
 # of this software and associated documentation files (the "Software"), to deal
 # in the Software without restriction, including without limitation the rights
 # to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 # copies of the Software, and to permit persons to whom the Software is
 # furnished to do so, subject to the following conditions:

 # The above copyright notice and this permission notice shall be included in all
 #copies or substantial portions of the Software.

 # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 # FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 # OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 # SOFTWARE.
################################################################################

"""@package python_scripts
A python script that reads and runs the experiments described in the JSON file
"""

import json
import sys
import numpy as np
import time
import os
from copy import deepcopy
import itertools

from run_sut_stress import SutStress


class Experiment(object):
    """A class used to run batch experiments
    Reads and runs the experiments described in the JSON file
    """
    _TEMP_FOLDER_PREFIX ="./temp_"

    def __init__(self):
        """
        Create an experiment object
        """
        self._sut = []
        self._stress = []
        self._mapping = None
        self._ranked_list = None
        self._cores = []
        self._iterations = None
        self._temp = None
        self._max_temperature = None
        self._cooldown_time = None
        self._folder_name = self._TEMP_FOLDER_PREFIX + time.strftime("%H%M%S") + "/"

    def read_json_object(self, json_object):
        """
        Sets the experiment data based on the JSON object
        :param json_object: The JSON object
        """

        self._sut = []
        self._stress = []
        self._cores = []

        # You can have a list for sut, stress and cores or a single object
        try:
            data = json_object['sut']
            if isinstance(data, str):
                self._sut.append(json_object["sut"])
            elif isinstance(data, list):
                self._sut.extend(json_object["sut"])
            else:
                raise KeyError
        except KeyError:
            print("Error processing sut filed in JSON")

        if "stress" in json_object:
            data = json_object['stress']
            if isinstance(data, str):
                self._stress.append(json_object["stress"])
            elif isinstance(data, list):
                self._stress.extend(json_object["stress"])
            else:
                raise KeyError
        elif "mapping" in json_object:
            self._mapping = json_object['mapping']
        elif "ranked_list" in json_object:
            self._ranked_list = json_object['ranked_list']
        else:
            raise ValueError("No stress or mapping given")

        try:
            data = json_object['cores']
            if isinstance(data, int):
                self._cores.append(json_object["cores"])
            elif isinstance(data, list):
                self._cores.extend(json_object["cores"])
            else:
                raise KeyError
        except KeyError:
            print("Error processing cores in JSON")

        # You can not have a list for iterations, temperature, cooldown_time
        try:
            self._iterations = int(json_object["iterations"])
        except KeyError:
            print("Unable to find iterations in JSON")

        try:
            self._max_temperature = int(json_object["max_temperature"])
        except KeyError:
            print("Unable to find max_temperature in JSON")

    # Deprecated
    def run_config(self, experiment, config, sut, stress, cores):
        """
        Run a config experiment only once
        :param experiment: Experiment name, only for display purpouses
        :param config: Configuration name, only for display purpouses
        :param sut: System under stress
        :param stress: Enemy process
        :param cores: Number of enemy cores
        :return: (time_list, temp_list) A tuple with the lists of time and temp
        """
        time_list =[]
        temp_list = []

        for it in range(self._iterations):
            # cool_down(self._max_temperature)
            s = SutStress()
            print("\nStarting " + str(experiment) +", " + \
                  str(config) +                           \
                  ", iteration " + str(it) + " with:")
            print("SUT:\t\t" + sut + "\n" + \
                  "Stress:\t\t" + stress + "\n" + \
                  "Cores:\t\t" + str(cores) + "\n")
            ex_time, ex_temp = s.run_sut_stress(sut, stress, cores, 0)

            time_list.append(ex_time)
            temp_list.append(ex_temp)

        return time_list, temp_list

    def _merge_dict(self, dict1, dict2):
        """
        Recursively merge two dictionaries
        :param dict1: First dict to merge
        :param dict2: Second dict to merge
        :return: Merged dict
        """
        if isinstance(dict1, dict) and isinstance(dict2, dict):
            dict1_and_dict2 = set(dict1).intersection(dict2)
            every_key = set(dict1).union(dict2)
            return dict((k, self._merge_dict(dict1[k], dict2[k]) if k in dict1_and_dict2 else
                deepcopy(dict1[k] if k in dict1 else dict2[k])) for k in every_key)
        return deepcopy(dict2)

    def merge_docs(self, output_file):
        """
        Merge the separate output files in a single one
        :param output_file: The JSON file where the experiment results are stored
        """
        output = dict()
        config_files = [f for f in os.listdir(self._folder_name) if os.path.isfile(os.path.join(self._folder_name, f))]

        for file in config_files:
            with open(self._folder_name + file) as data_file:
                experiments_object = json.load(data_file)
                output = self._merge_dict(output, experiments_object)

        with open(output_file, 'w') as outfile:
            json.dump(output, outfile, sort_keys=True, indent=4)

    def _cleanup(self):
        """
        Remove temp files and temp dir
        """

        config_files = [f for f in os.listdir(self._folder_name) if os.path.isfile(os.path.join(self._folder_name, f))]

        for file in config_files:
            os.remove(self._folder_name + file)

        os.rmdir(self._folder_name)

    def _log_data(self, sut, stress, cores, time_list, temp_list = None, suffix=""):
        """
        Stores the time list, temp list, average time, average temp and std time and std temp
        in a dictionary
        :param sut: System under stress
        :param stress: Enemy process
        :param cores: Number of enemy cores
        :param time_list: A list with all the execution times
        :param temp_list: A list with all the temperatures
        :param suffix: Suffix tha cna be added to all keys
        :return: A dictionary with all the data
        """
        data = dict()

        data['sut'] = sut
        data['stress'] = stress
        data['cores'] = cores
        data['iterations'] = self._iterations

        data['time_list'+ suffix] = time_list
        time_array = np.asarray(time_list)
        data['time_avg' + suffix] = time_array.mean()
        data['time_std' + suffix] = time_array.std()

        if temp_list:
            data['temp_list' + suffix] = temp_list
            temp_array = np.asarray(temp_list)
            data['temp_avg' + suffix] = temp_array.mean()
            data['temp_std' + suffix] = temp_array.std()

        return data

    def _log_data2(self, sut, stress, cores, time_list_baseline, time_list_enemy,
                   temp_list_baseline=None, temp_list_enemy=None):
        """
        Stores the time list, temp list, average time, average temp and std time and std temp
        in a dictionary
        :param sut: System under stress
        :param stress: Enemy process
        :param cores: Number of enemy cores
        :param time_list_baseline: A list with all the execution times
        :param time_list_enemy: A list with all the execution times
        :return: A dictionary with all the data
        """
        data = dict()

        data['sut'] = sut
        data['stress'] = stress
        data['cores'] = cores
        data['iterations'] = self._iterations

        data['time_list_baseline'] = time_list_baseline
        time_array = np.asarray(time_list_baseline)
        data['time_list_baseline_avg'] = time_array.mean()
        data['time_list_baseline_std'] = time_array.std()

        if temp_list_baseline:
            data['temp_list_baseline'] = temp_list_baseline
            temp_array = np.asarray(temp_list_baseline)
            data['temp_list_baseline_avg'] = temp_array.mean()
            data['temp_list_baseline_std'] = temp_array.std()

        data['time_list_enemy'] = time_list_enemy
        time_array = np.asarray(time_list_enemy)
        data['time_list_enemy_avg'] = time_array.mean()
        data['time_list_enemy_std'] = time_array.std()

        if temp_list_enemy:
            data['temp_list_enemy'] = temp_list_enemy
            temp_array = np.asarray(temp_list_enemy)
            data['temp_list_enemy_avg'] = temp_array.mean()
            data['temp_list_enemy_std'] = temp_array.std()

        return data

    def _log_data3(self, sut, stress, cores, time_list_baseline, dict_mappings):
        """
        Stores the time list, temp list, average time, average temp and std time and std temp
        in a dictionary
        :param sut: System under stress
        :param stress: Enemy process
        :param cores: Number of enemy cores
        :param time_list_baseline: A list with all the execution times
        :param dict_mappings: Dict with enemies and averages
        :return: A dictionary with all the data
        """
        data = dict()

        data['sut'] = sut
        data['stress'] = stress
        data['cores'] = cores
        data['iterations'] = self._iterations

        time_array = np.asarray(time_list_baseline)
        data['time_list_baseline_avg'] = time_array.mean()

        sorted_by_value = sorted(dict_mappings.items(), key=lambda kv: kv[1])
        data['ranked_list'] = sorted_by_value



        return data

    def run(self, input_file, output_file):
        """
        Run the configured experiment
        :param input_file: The JSON file where the experiments are defined
        :param output_file: The JSON file where the experiment results are stored
        """

        #Create a folder for the temp files
        if not os.path.exists(self._folder_name):
            os.makedirs(self._folder_name)

        # Read the configuration in the JSON file
        with open(input_file) as data_file:
            experiments_object = json.load(data_file)
        output = dict()

        for experiment in experiments_object:
            output[experiment] = dict()
            self.read_json_object(experiments_object[experiment])

            if self._mapping:
                s = SutStress()

                (time_list_baseline, temp_list_baseline) = s.run_mapping(sut=self._sut[0],
                                                                         mapping=dict(),
                                                                         iterations=self._iterations,
                                                                         max_temperature=self._max_temperature)

                (time_list_enemy, temp_list_enemy) = s.run_mapping(sut=self._sut[0],
                                                                   mapping=self._mapping,
                                                                   iterations=self._iterations,
                                                                   max_temperature=self._max_temperature)
                output[experiment] = self._log_data2(self._sut,
                                        str(self._mapping),
                                        self._cores,
                                        time_list_baseline,
                                        time_list_enemy,
                                        temp_list_baseline,
                                        temp_list_enemy
                                        )

                config_out_file = self._folder_name + experiment + ".json"

                with open(config_out_file, 'w') as outfile:
                    json.dump(output, outfile, sort_keys=True, indent=4)

                output.pop(experiment)
            elif self._stress:

                gen = ((sut, stress, cores) for sut in self._sut
                                        for stress in self._stress
                                        for cores in self._cores)
                config = 1

                for sut, stress, cores in gen:

                    # Log test conditions
                    config_str = "config_" + str(config)

                    # Run baseline with zero enemies and store results
                    (time_list , temp_list ) = self.run_config(experiment,
                                                           "baseline",
                                                           sut,
                                                           stress,
                                                           0)
                    output[experiment][config_str] = self._log_data(sut,
                                                                stress,
                                                                cores,
                                                                time_list,
                                                                temp_list,
                                                                "_baseline")

                    # Run actual config and store results
                    (time_list , temp_list ) = self.run_config(experiment,
                                                           config_str,
                                                           sut,
                                                           stress,
                                                           cores)

                    output[experiment][config_str].update(self._log_data(sut,
                                                                stress,
                                                                cores,
                                                                time_list,
                                                                temp_list)
                                                      )

                    config_out_file = self._folder_name + experiment + "_" + \
                        config_str + ".json"

                    with open(config_out_file, 'w') as outfile:
                        json.dump(output, outfile, sort_keys=True, indent=4)
                    output[experiment].pop(config_str)

                    config = config + 1
                output.pop(experiment)

            elif self._ranked_list:
                s = SutStress()

                (time_list_baseline, _) = s.run_mapping(sut=self._sut[0],
                                                        mapping=dict(),
                                                        iterations=self._iterations,
                                                        max_temperature=self._max_temperature)

                results = dict()
                c = [p for p in itertools.product(self._ranked_list, repeat=self._cores[0])]
                conf_mapping = dict()
                for conf in c:
                    for core in range(1, self._cores + 1):
                        conf_mapping[core] = conf[core - 1]

                    (time_list_enemy, _) = s.run_mapping(sut=self._sut[0],
                                                         mapping=conf_mapping,
                                                         iterations=self._iterations,
                                                         max_temperature=self._max_temperature)

                    results[conf_mapping] = np.asarray(time_list_enemy).mean()

                output[experiment] = self._log_data3(self._sut,
                                        str(self._ranked_list),
                                        self._cores,
                                        time_list_baseline,
                                        results,
                                        )
                config_out_file = self._folder_name + experiment + ".json"

                with open(config_out_file, 'w') as outfile:
                    json.dump(output, outfile, sort_keys=True, indent=4)

                output.pop(experiment)

        self.merge_docs(output_file)
        self._cleanup()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: " + sys.argv[0] + " <experments_file>.json  <results>.json \n")
        exit(1)

    exp = Experiment()

    exp.run(sys.argv[1], sys.argv[2])
