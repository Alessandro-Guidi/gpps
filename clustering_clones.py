#!/usr/bin/python
# Compute the tree which maximizes the likehood
import os
import math
import errno
import argparse
from collections import namedtuple
import collections
import numpy as np
import networkx as nx 
from networkx.algorithms import approximation
from matrix_utils import read_matrix_tab

#create graph for rows and return it
def create_graph(n_nodes,dictionary,threshold):
    G = nx.Graph()
    G.add_nodes_from(range(n_nodes))
    [G.add_edge(key[0],key[1], weight = value) for key, value in dictionary.iteritems() if value>threshold]
    return G


#I use the dict, pair clones(them index)and similar probability.
#make tuple
def create_dict_prob_row(matrix,alpha,l_alpha,beta,l_beta): 
    tup_row = namedtuple('Tup',['index','percent'])
    pair_percent =[]
    for index1 in range(len(matrix)-1):
        for index2 in range(index1+1,len(matrix)):
            prob = prob_merging(matrix[index1],matrix[index2],alpha,l_alpha,beta,l_beta)
            pair_percent.append(tup_row((index1,index2),prob))
    d_row = dict(pair_percent)
    return d_row


#I use the dict, pair mutations(them index)and similar probability.
#make tuple
def create_dict_prob_col(matrix,alpha,l_apha,beta,l_beta):
    tup_col = namedtuple('Tup',['index','percent'])
    pair_probability = []
    for index1 in range(len(matrix[0])-1):
        for index2 in range(index1+1,len(matrix[0])):
            prob = prob_merging(matrix[:,index1],matrix[:,index2],alpha,l_apha,beta,l_beta)
            pair_probability.append(tup_col((index1,index2),prob))
    d_col = dict(pair_probability)
    return d_col

#for every pair rows returns likelihood probability
def prob_merging(row1, row2, alpha, l_alpha, beta, l_beta):
    prob = 0
    lenght = len(row1)
    for i in range(lenght):
        if row1[i] == row2[i]:
            if row1[i] == 1:
                prob = prob + ((l_beta)*2+beta*2)
            elif row1[i] == 0:
                prob = prob + ((l_alpha)*2+alpha*2)
        elif (row1[i] != 2) and (row2[i] != 2):
            prob = prob + ((l_beta)+alpha + (l_alpha)+beta)
    return prob

#function support to merge_rows
def merge_set_of_clone(matrix,subgraph,alpha,l_alpha,beta,l_beta):
    if type(subgraph) is not(set):
        nodes = list(subgraph.nodes)
    else:
        nodes = list(subgraph)
    clones = matrix[np.array(nodes)]
    new_clone = []
    for i in range(len(clones[0])):
        col = collections.Counter(clones[:,i])
        prob_all_one = alpha**col[0]*(l_beta)**col[1]
        prob_all_zero = beta**col[1]*(l_alpha)**col[0]
        if prob_all_one >= prob_all_zero:
            new_clone = np.append(new_clone, 1)
        else:
            new_clone = np.append(new_clone, 0)
    set_nodes = set(nodes)
    set_clones = set(range(len(matrix)))
    new_index = list(set_clones-set_nodes)
    matrix = matrix[new_index]
    matrix = np.vstack((matrix,new_clone))     
    return matrix  


#take result to find_all_candidates_to_merge_cc and for each connected component calculate the weight and return the maximum
def find_single_set_to_merge(candidates):
    max_weight = None
    max_SB = None
    candidates = list(candidates)
    for subgraph in candidates:
        if len(list(subgraph.nodes)) > 1:
            weight = 0
            for index1, nbrs in subgraph.adj.items():
                for index2, w in nbrs.items():
                    weight = weight+w['weight']
            if abs(weight)/2 > abs(max_weight):
                max_weight = weight/2
                max_SB = subgraph
    return max_SB


#function that support merge_rows, give a graph and return a potenzial set to merge. Strategy more conservative
def find_all_candidates_to_merge_cl(graph):
    candidate = approximation.clique.max_clique(graph)
    return candidate    
#function that support merge_rows,give a graph and return a potenzial set to merge. Strategy more aggressive
def find_all_candidates_to_merge_cc(graph):
    candidates =  nx.algorithms.components.connected_component_subgraphs(graph)
    return candidates
    
#merge rows with higher likelihood value, behind merge the cicle, after merge the single edge, if there are
def merge_rows(matrix, graph, strategy,alpha,l_alpha,beta,l_beta,threshold,merge_clone):
    candidates = []
    if strategy == 'clique':
        candidate = find_all_candidates_to_merge_cl(graph)
        if len(candidate) == 1:
            candidate = [] 
    elif strategy == 'conncomp':
        candidates = find_all_candidates_to_merge_cc(graph)
        candidate = find_single_set_to_merge(candidates)
        if len(list(candidate.nodes)) == 1:
            candidate = [] 
    if candidate != []:
        set_max = candidate
        merge_clone.append(list(candidate))
        matrix = merge_set_of_clone(matrix,set_max,alpha,l_alpha,beta, l_beta)
        d_row = create_dict_prob_row(matrix,alpha,l_alpha,beta,l_beta)
        G = create_graph(len(matrix),d_row,threshold)
        matrix,merge_clone = merge_rows(matrix, G, strategy, alpha, l_alpha, beta,l_beta, threshold, merge_clone)
        return matrix,merge_clone            
    else:
        return matrix,merge_clone

#function support to merge_cols !!!the miss_value are changed!!!
def merge_set_of_mutation(matrix,subgraph,alpha,l_alpha,beta,l_beta):
    if type(subgraph) is not(set):
        nodes = list(subgraph.nodes)
    else:
        nodes = list(subgraph)
    mutations = matrix[:,nodes]
    new_mutation = []
    for i in range(len(mutations)):
        row = collections.Counter(mutations[i])
        prob_all_one = alpha**row[0]*(l_beta)**row[1]
        prob_all_zero = beta**row[1]*(l_alpha)**row[0]
        if prob_all_one >= prob_all_zero:
            new_mutation = np.append(new_mutation, 1)
        else:
            new_mutation = np.append(new_mutation, 0)
    set_nodes = set(nodes)
    set_mutation = set(range(len(matrix[0])))
    new_index = list(set_mutation-set_nodes)
    matrix = matrix[:,new_index]
    matrix = np.column_stack((matrix,np.array(new_mutation)))
    return matrix


#merge cols with higher likelihood value
def merge_cols(matrix, graph, strategy,alpha,l_alpha,beta,l_beta,threshold,merge_mutation):
    candidates = []
    if strategy == 'clique':
        candidate = find_all_candidates_to_merge_cl(graph)
        if len(candidate) == 1:
            candidate = [] 
    elif strategy == 'conncomp':
        candidates = find_all_candidates_to_merge_cc(graph)
        candidate = find_single_set_to_merge(candidates)
        if len(list(candidate.nodes)) == 1:
            candidate = [] 
    if candidate != []:
        set_max = candidate
        merge_mutation.append(candidate)
        matrix = merge_set_of_mutation(matrix,set_max,alpha,l_alpha,beta,l_beta)
        d_col = create_dict_prob_col(matrix,alpha,l_alpha,beta,l_beta)
        G = create_graph(len(matrix),d_col,threshold)
        matrix,merge_mutation = merge_cols(matrix, G, strategy, alpha,l_alpha, beta,l_beta, threshold, merge_mutation)
        return matrix,merge_mutation
    else:
        return matrix,merge_mutation


#merge clones/rows with many missing value
def remove_clones(matrix,missing_value):
    lenght = len(matrix[0])
    index = []
    for i in range(len(matrix)):
        occurrences = list(matrix[i]).count(2)
        if float(occurrences)/lenght>missing_value:#float(occurrences)/lenght>math.exp(missing_value):
            index.append(i)
    for num in index:		
        matrix = np.delete(matrix, num, 0)
    return matrix

#delete mutation/cols with many missing value or with few value 1
def remove_mutations(matrix, missing_value, few_one):
    lenght = len(matrix[0])
    index = []
    for i in range(lenght):
        occurrences_data_missing = list(matrix[:,i]).count(2)
        occurrences_few_mutation = list(matrix[:,i]).count(1)
        if float(occurrences_data_missing)/len(matrix)>missing_value or float(occurrences_few_mutation)/len(matrix)<few_one:
            index.append(i)
    for num in index[::-1]:
	    matrix = np.delete(matrix, num, 1)
    return matrix

#return if the mutations are independent or dependent with probability
def prob_independent_mutations(col1,col2,alpha,l_alpha,beta,l_beta):
    lenght = len(col1)
    prob_ind = 1
    prob_not_independent = 1
    for i in range(lenght):
        if col1[i] == col2[i]:
            if col1[i] == 1:
                prob_ind = prob_ind * (1-((l_beta)**2))
                prob_not_independent = prob_not_independent * (((l_beta)**2))
            elif col1[i] == 0:
                prob_ind = prob_ind * ((l_alpha)**2)
                prob_not_independent = prob_not_independent * (1-((l_alpha)**2))
        elif (col1[i] != 2) and (col2[i] != 2):
            prob_ind = prob_ind * (1-((l_beta)*alpha))
            prob_not_independent = prob_not_independent * (((l_beta)*alpha))
    return prob_ind, prob_not_independent

#create text to file output mutation
def merge_file_mutation(testo,merge_mutations):
    newFile = testo.split()
    for group in merge_mutations:
        merge = []
        temp = []
        for i in range(len(newFile)):
            if i in group:
                merge.append(newFile[i])
            else:
                temp.append(newFile[i])
        flat = []
        for sublist in merge:
            if sublist is list:
                flat_sub = [val for sublist in merge for val in sublist]
                flat.append(flat_sub) 
            else: 
                flat.append(sublist)
        temp.append(flat)
        newFile = temp
    return newFile

def dict_log(clones,merge_nodes):
    if merge_nodes != []:
        num_clones = clones
        check = []
        d = dict()
        first = merge_nodes.pop(0)
        num_clones = num_clones-len(first)+1
        d[num_clones] = first
        for i in first:
            check.append(i)
        for group in merge_nodes:
            num_clones = num_clones-len(group)+1
            index = []
            group.sort()
            group.reverse()
            for n in group:
                if n in set(d.keys()):
                    value = set(d[n])
                    i = set(index)
                    index = list(value|i)
                    del d[n]
                elif n in check:
                    minor = minor_set(n, check)
                    n = n+minor
                    if n in check:
                        num = next_missing(check, n)
                    else: 
                        num = n
                    check.append(num)
                    check.sort()
                    index.append(num)
                else:
                    minor = minor_set(n, check)
                    check.append(n+minor)
                    check.sort()
                    index.append(n+minor)
            d = update_dict(d, group)
            index.sort()
            d[num_clones-1] = index
        return d
    else:
        return []

def minor_set(index,sets):
    n = 0
    minor = True
    while(minor):
        if n >= len(sets):
            n = n+1
            minor = False
        elif sets[n] < index:  
            n=n+1
        else:
            minor = False
    return n 

def update_dict(d, group):
    keys = d.keys()
    keys.sort()
    for key in keys:
        minor = minor_set(key, group)
        if minor != 0:
            value = d[key]
            del d[key]
            d[key-minor] = value
    return d

def next_missing(sets, n):
    sets.sort()
    index = 0
    miss = True
    n = n+1
    while(miss):
        if n == len(sets):
            index = n
            miss = False
        elif sets[n] != n: 
            index = n
            miss = False
        n=n+1
    return index
        
def write_file_log(outline,dict_clone):
    with open('{0}.log'.format(outline),'w+') as file_out:
        if bool(dict_clone):
            for key, value in dict_clone.iteritems():
                print >> file_out, key, "\t", "\"",value,"\"" 
        else:
            print >> file_out, "nothing merge"

def clustering_clones(pathfile,pathfileMut,output,v_alpha,v_beta,v_threshold,strategy,mv=None,fo=None):
    alpha = math.log(float(v_alpha))
    l_alpha = math.log(1-float(v_alpha))
    beta = math.log(float(v_beta))
    l_beta = math.log(1-float(v_beta))
    threshold = math.log(float(v_threshold))
    if mv is not(None):
        missing_value= math.log(float(mv))
    else:
        missing_value = None
    if fo is not(None):
        fewone = math.log(float(fo))
    else:
        few_one = None
    if strategy == 'clique' or strategy == 'conncomp':
        strategy = strategy
    pathfile_mutation = pathfileMut
    input_matrix = read_matrix_tab(pathfile)
    input_matrix = np.array(input_matrix) #I exploit library NumPy
    
    if missing_value is not(None):
        input_matrix = remove_clones(input_matrix, missing_value)
    if few_one is not(None):
        input_matrix = remove_mutations(input_matrix, missing_value, few_one)
    
    num_clones = len(input_matrix)
    print "(alpha:",alpha,", beta:",beta,")"
    print "(1-alpha:",l_alpha,", 1-beta:",l_beta,")"
    print "trheshold:",threshold
    d_row = create_dict_prob_row(input_matrix,alpha,beta,l_alpha,l_beta)
    G = create_graph(len(input_matrix),d_row,threshold)
    merge_clone = []
    print "CLONE"
    input_matrix,merge_clone = merge_rows(input_matrix, G, strategy, alpha, l_alpha, beta, l_beta, threshold, merge_clone)

    d_col = create_dict_prob_col(input_matrix, alpha, l_alpha, beta, l_beta)
    G = create_graph(len(input_matrix[0]),d_col,threshold)
    merge_mutation = []
    print "MUTATION"
    input_matrix,merge_mutation = merge_cols(input_matrix, G, strategy,alpha, l_alpha, beta, l_beta, threshold,merge_mutation)

    import os
    try:
        os.makedirs(output)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(output):
            pass
        else:
            raise

    filename = os.path.splitext(os.path.basename(pathfile))[0]
    outfile = os.path.join(output, filename)

    with open(pathfile_mutation, 'r') as file_mut:
        testo = file_mut.read()

    file_mutation = merge_file_mutation(testo,merge_mutation)

    with open('{0}_mutation.out'.format(outfile),'w+') as file_mut_out:
        for item in file_mutation:
            print >> file_mut_out, item

    np.savetxt('{0}_matrix.out'.format(outfile), input_matrix , fmt = '%d', delimiter=' ',newline='\n')
    dict_clone_log = dict_log(num_clones, merge_clone)
    write_file_log(outfile,dict_clone_log)