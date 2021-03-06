#!/usr/bin/env python
#===================================================================================
#title           : em_inside_outside_algorithm.py                                  =
#description     : EM Algorithm                                                    =
#author          : Shashi Narayan, shashi.narayan(at){ed.ac.uk,loria.fr,gmail.com})=                                    
#date            : Created in 2014, Later revised in April 2016.                   =
#version         : 0.1                                                             =
#===================================================================================


import function_select_methods

class EM_InsideOutside_Optimiser:
    def __init__(self, smt_sentence_pairs, probability_tables, count_tables, METHOD_FEATURE_EXTRACT):
        self.smt_sentence_pairs = smt_sentence_pairs
        self.probability_tables = probability_tables
        self.count_tables = count_tables
        self.METHOD_FEATURE_EXTRACT = METHOD_FEATURE_EXTRACT

        self.method_feature_extract = function_select_methods.select_feature_extract_method(self.METHOD_FEATURE_EXTRACT)

    def initialize_probabilitytable_smt_input(self, sentid, main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph):
        #print sentid

        # Process all oper nodes
        for oper_node in training_graph.oper_nodes:
            oper_type = training_graph.get_opernode_type(oper_node)
            if oper_type not in self.probability_tables:
                self.probability_tables[oper_type] = {}
            if oper_type not in self.count_tables:
                self.count_tables[oper_type] = {}

            parent_major_node = training_graph.find_parent_of_opernode(oper_node)
            children_major_nodes = training_graph.find_children_of_opernode(oper_node)

            if oper_type == "split":
                # Parent main sentence
                parent_nodeset = training_graph.get_majornode_nodeset(parent_major_node)
                parent_filtered_mod_pos = training_graph.get_majornode_filtered_postions(parent_major_node)
                parent_sentence = boxer_graph.extract_main_sentence(parent_nodeset, main_sent_dict, parent_filtered_mod_pos)

                # Children sentences
                children_sentences = []
                for child_major_node in children_major_nodes:
                    child_nodeset = training_graph.get_majornode_nodeset(child_major_node)
                    child_filtered_mod_pos = training_graph.get_majornode_filtered_postions(child_major_node)
                    child_sentence = boxer_graph.extract_main_sentence(child_nodeset, main_sent_dict, child_filtered_mod_pos)
                    children_sentences.append(child_sentence)

                split_candidate = training_graph.get_opernode_oper_candidate(oper_node)
                
                #print split_candidate

                if split_candidate != None:
                    split_feature = self.method_feature_extract.get_split_feature(split_candidate, parent_sentence, children_sentences, boxer_graph)
                    if split_feature not in self.probability_tables["split"]:
                        self.probability_tables["split"][split_feature] = {"true":0.5, "false":0.5}
                    if split_feature not in self.count_tables["split"]:
                        self.count_tables["split"][split_feature] = {"true":0, "false":0}
                else:
                    not_applied_cands = training_graph.get_opernode_failed_oper_candidates(oper_node)
                    #print not_applied_cands
                    for split_candidate_left in not_applied_cands:
                        split_feature_left = self.method_feature_extract.get_split_feature(split_candidate_left, parent_sentence, children_sentences, boxer_graph)
                        #print split_feature_left
                        if split_feature_left not in self.probability_tables["split"]:
                            self.probability_tables["split"][split_feature_left] = {"true":0.5, "false":0.5}
                        if split_feature_left not in self.count_tables["split"]:
                            self.count_tables["split"][split_feature_left] = {"true":0, "false":0}
                #print self.probability_tables["split"]

            if oper_type == "drop-rel":
                rel_node = training_graph.get_opernode_oper_candidate(oper_node)
                parent_nodeset = training_graph.get_majornode_nodeset(parent_major_node)
                drop_rel_feature = self.method_feature_extract.get_drop_rel_feature(rel_node, parent_nodeset, main_sent_dict, boxer_graph)
                if drop_rel_feature not in self.probability_tables["drop-rel"]:
                    self.probability_tables["drop-rel"][drop_rel_feature] = {"true":0.5, "false":0.5}
                if drop_rel_feature not in self.count_tables["drop-rel"]:
                    self.count_tables["drop-rel"][drop_rel_feature] = {"true":0, "false":0}
                    
            if oper_type == "drop-mod":
                mod_cand = training_graph.get_opernode_oper_candidate(oper_node)
                drop_mod_feature = self.method_feature_extract.get_drop_mod_feature(mod_cand, main_sent_dict, boxer_graph)
                if drop_mod_feature not in self.probability_tables["drop-mod"]:
                    self.probability_tables["drop-mod"][drop_mod_feature] = {"true":0.5, "false":0.5}
                if drop_mod_feature not in self.count_tables["drop-mod"]:
                    self.count_tables["drop-mod"][drop_mod_feature] = {"true":0, "false":0}

            if oper_type == "drop-ood":
                ood_node = training_graph.get_opernode_oper_candidate(oper_node)
                parent_nodeset = training_graph.get_majornode_nodeset(parent_major_node)
                drop_ood_feature = self.method_feature_extract.get_drop_ood_feature(ood_node, parent_nodeset, main_sent_dict, boxer_graph)
                if drop_ood_feature not in self.probability_tables["drop-ood"]:
                    self.probability_tables["drop-ood"][drop_ood_feature] = {"true":0.5, "false":0.5}
                if drop_ood_feature not in self.count_tables["drop-ood"]:
                    self.count_tables["drop-ood"][drop_ood_feature] = {"true":0, "false":0}

        #print self.probability_tables["split"]['as-as-patient_eq-eq_1']
        # if int(sentid) <= 3:
        #     print self.probability_tables["split"]

        # Extract all sentence pairs for SMT from all "fin" major nodes
        self.smt_sentence_pairs[sentid] = training_graph.get_final_sentences(main_sentence, main_sent_dict, boxer_graph)

    def reset_count_table(self):
        for oper_type in self.count_tables: # split, drop-rel, drop-mod, drop-ood
            for oper_feature_key in self.count_tables[oper_type]: # feature patterns
                for val in self.count_tables[oper_type][oper_feature_key]: # true, false
                    self.count_tables[oper_type][oper_feature_key][val] = 0

    def iterate_over_probabilitytable(self, sentid, main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph):
        #print sentid
        # Calculating beta-probability, inside probability
        #print "Calculating beta-probabilities (Inside probability) ..."
        bottom_nodes = training_graph.find_all_fin_majornode()
        beta_prob = self.calculate_inside_probability({}, bottom_nodes, main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph)
        #print beta_prob

        # Calculating alpha-probability, outside probability
        #print "Calculating alpha-probabilities (Outside probability) ..."
        root_node = "MN-1"
        alpha_prob = self.calculate_outside_probability({}, [root_node], main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph, beta_prob)
        #print alpha_prob
        
        # Updating counts for each operation happened in this sentence
        #print "Updating counts of each operation happened in this training sentence ..."
        self.update_count_for_operations(sentid, main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph, alpha_prob, beta_prob)

    def calculate_outside_probability(self, alpha_prob, tgnodes_to_process, main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph, beta_prob):
        if len(tgnodes_to_process) == 0:
            return alpha_prob
        
        tgnode = tgnodes_to_process[0]
        if tgnode.startswith("MN"):
            # Major Nodes
            if tgnode == "MN-1":
                # Root major node
                alpha_prob[tgnode] = 1
            else:
                parents_oper_nodes = training_graph.find_parents_of_majornode(tgnode)
                alpha_prob_tgnode = 0
                for parent_oper_node in parents_oper_nodes:
                    alpha_prob_parent_oper_node = alpha_prob[parent_oper_node]
                    children_major_nodes = training_graph.find_children_of_opernode(parent_oper_node)
                    beta_prod_product = 1
                    for child_major_node in children_major_nodes:
                        if child_major_node != tgnode:
                            beta_prod_product = beta_prod_product * beta_prob[child_major_node]
                    alpha_prob_tgnode += alpha_prob_parent_oper_node * beta_prod_product
                alpha_prob[tgnode] = alpha_prob_tgnode

            # Adding children to tgnodes_to_process
            children_oper_nodes = training_graph.find_children_of_majornode(tgnode)
            for child_oper_node in children_oper_nodes:
                # Check its not already inserted
                if (child_oper_node not in alpha_prob) and (child_oper_node not in tgnodes_to_process):
                    # Check its parent is already inserted
                    parent_major_node = training_graph.find_parent_of_opernode(child_oper_node)
                    if (parent_major_node in alpha_prob) or (parent_major_node in tgnodes_to_process):
                        tgnodes_to_process.append(child_oper_node)
        else:
            # Oper nodes
            parent_major_node = training_graph.find_parent_of_opernode(tgnode)
            alpha_prob_tgnode = alpha_prob[parent_major_node] * self.fetch_probability(tgnode, main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph)
            alpha_prob[tgnode] = alpha_prob_tgnode 
            
            # Adding children to tgnodes_to_process
            children_major_nodes = training_graph.find_children_of_opernode(tgnode)
            for child_major_node in children_major_nodes:
                # Check its not already inserted
                if (child_major_node not in alpha_prob) and (child_major_node not in tgnodes_to_process):
                    # Check all its parents are already inserted
                    parents_oper_nodes = training_graph.find_parents_of_majornode(child_major_node)
                    flag = True
                    for parent_oper_node in parents_oper_nodes:
                        if (parent_oper_node not in alpha_prob) and (parent_oper_node not in tgnodes_to_process):
                            flag = False
                            break
                    if flag == True:
                        tgnodes_to_process.append(child_major_node)
        
        alpha_prob = self.calculate_outside_probability(alpha_prob, tgnodes_to_process[1:], main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph, beta_prob)
        return alpha_prob
        
    def calculate_inside_probability(self, beta_prob, tgnodes_to_process, main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph):
        if len(tgnodes_to_process) == 0:
            return beta_prob

        tgnode = tgnodes_to_process[0]
        if tgnode.startswith("MN"):
            # Major nodes
            major_node_type = training_graph.get_majornode_type(tgnode)
            if major_node_type == "fin":
                # Leaf major nodes
                beta_prob[tgnode] = 1
            else:
                children_oper_nodes = training_graph.find_children_of_majornode(tgnode)
                beta_prob_tgnode = 0
                for child_oper_node in children_oper_nodes:
                    beta_prob_tgnode += self.fetch_probability(child_oper_node, main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph) * beta_prob[child_oper_node]
                beta_prob[tgnode] = beta_prob_tgnode

            # Adding parents to tgnodes_to_process
            parents_oper_nodes = training_graph.find_parents_of_majornode(tgnode)
            for parent_oper_node in parents_oper_nodes:
                # Check its not already inserted
                if (parent_oper_node not in beta_prob) and (parent_oper_node not in tgnodes_to_process):
                    # Check all its chilren are already inserted
                    children_major_nodes = training_graph.find_children_of_opernode(parent_oper_node)
                    flag = True
                    for child_major_node in children_major_nodes:
                        if (child_major_node not in beta_prob) and (child_major_node not in tgnodes_to_process):
                            flag = False
                            break
                    if flag == True:
                        tgnodes_to_process.append(parent_oper_node)
        else:
            # Oper nodes
            children_major_nodes = training_graph.find_children_of_opernode(tgnode)
            beta_prob_tgnode = 1
            for child_major_node in children_major_nodes:
                beta_prob_tgnode = beta_prob_tgnode * beta_prob[child_major_node]
            beta_prob[tgnode] = beta_prob_tgnode

            # Adding parent to tgnodes_to_process
            parent_major_node = training_graph.find_parent_of_opernode(tgnode)
            # Check its not already inserted
            if (parent_major_node not in beta_prob) and (parent_major_node not in tgnodes_to_process):
                # Check all its chilren are already inserted
                children_oper_nodes = training_graph.find_children_of_majornode(parent_major_node)
                flag = True
                for child_oper_node in children_oper_nodes:
                    if (child_oper_node not in beta_prob) and (child_oper_node not in tgnodes_to_process):
                        flag = False
                        break
                if flag == True:
                    tgnodes_to_process.append(parent_major_node)

        beta_prob = self.calculate_inside_probability(beta_prob, tgnodes_to_process[1:], main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph)
        return beta_prob

    def fetch_probability(self, oper_node, main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph):
        oper_node_type = training_graph.get_opernode_type(oper_node)
        if oper_node_type == "split":
            # Parent main sentence
            parent_major_node = training_graph.find_parent_of_opernode(oper_node)
            parent_nodeset = training_graph.get_majornode_nodeset(parent_major_node)
            parent_filtered_mod_pos = training_graph.get_majornode_filtered_postions(parent_major_node)
            parent_sentence = boxer_graph.extract_main_sentence(parent_nodeset, main_sent_dict, parent_filtered_mod_pos)

            # Children sentences
            children_major_nodes = training_graph.find_children_of_opernode(oper_node)
            children_sentences = []
            for child_major_node in children_major_nodes:
                child_nodeset = training_graph.get_majornode_nodeset(child_major_node)
                child_filtered_mod_pos = training_graph.get_majornode_filtered_postions(child_major_node)
                child_sentence = boxer_graph.extract_main_sentence(child_nodeset, main_sent_dict, child_filtered_mod_pos)
                children_sentences.append(child_sentence)

            total_probability = 1
            split_candidate = training_graph.get_opernode_oper_candidate(oper_node)
            if split_candidate != None:
                split_feature = self.method_feature_extract.get_split_feature(split_candidate, parent_sentence, children_sentences, boxer_graph)
                total_probability = self.probability_tables["split"][split_feature]["true"]
                return total_probability
            else:
                not_applied_cands = training_graph.get_opernode_failed_oper_candidates(oper_node)
                for split_candidate_left in not_applied_cands:
                    split_feature_left = self.method_feature_extract.get_split_feature(split_candidate_left, parent_sentence, children_sentences, boxer_graph)
                    total_probability = total_probability * self.probability_tables["split"][split_feature_left]["false"]
                return total_probability
                
        elif oper_node_type == "drop-rel":
            parent_major_node = training_graph.find_parent_of_opernode(oper_node)
            parent_nodeset = training_graph.get_majornode_nodeset(parent_major_node)
            rel_candidate = training_graph.get_opernode_oper_candidate(oper_node)
            drop_rel_feature = self.method_feature_extract.get_drop_rel_feature(rel_candidate, parent_nodeset, main_sent_dict, boxer_graph)
            isDropped = training_graph.get_opernode_drop_result(oper_node)
            prob_value = 0
            if isDropped == "True":
                prob_value = self.probability_tables["drop-rel"][drop_rel_feature]["true"]
            else:
                prob_value = self.probability_tables["drop-rel"][drop_rel_feature]["false"]
            return prob_value

        elif oper_node_type == "drop-mod":
            mod_candidate = training_graph.get_opernode_oper_candidate(oper_node)
            drop_mod_feature = self.method_feature_extract.get_drop_mod_feature(mod_candidate, main_sent_dict, boxer_graph)
            isDropped = training_graph.get_opernode_drop_result(oper_node)
            prob_value = 0
            if isDropped == "True":
                prob_value = self.probability_tables["drop-mod"][drop_mod_feature]["true"]
            else:
                prob_value = self.probability_tables["drop-mod"][drop_mod_feature]["false"]
            return prob_value

        elif oper_node_type == "drop-ood":
            parent_major_node = training_graph.find_parent_of_opernode(oper_node)
            parent_nodeset = training_graph.get_majornode_nodeset(parent_major_node)
            ood_candidate = training_graph.get_opernode_oper_candidate(oper_node)
            drop_ood_feature = self.method_feature_extract.get_drop_ood_feature(ood_candidate, parent_nodeset, main_sent_dict, boxer_graph)
            isDropped = training_graph.get_opernode_drop_result(oper_node)
            prob_value = 0
            if isDropped == "True":
                prob_value = self.probability_tables["drop-ood"][drop_ood_feature]["true"]
            else:
                prob_value = self.probability_tables["drop-ood"][drop_ood_feature]["false"]
            return prob_value

    def update_count_for_operations(self, sentid, main_sentence, main_sent_dict, simple_sentences, boxer_graph, training_graph, alpha_prob, beta_prob):
        # Process all oper nodes
        for oper_node in training_graph.oper_nodes:
            # Calculating count
            root_inside_prob = beta_prob["MN-1"]
            oper_node_inside_prob = beta_prob[oper_node]
            oper_node_outside_prob = alpha_prob[oper_node]
            count_oper_node = (oper_node_inside_prob * oper_node_outside_prob) / root_inside_prob

            oper_node_type = training_graph.get_opernode_type(oper_node)
            if oper_node_type == "split":
                # Parent main sentence
                parent_major_node = training_graph.find_parent_of_opernode(oper_node)
                parent_nodeset = training_graph.get_majornode_nodeset(parent_major_node)
                parent_filtered_mod_pos = training_graph.get_majornode_filtered_postions(parent_major_node)
                parent_sentence = boxer_graph.extract_main_sentence(parent_nodeset, main_sent_dict, parent_filtered_mod_pos)
                
                # Children sentences
                children_major_nodes = training_graph.find_children_of_opernode(oper_node)
                children_sentences = []
                for child_major_node in children_major_nodes:
                    child_nodeset = training_graph.get_majornode_nodeset(child_major_node)
                    child_filtered_mod_pos = training_graph.get_majornode_filtered_postions(child_major_node)
                    child_sentence = boxer_graph.extract_main_sentence(child_nodeset, main_sent_dict, child_filtered_mod_pos)
                    children_sentences.append(child_sentence)

                split_candidate = training_graph.get_opernode_oper_candidate(oper_node)
                if split_candidate != None:
                    split_feature = self.method_feature_extract.get_split_feature(split_candidate, parent_sentence, children_sentences, boxer_graph)
                    self.count_tables["split"][split_feature]["true"] += count_oper_node
                else:
                    not_applied_cands = training_graph.get_opernode_failed_oper_candidates(oper_node)
                    for split_candidate_left in not_applied_cands:
                        split_feature_left = self.method_feature_extract.get_split_feature(split_candidate_left, parent_sentence, children_sentences, boxer_graph)
                        self.count_tables["split"][split_feature_left]["false"] += count_oper_node
                    
            elif oper_node_type == "drop-rel":
                parent_major_node = training_graph.find_parent_of_opernode(oper_node)
                parent_nodeset = training_graph.get_majornode_nodeset(parent_major_node)
                rel_candidate = training_graph.get_opernode_oper_candidate(oper_node)
                drop_rel_feature = self.method_feature_extract.get_drop_rel_feature(rel_candidate, parent_nodeset, main_sent_dict, boxer_graph)
                isDropped = training_graph.get_opernode_drop_result(oper_node)
                if isDropped == "True":
                    self.count_tables["drop-rel"][drop_rel_feature]["true"] += count_oper_node
                else:
                    self.count_tables["drop-rel"][drop_rel_feature]["false"] += count_oper_node
                    
            elif oper_node_type == "drop-mod":
                mod_candidate = training_graph.get_opernode_oper_candidate(oper_node)
                drop_mod_feature = self.method_feature_extract.get_drop_mod_feature(mod_candidate, main_sent_dict, boxer_graph)
                isDropped = training_graph.get_opernode_drop_result(oper_node)
                if isDropped == "True":
                    self.count_tables["drop-mod"][drop_mod_feature]["true"] += count_oper_node
                else:
                    self.count_tables["drop-mod"][drop_mod_feature]["false"] += count_oper_node
                    
            elif oper_node_type == "drop-ood":
                parent_major_node = training_graph.find_parent_of_opernode(oper_node)
                parent_nodeset = training_graph.get_majornode_nodeset(parent_major_node)
                ood_candidate = training_graph.get_opernode_oper_candidate(oper_node)
                drop_ood_feature = self.method_feature_extract.get_drop_ood_feature(ood_candidate, parent_nodeset, main_sent_dict, boxer_graph)
                isDropped = training_graph.get_opernode_drop_result(oper_node)
                if isDropped == "True":
                    self.count_tables["drop-ood"][drop_ood_feature]["true"] += count_oper_node
                else:
                    self.count_tables["drop-ood"][drop_ood_feature]["false"] += count_oper_node

    def update_probability_table(self):
        for oper_type in self.probability_tables: # split, drop-ood, drop-rel, drop-mod
            for oper_feature_key in self.probability_tables[oper_type]: # feature patterns
                totalSum = 0
                for val in self.probability_tables[oper_type][oper_feature_key]:
                    totalSum += self.count_tables[oper_type][oper_feature_key][val] 
                
                # if totalSum == 0:
                #     print oper_type
                #     print oper_feature_key
                #     print self.probability_tables[oper_type][oper_feature_key]
                #     print self.count_tables[oper_type][oper_feature_key]

                if totalSum == 0:
                    for val in self.probability_tables[oper_type][oper_feature_key]:
                        self.probability_tables[oper_type][oper_feature_key][val] = 0.5 # Uniform 1.0/len(self.probability_tables[oper_type][oper_feature_key]) 
                else:
                    for val in self.probability_tables[oper_type][oper_feature_key]:
                        self.probability_tables[oper_type][oper_feature_key][val] = self.count_tables[oper_type][oper_feature_key][val] / totalSum
