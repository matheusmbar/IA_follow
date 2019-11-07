#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov  1 15:21:17 2019

@author: matheus
"""

import numpy as np
from random import randrange, shuffle, gauss

#https://towardsdatascience.com/continuous-genetic-algorithm-from-scratch-with-python-ff29deedd099
#https://towardsdatascience.com/genetic-algorithm-implementation-in-python-5ab67bb124a6

class Genetic ():
    def __init__(self, results):
        self.indiv = len(results)
        self.results = sorted(results, key=lambda r: r["fitness"],reverse=True)
    
    def evolve(self, keep_percent=0.5):
        keep_indiv = int(self.indiv * keep_percent)
        create_indiv = self.indiv - keep_indiv
        parents = self.results[:keep_indiv]
        
        parents_indexes = list(range(keep_indiv)) * int(np.ceil(create_indiv/keep_indiv) + 1)
        shuffle(parents_indexes)

        sons = list()
        for i in range(int(np.ceil(create_indiv/2))):
            p_1 = parents_indexes[i*2]
            p_2 = parents_indexes[i*2+1]
            out_1, out_2 = self.cross_pair(parents[p_1], parents[p_2])
#            out_1, out_2 = self.cross_pair(parents[0], parents[1])  # comment this line

            sons.append(out_1)
            sons.append(out_2)
            
        mutation_start = int(keep_indiv * 0.4)
                
        parents_to_mutate = list()
        for i, p in enumerate(parents[:self.indiv - mutation_start]): 
            parents_to_mutate.append(dict(p))
        
        all_gains = parents[:mutation_start] + parents_to_mutate + sons

        for g in all_gains[mutation_start:]:
            g["gains"] = self.mutate(g["gains"],mutation_rate=0.4,stdev=2)
            g["id"] = "{}_x".format(g["id"])
            
#        print ("\nAfter evolve")
#        for i, a in enumerate(all_gains[:5]):
#            print ("{} {} {}".format(i, a.get("fitness"), a.get("id")))
        
        return all_gains[:self.indiv]
    
    @staticmethod
    def mutate (gains, mutation_rate=0.1, stdev=1):
        gains_len = len(gains)
        gains_to_mutate = int(gains_len * mutation_rate) 
        
        indexes = list(range(gains_len))
        shuffle(indexes)
        
        new_gains = list(gains)
    
        mutate_types = ['reset', 'gauss']
        for i in indexes[:gains_to_mutate]:
            mutate_type = mutate_types[randrange(len(mutate_types))]
            if mutate_type == 'reset':
                new_gains[i] = np.random.rand() *stdev - stdev/2
            elif mutate_type == 'gauss':
                new_gains[i] = gauss(gains[i], stdev)

        return new_gains           

    @staticmethod
    def cross_pair (indiv_1, indiv_2, max_cross_percent=0.3):        
        in_1 = indiv_1["gains"]
        in_2 = indiv_2["gains"]
        id_1 = indiv_1.get("id")
        id_2 = indiv_2.get("id")
        gains_len = len(in_1)
        max_cross_len = int(max_cross_percent * gains_len)
        split_start = randrange(0, gains_len - 2)
        split_end = randrange(split_start + 1, gains_len-1)
        
        split_end = min(split_end, split_start + max_cross_len)
        
#        print ("Crossing between {} and {}".format(split_start, split_end))
                
        gains_1 = in_1[:split_start] + in_2[split_start:split_end] + in_1[split_end:]
        gains_2 = in_2[:split_start] + in_1[split_start:split_end] + in_2[split_end:]
        out_1 = {"gains":gains_1, "id":"{}_{}".format(id_1, id_2)}
        out_2 = {"gains":gains_2, "id":"{}_{}".format(id_2, id_1)}
        return out_1, out_2
