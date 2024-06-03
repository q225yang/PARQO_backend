import psycopg2

from sensitive_dict import *
from prep_error_list import *

from prep_cardinality import get_maps, ori_cardest
from postgres import get_all_plan_cost
from prep_plan_set import get_plan_set_by_enum
from prep_cardinality import get_raw_table_size

import json

EXPLAIN = "EXPLAIN (SUMMARY, COSTS, FORMAT JSON)"
EXPLAIN_ALL = "EXPLAIN (ANALYZE, SUMMARY, COSTS, FORMAT JSON)"
file_of_base_sel = './cardinality/new_single.txt'  # file to be sent to pg folder, contains cardinality for base_rel
file_of_join_sel = './cardinality/join.txt'  # file to be sent to pg folder, contains cardinality for join_rel

class Demo():
    def __init__(self, db_name="imdbloadbase", query_id="2a",
                 method="sobol", rel_error=False, div=2, t=0.2, b=1, inst_id=-2, naive=False):
        ### Store the inputs
        self.db_name = db_name
        self.query_id = query_id
        self.method = method
        self.rel_error = rel_error
        self.t = t
        self.b = b
        self.inst_id = inst_id
        self.naive = naive

        ##### Process db and query, load the cached sensitivity and errors
        if self.method == 'morris':
            cal_sen_method = '_morris'
            if self.db_name == 'imdbloadbase':
                sen_dict = sen_dict_morris  
            if db_name == 'dsb':
                sen_dict =  dsb_sen_dict_morris
            if db_name == 'stats':
                sen_dict =  stats_sen_dict_morris
        elif self.method == 'local':
            cal_sen_method = '_local'
            sen_dict = sen_dict_local
        else:
            cal_sen_method = ''
            if self.db_name == 'imdbloadbase':
                sen_dict = sen_dict_sobol  
            if self.db_name == 'dsb':
                sen_dict =  dsb_sen_dict_sobol
            if self.db_name == 'stats':
                sen_dict =  stats_sen_dict_sobol
        self.cal_sen_method = cal_sen_method
        self.sen_dict = sen_dict

        if self.db_name == 'stats':
            with open(f'./query/stats/stats_{self.query_id}.sql') as p:
                sql = p.read()
            err_files_dict = err_files_dict_stats
        if self.db_name == 'imdbloadbase':
            with open('./query/join-order-benchmark/' + self.query_id + '.sql') as p:
                sql = p.read()
            err_files_dict = err_files_dict_job
        if self.db_name == 'dsb':
            with open(f'./query/dsb/query{self.query_id}_spj_1.sql') as p:
                sql = p.read()
            err_files_dict = err_files_dict_dsb
        self.err_files_dict = err_files_dict

        if self.inst_id == 0:
            self.on_sample = "on-random/"   
            sql = modify_query("random_", "_4", sql)
        elif self.inst_id == -1:
            self.on_sample = "on-sample/"   
            sql = modify_query("sampled_", "_4", sql)
        elif self.inst_id >= 1:
            self.on_sample = "on-cat/"   
            sql = modify_query("cat_", f"_{self.inst_id}", sql)
        else:
            self.on_sample = 'on-base/' + db_name + '/'
            self.inst_id = None
        self.sql = sql

        ### Create connection
        conn = psycopg2.connect(host="/tmp", dbname=self.db_name, user="vcm") # what database should be used
        conn.set_session(autocommit=True)
        self.cursor = conn.cursor()

        ### Prepare the basic info
        table_name_id_dict, join_maps, join_info, pair_rel_info = get_maps(self.db_name, self.sql)
        print(table_name_id_dict)
        print(join_maps)
        print(join_info)
        print(pair_rel_info)
        


    def get_basic_info(self):
        
        return

    def rqo(self):
        if self.sql:
            file_of_base_sel = './cardinality/new_single.txt'  # file to be sent to pg folder, contains cardinality for base_rel
            file_of_join_sel = './cardinality/join.txt'  # file to be sent to pg folder, contains cardinality for join_rel

            # ### Connect ot postgres server
            # conn = psycopg2.connect(host="/tmp", dbname=self.db_name, user="vcm") # what database should be used
            # conn.set_session(autocommit=True)
            # cursor = conn.cursor()

            ### Original Postgres's estimated cardinality
            # table_name_id_dict: {'tbl1':0, 'tbl2':1}
            # join_maps: 2D structure to record which two tables can be joined together
            # pair_relation_list: all edges (pair of two single tables): [('tbl1', 'tbl2'),]
            # join_relation_list: left relation, right relation, raw card (row(left) * row(right)): [[6], [0, 1, 3], 4874964462720]
            table_name_id_dict, join_maps, join_info, pair_rel_info = get_maps(self.db_name, self.sql)
            est_base_card, est_join_card_info = ori_cardest(self.db_name, self.sql)
            est_join_card = list(est_join_card_info[:, 2]) # all 2-way join estimated cardinality
            est_card = est_base_card + est_join_card

            ## selectivity = est_card / raw_card
            ## raw_base_card: number of rows of base_rel
            raw_base_card = get_raw_table_size(self.sql, self.db_name)
            ## raw_join_card: number of rows of left_table * number of rows of right_table
            raw_join_card = [i[2] for i in join_info]
            # raw_card = raw_base_card + raw_join_card
            num_of_base_rel = len(raw_base_card)
            # num_of_pair_rel = len(pair_rel_info)
            num_of_join_rel = len(raw_join_card)
            est_base_sel = [est_base_card[i]/raw_base_card[i] for i in range(num_of_base_rel)]
            est_join_sel = [est_join_card[i]/raw_join_card[i] for i in range(num_of_join_rel)]
            est_sel = est_base_sel + est_join_sel

            # ### Calculate sensitive dimensions on-the-fly
            # print("## RQO: Start analyzing dimension sensitivity...")
            # exp_prob_of_penalized = None
            # sensitive_rels = cal_dim_sensitivity()
            # print("## RQO: Current sensitive dimensions are", sensitive_rels)

            ### prepare selectivity: correct the selectivity if the relations are sensitive
            # prep_sel(sensitive_rels)

            ### Get candidate plan set
            cur_plan_list = get_plan_list(sensitive_rels)
            cost_of_all_hints = get_all_plan_cost(self.cursor, self.sql, self.explain, cur_plan_list)
            ori_opt_plan_id = cost_of_all_hints.index(min(cost_of_all_hints))
            print(f"## RQO: Current we have {len(cur_plan_list)} candidate plans", )

            # ### Filter the plans based on different metrics
            # ## ROBUST METRIC 1: exp penalty
            # _start = time.time()
            
            # joint_err_samples = gen_samples_from_joint_err_dist(args.sample, relations=sensitive_rels, random_seeds=True, naive=args.naive)

            # logging.info(f"The number of samples to calculate expected penalty = {args.sample}.")
            # exp_penalty_list, std_penalty_list, prob_of_penal = exp_penalty_by_samples(cur_plan_list, sensitive_rels, joint_err_samples, tolerance=tolerance, save_samples=True)
            
            # robust_plan_id = [i for i, x in enumerate(exp_penalty_list) if x == min(exp_penalty_list)]
            # _end = time.time()
            # print(f"## RQO: Calculate expected penalty: {_end - _start}(s)")
            # logging.info(f"### Best plan by exp penalty: {robust_plan_id}, overhead {_end - _start}s")
            # logging.info(f"exp_penalty_w_tol: \t{[(id_, i_) for id_, i_ in enumerate(exp_penalty_list)]}")
            
            # ## ROBUST METRIC 2: std penalty
            # robust_plan_id = [i for i, x in enumerate(std_penalty_list) if x == min(std_penalty_list)]
            # logging.info(f"### Best plan by std penalty: {robust_plan_id}, overhead {_end - _start}s")
            # logging.info(f"std_penalty: \t{[(id_, i_) for id_, i_ in enumerate(std_penalty_list)]}")

            # ## ROBUST METRIC 3: std penalty
            # robust_plan_id = [i for i, x in enumerate(prob_of_penal) if x == min(prob_of_penal)]
            # logging.info(f"### Best plan by prob of penalized: {robust_plan_id}, overhead {_end - _start}s")
            # logging.info(f"std_penalty: \t{[(id_, i_) for id_, i_ in enumerate(prob_of_penal)]}")
        else:
            print("SQL query not found, make sure the query has been loaded, try .load_sql()")

if __name__ == "__main__":
    demo = Demo()
    