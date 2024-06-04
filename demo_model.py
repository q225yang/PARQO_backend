import psycopg2
import time
import json
from tqdm import tqdm

from sensitive_dict import *
from prep_error_list import *
from cached_robust_plan_dict import *

from prep_cardinality import get_maps, ori_cardest, write_to_file, write_pointers_to_file
from postgres import get_all_plan_cost, get_real_latency, get_plan_cost
from prep_cardinality import get_raw_table_size
from prep_selectivity import prep_sel

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
        self.div = div
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
            rob_plan_dict = cached_rob_plan_dict_stats
        if self.db_name == 'imdbloadbase':
            with open('./query/join-order-benchmark/' + self.query_id + '.sql') as p:
                sql = p.read()
            err_files_dict = err_files_dict_job
            rob_plan_dict = cached_rob_plan_dict
        if self.db_name == 'dsb':
            with open(f'./query/dsb/query{self.query_id}_spj_1.sql') as p:
                sql = p.read()
            err_files_dict = err_files_dict_dsb
            rob_plan_dict = cached_rob_plan_dict_dsb
        self.err_files_dict = err_files_dict
        self.rob_plan_dict = rob_plan_dict

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

        ### Prepare the basic info
        ## Dimension info
        table_name_id_dict, join_map, join_info, pair_rel_info = get_maps(self.db_name, self.sql)
        self.join_map = join_map    # for prep_sel
        self.join_info = join_info  # for prep_sel
        self.num_of_base = len(table_name_id_dict)
        self.num_of_pair = len(pair_rel_info)
        self.num_of_join = len(join_info)
        dim_name2id_dict, dim_id2name_dict = {}, {}
        for id in range(self.num_of_base+self.num_of_pair):
            if id < self.num_of_base:
                name = list(table_name_id_dict.keys())[id]
            else:
                pair = pair_rel_info[id-self.num_of_base]
                name = pair[0] + '-' + pair[1]
            dim_name2id_dict[name] = id
            dim_id2name_dict[id] = name
        self.dim_name2id_dict = dim_name2id_dict
        self.dim_id2name_dict = dim_id2name_dict
        self.sen_dims = self.sen_dict[get_pure_q_id(self.query_id, self.db_name)]

        ## Estimated cardinality
        est_base_card, est_join_card_info = ori_cardest(self.db_name, self.sql)
        est_join_card = list(est_join_card_info[:, 2]) # all 2-way join estimated cardinality
        self.est_card = est_base_card + est_join_card

        ## Raw cardinality
        raw_base_card = get_raw_table_size(self.sql, self.db_name)
        raw_join_card = [i[2] for i in join_info]  # number of rows of left_table * number of rows of right_table
        self.raw_card = raw_base_card + raw_join_card

        ## Estimated selectivity: selectivity = est_card / raw_card
        est_base_sel = [est_base_card[i]/raw_base_card[i] for i in range(self.num_of_base)]
        est_join_sel = [est_join_card[i]/raw_join_card[i] for i in range(self.num_of_join)]
        self.est_base_sel = est_base_sel
        self.est_join_sel = est_join_sel
        self.est_sel = est_base_sel + est_join_sel

        ## Error information
        err_info_dict = {}
        for i in range(self.num_of_base + self.num_of_pair):

            cur_err_list, cur_err_hist = prepare_error_data(db_name, query_id, sensi_dim=i, max_sel=1.0, 
                                                            rel_error=self.rel_error, div=self.div)
            if cur_err_list == [] and cur_err_hist == []: # Don't need to build err profile for this dimension
                err_info_dict[i] = []
                continue
            cur_kde_list = cal_pdf(cur_err_hist, rel_error=self.rel_error, bandwidth=self.b, naive=self.naive)
            err_info_dict[i] = [cur_err_list, cur_err_hist, cur_kde_list]
        self.err_info_dict = err_info_dict

        ## Plan hints
        cur_plan_list = []
        if self.inst_id != None:
            file = './plan/' + self.on_sample + 'tmp_plan_dict_' + self.db_name + '_' + self.query_id + '_' + str(self.inst_id) + self.cal_sen_method + '.txt'
        else:
            file = './plan/' + self.on_sample + 'tmp_plan_dict_' + self.db_name + '_' + self.query_id + self.cal_sen_method +'.txt'
            
            if self.db_name == 'imdbloadbase': # use the plan generated by full err profile (no train-test split)
                file = './plan/' + self.on_sample + 'saved-tmp_plan_dict_' + self.db_name + '_' + self.query_id + self.cal_sen_method +'.txt'
        plan_hint_dict = json.load(open(file))        
        for i in plan_hint_dict.values():
            cur_plan_list = cur_plan_list + i
        cur_plan_list = list(sorted(set(cur_plan_list)))
        # if query_id == '17a':
        #     cur_plan_list = [cur_plan_list[7], cur_plan_list[8], cur_plan_list[10], cur_plan_list[44]]
        self.cur_plan_list = cur_plan_list  # all current plan hints
        self.plan_list = None   # the selected plan hints

    def get_error_data(self, dim):
        '''Prepare the error data for error distribution at a given dimension
        '''
        data = None
        plotable = False
        error = None
        if dim in self.err_files_dict[get_pure_q_id(self.query_id, self.db_name)]:
            plotable = True
            r = find_bin_id_from_err_hist_list(self.est_card, self.raw_card, cur_dim=dim, err_info_dict=self.err_info_dict)
            kde = self.err_info_dict[dim][2][r]
            error = [_[1] for _ in self.err_info_dict[dim][1][r]] # (est_sel, rel_err)
            error = np.array(error).reshape(-1, 1)
            if True:
                x = np.linspace(min(-5, np.min(error) - 2), max(5, np.max(error) + 2), 1000)[:, np.newaxis]
            # else:
            #     x = np.linspace(min(np.min(error), -np.max(error)), max(-np.min(error), np.max(error)), 1000)[:, np.newaxis]
            y = np.exp(kde.score_samples(x)).tolist()
            error = error[:, 0].tolist()
            x = x[:, 0].tolist()
            data = {"x":x, "y":y}
        return plotable, data, error

    def get_basic_info(self, save=False):
        '''Pack the basic information for each dimension
        '''
        basic_info = {}
        for dim, dim_name in self.dim_id2name_dict.items():
            isedge = dim>=self.num_of_base
            if not isedge:
                component = [dim_name]
            else:
                component = dim_name.split('-')
            plotable, error_plot, error = self.get_error_data(dim)
            dim_info = {
                "dim": dim,
                "isedge": isedge,
                "component": component,
                "cardinality": int(self.est_card[dim]),
                "raw_cardinality": int(self.raw_card[dim]),
                "selectivity": float(self.est_sel[dim]),
                "plotable": plotable,
                "error_plot": error_plot,
                "error": error
            }
            basic_info[dim_name] = dim_info
        if save:
            with open(f'./demo_data/basic_stats_{self.db_name}_{self.query_id}.json', 'w') as file:
                json.dump(basic_info, file, indent=1)
        return json.dumps(basic_info, indent=1)

    def get_sensitive_dim(self, save=False):
        '''Return all sensitive dimensions
        '''
        sen_info = {}
        for dim in self.sen_dims:
            dim_name = self.dim_id2name_dict[dim]
            isedge = dim>=self.num_of_base
            if not isedge:
                component = [dim_name]
            else:
                component = dim_name.split('-')
            dim_info = {
                "dim": dim,
                "isedge": isedge,
                "component": component,
            }
            sen_info[dim_name] = dim_info
        if save:
            with open(f'./demo_data/sensitive_{self.db_name}_{self.query_id}.json', 'w') as file:
                json.dump(sen_info, file, indent=1)
        return json.dumps(sen_info, indent=1)

    def rqo(self, inject=None, save=False):
        '''Get plans under rqo algo. If user-input selectivity is provided, add an additional plan with input injected.
        '''
        t1 = time.perf_counter()
        ### Connect ot postgres server
        conn = psycopg2.connect(host="/tmp", dbname=self.db_name, user="lsh") # what database should be used
        conn.set_session(autocommit=True)
        cursor = conn.cursor()

        if not inject:
            ### Set up for query execution
            write_to_file(self.est_base_sel, file_of_base_sel)
            write_to_file(self.est_join_sel, file_of_join_sel)
            write_pointers_to_file(list(range(self.num_of_base + self.num_of_join)))

            ### Get candidate plan set
            cost_of_all_hints = get_all_plan_cost(cursor, self.sql, EXPLAIN, self.cur_plan_list)
            ori_opt_plan_id = cost_of_all_hints.index(min(cost_of_all_hints))   # original optimal plan

            ### Get robust plan
            rob_plan_id = self.rob_plan_dict[self.query_id]

            self.plan_list = [ori_opt_plan_id] + rob_plan_id

            plans = []
            latencies = []
            for hint_id in self.plan_list:
                hint = self.cur_plan_list[hint_id]
                _, plan = get_plan_cost(cursor, self.sql, hint=hint, explain=EXPLAIN_ALL, plan=True)
                latency = get_real_latency(self.db_name, self.sql, hint=hint)
                latencies.append(latency)
                plans.append(plan)
            self.plans = plans
            self.latencies = latencies
        else:
            ### Inject the user's inputs
            self.inject_input_sel(inject)
            _, plan = get_plan_cost(cursor, self.sql, explain=EXPLAIN_ALL, plan=True)
            latency = get_real_latency(self.db_name, self.sql)
            latencies = self.latencies + [latency]
            plans = self.plans + [plan]
        # cursor.close()

        if save:
            if inject:
                inject_ = "_adj"
            else:
                inject_ = ""
            with open(f'./demo_data/plans{inject_}_{self.db_name}_{self.query_id}.json', 'w') as file:
                json.dump(plans, file, indent=1)
            with open(f'./demo_data/latencies{inject_}_{self.db_name}_{self.query_id}.json', 'w') as file:
                json.dump(latencies, file, indent=1)
        t2 = time.perf_counter()
        print(f"time: {t2-t1}s")
        return json.dumps(plans, indent=1)

    def inject_input_sel(self, inject):
        '''Process and inject the user input into postgres
        '''
        error = []
        rel_list = []
        for dim_name, sel_adj in inject.items():
            rel_list.append(self.dim_name2id_dict[dim_name])
            error.append(sel_adj)
        _, _ = prep_sel(self.dim_name2id_dict, self.join_map, self.join_info,
                        self.est_base_sel, file_of_base_sel,
                        self.est_join_sel, file_of_join_sel,
                        error=error, recentered_error=None,
                        relation_list=rel_list, rela_error=self.rel_error)

    def gen_samples_from_joint_err_dist(self, N, random_seeds=True, naive=False):
        ''' Generate samples from the error distribution on each dimension and then joint them
        '''
        if random_seeds:
            np.random.seed(2023)
        joint_error_samples = []
        for table_id in self.sen_dims:
            if naive:
                err_sample = np.random.uniform(-10, 10, N)
            else:
                r = find_bin_id_from_err_hist_list(self.est_card, self.raw_card, cur_dim=table_id, err_info_dict=self.err_info_dict)
                pdf_of_err = self.err_info_dict[table_id][2][r]
                err_sample = pdf_of_err.sample(N)
            joint_error_samples.append(err_sample)
        ### Transfer to joint samples
        if naive:
            joint_error_samples = np.array(joint_error_samples).T.tolist()
        else:
            joint_error_samples = np.array(joint_error_samples).T.tolist()[0]
        return joint_error_samples

    def get_all_cost(self, inject=None, N=100):
        if self.plan_list:
            costs = []
            ### Connect ot postgres server
            conn = psycopg2.connect(host="/tmp", dbname=self.db_name, user="lsh") # what database should be used
            conn.set_session(autocommit=True)
            cursor = conn.cursor()
            if not inject:
                ### Set up for query execution
                write_to_file(self.est_base_sel, file_of_base_sel)
                write_to_file(self.est_join_sel, file_of_join_sel)
                write_pointers_to_file(list(range(self.num_of_base + self.num_of_join)))

                error_samples = self.gen_samples_from_joint_err_dist(N, naive=self.naive)
                for i, plan_id in enumerate(self.plan_list):
                    plan_costs = {}
                    hint = self.cur_plan_list[plan_id]
                    for j, dim in enumerate(self.sen_dims):
                        dim_name = self.dim_id2name_dict[dim]
                        x, y = [], []
                        dim_cost = []
                        for sample in tqdm(error_samples):
                            sample_inject = {dim_name:sample[j]}
                            self.inject_input_sel(sample_inject)
                            cost = get_plan_cost(cursor, self.sql, hint=hint, explain=EXPLAIN)
                            dim_cost.append((sample[j], cost))
                        dim_cost = sorted(dim_cost, key=lambda t:t[0])
                        for s, c in dim_cost:
                            x.append(s)
                            y.append(c)
                        plan_costs[dim_name] = {"x":x, "y":y}
                    
                    costs.append(plan_costs)
                    print(f"plans: {i+1}/{len(self.plan_list)} done.")
                # self.costs = costs
                
                if save:
                    if inject:
                        inject_ = "_adj"
                    else:
                        inject_ = ""
                    with open(f'./demo_data/costs{inject_}_{self.db_name}_{self.query_id}.json', 'w') as file:
                        json.dump(costs, file, indent=1)
                return json.dumps(costs, indent=1)
            # else:pass


if __name__ == "__main__":
    query_id = "2a"
    save = True
    demo = Demo(query_id=query_id)
    basic_stats = demo.get_basic_info(save=save)
    
    sen_dims = demo.get_sensitive_dim(save=save)

    plans = demo.rqo(save=save)
    
    # inject = {"mi_idx-it":0.1}  # 1a
    inject = {"mc-cn":0.1}  # 2a
    plans_adj = demo.rqo(inject=inject, save=save)

    costs = demo.get_all_cost()