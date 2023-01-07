from __future__ import print_function
import copy
import multiprocessing
import random
import time
from itertools import combinations
from multiprocessing import Process
from queue import Queue
import sys
import pandas as pd


def preprocess(file_s="D:\Tool\lich.csv", file_in="D:\Tool\index.csv"):
    x = pd.read_csv(file_s)
    x = x.fillna("")
    index_map = pd.read_csv(file_in)
    map_name2index = {}
    map_index2name = {}
    for index, i in enumerate(zip(index_map['Name'].values, index_map['Index'].values)):
        map_name2index[i[1]] = index
        map_index2name[index] = i[1]
    return x, index_map, map_name2index, map_index2name


def xuly(i, postfix="", max_t=50):
    i = min(int(round(i)), max_t)
    str_format = "\r" + "=" * i + ">" + " " * (max_t - i) + f" {i * 100 // max_t}%" + postfix
    return str_format


class PreMinMaxFlow():
    def __init__(self, name='min_max_flow',
                 num_sink=None,
                 num_flow_to_sink=None,
                 Graph=None,
                 **kwargs):
        self.__dict__.update(**kwargs)
        self.name = name
        assert num_sink is not None
        assert num_flow_to_sink is not None
        assert Graph is not None
        self.num_sink = num_sink
        self.num_flow_to_sink = num_flow_to_sink
        self.num_source = len(Graph[0] if len(Graph) else 0)
        self.anotation = {
            'graph': copy.deepcopy(Graph)
        }
        st = time.time()
        if not hasattr(self, 'limit_combinations'): self.limit_combinations = -1
        self.prepare_sink()

        if hasattr(self, 'multi_gpu'):
            self.prepare_combinations_mp()
        else:
            self.prepare_combinations_no_mp()
        end = time.time()
        print("\nprepare done time = {:.2f}s\n".format(end - st))

    def __str__(self):
        return self.name

    @staticmethod
    def gen(all_combination):
        first_two_combination = combinations(all_combination, 2)
        all_xx = []
        for i in list(first_two_combination):
            current = set(all_combination) - set(i)
            new_z = list(combinations(current, 2))
            all_xx = all_xx + [i + j + tuple(current - set(j)) for j in new_z]
        return all_xx

    def prepare_sink(self):
        if hasattr(self, 'require_sink'):
            require_sink = getattr(self, 'require_sink')
        else:
            require_sink = lambda x: True
        sink = [i for i in range(len(self.anotation['graph'])) \
                if require_sink(self.anotation['graph'][i])]
        self.sink = sink
        self.num_sink_valid = len(sink)

        self.cans_combine_sink = [[1 for i in range(len(self.anotation['graph']))] \
                                  for i in range(len(self.anotation['graph']))]
        for i in range(len(self.anotation['graph'])):
            for j in range(i, len(self.anotation['graph'])):
                x = [1 \
                     for i in zip(self.anotation['graph'][i], self.anotation['graph'][j]) \
                     if (i[0] == i[1] and i[0] == 1)]
                if require_sink(x):
                    self.cans_combine_sink[i][j] = self.cans_combine_sink[j][i] = 1
                else:
                    self.cans_combine_sink[i][j] = self.cans_combine_sink[j][i] = 0

        combination = list(combinations(sink, self.num_sink * self.num_flow_to_sink))
        if hasattr(self, 'shuffle_sink'):
            random.shuffle(combination)
        self.anotation['combinations'] = combination[:self.limit_combinations]

    def prepare_combinations_mp(self):
        num_process = 3
        combination = self.anotation.pop("combinations", [])
        total = len(combination) // 3
        map_process = []
        for i in range(2):
            map_process.append((i * total, i * total + total))
        map_process.append((2 * total, len(combination)))
        process_list = []
        manager = multiprocessing.Manager()
        final_list = manager.list()

        def run_operation(st, end):
            for com in combination[st:end]:
                com_split = PreMinMaxFlow.gen(com)
                for item in com_split:
                    for i in range(0, self.num_sink * self.num_flow_to_sink, 2):
                        if self.cans_combine_sink[item[i]][item[i + 1]] == 0:
                            break
                    else:
                        final_list.append(item)

        for _ in range(num_process):
            p = Process(target=run_operation, args=(map_process[_][0], map_process[_][1]))
            p.start()
            process_list.append(p)

        for _ in range(len(process_list)):
            p = process_list[_]
            p.join()
        self.anotation['combinations'] = list(final_list)

    def prepare_combinations_no_mp(self):  # 10 ^ 7
        combination = self.anotation.pop("combinations", [])
        deep_combination = []
        total = len(combination)
        iter_done = 0
        for com in combination:
            com_split = PreMinMaxFlow.gen(com)
            for item in com_split:
                for i in range(0, self.num_sink * self.num_flow_to_sink, 2):
                    if self.cans_combine_sink[item[i]][item[i + 1]] == 0:
                        break
                else:
                    deep_combination.append(item)
            iter_done += 1
            if iter_done % 100 == 0:
                print(xuly(iter_done * 50 / total), end="\r", sep="\r")
        self.anotation['combinations'] = deep_combination


class MinMaxFlow(object):
    max_off = 50

    def __init__(self, Graph, sink=None):
        self.Graph = copy.deepcopy(Graph)

        self.offset = 10
        self.s = MinMaxFlow.max_off - 2
        self.t = MinMaxFlow.max_off - 1

        self.f = -1
        self.p = [-1 for i in range(MinMaxFlow.max_off)]
        if sink: self.setup(sink)

    def setup(self, sink):
        self.sink = copy.deepcopy(sink)
        self.annotation = {
            'reduce_path': [[0 for i in range(MinMaxFlow.max_off)] for i in range(MinMaxFlow.max_off)],
        }
        self.annotation['graph'] = self.prepare_graph()

    def prepare_graph(self):
        G = [[] for i in range(MinMaxFlow.max_off)]
        for i in range(0, 6, 2):
            d1, d2 = self.sink[i], self.sink[i + 1]
            G[i // 2].append(self.t)
            G[self.t].append(i // 2)
            self.annotation['reduce_path'][i // 2][self.t] = 9  # max
            for index, ix in enumerate(zip(self.Graph[d1], self.Graph[d2])):
                if ix[0] == ix[1] == 1:
                    G[i // 2].append(self.offset + index)
                    G[self.offset + index].append(i // 2)

                    self.annotation['reduce_path'][self.offset + index][i // 2] = 1
        self.all_cost = 0
        for index in range(len(self.Graph[0])):
            G[self.s].append(index + self.offset)
            G[index + self.offset].append(self.s)
            self.annotation['reduce_path'][self.s][index + self.offset] = 1
            self.all_cost += 1

        return G

    def flow(self, v, cur):
        if (v == self.s):
            self.f = cur
            return
        if (self.p[v] != -1):
            #             print(p,v)
            h = self.annotation['reduce_path'][self.p[v]][v]
            self.flow(self.p[v], min(cur, h))

            self.annotation['reduce_path'][self.p[v]][v] -= self.f
            self.annotation['reduce_path'][v][self.p[v]] += self.f

    def run_step(self):
        mf = 0
        while True:
            queue = Queue()
            queue.put(self.s)
            dfs = [0 for i in range(MinMaxFlow.max_off)]
            self.p = [-1 for i in range(MinMaxFlow.max_off)]
            dfs[self.s] = 1
            while queue.empty() == False:
                top = queue.get()
                if top == self.t: break

                for z in self.annotation['graph'][top]:
                    if dfs[z] == 0 and self.annotation['reduce_path'][top][z]:
                        queue.put(z)
                        dfs[z] = 1
                        self.p[z] = top

            self.f = 0
            self.flow(self.t, 1000000)
            mf += self.f
            if self.f == 0: break

        if mf == self.all_cost:
            return True
        return False

    def reduce_path_graph(self, map_name=lambda x: x):
        str_ans = "Thu {} kip {} | Thu {} kip {}"
        reduce_day = lambda x: x // 5 + 2 if x // 5 + 2 <= 7 else 'CN'
        reduce_kip = lambda x: x % 5 + 1
        ans = {}
        for index_k in range(3):
            str_ans_cur = str_ans.format(reduce_day(self.sink[index_k * 2]), reduce_kip(self.sink[index_k * 2]),
                                         reduce_day(self.sink[index_k * 2 + 1]),
                                         reduce_kip(self.sink[index_k * 2 + 1]))
            ans[str_ans_cur] = ""
            for index in range(len(self.Graph[0])):
                if self.annotation['reduce_path'][index_k][index + self.offset] == 1:
                    #                     print(map_name(index),end=" ")
                    ans[str_ans_cur] += " " + map_name(index)
                #             print("")

        return ans


if __name__ == "__main__":
    file_pd = sys.argv[1]
    file_index = sys.argv[2]
    if len(sys.argv) > 3:
        limit_combinations = int(sys.argv[3])
    else:
        limit_combinations = -1

    x, index_map, map_name2index, map_index2name = preprocess(file_s=file_pd, file_in=file_index)
    Graph = [[1 for i in range(26)] for i in range(35)]
    for i in range(2, 9):
        index_day = f'T{i}' if i != 8 else 'CN'
        for st, sc in enumerate(x[index_day].values):
            sc_students = [map_name2index[i.strip()] for i in sc.split(",") if len(i.strip()) > 0]
            for sc_student in sc_students:
                Graph[(i - 2) * 5 + st][sc_student] = 0

    p = PreMinMaxFlow(num_sink=3, num_flow_to_sink=2, Graph=Graph, shuffle_sink=True,
                      require_sink=lambda x: True if sum(x) >= 8 else False,
                      limit_combinations=limit_combinations)
    st = time.time()
    total = len(p.anotation['combinations'])
    iter_ = 0
    cal_xz = MinMaxFlow(p.anotation['graph'])
    total_ans = []
    for item in p.anotation['combinations']:
        iter_ += 1
        if iter_ % 1000 == 0 or iter_ == total:
            print(xuly(iter_ * 50 / total, postfix=" NP"), end="\r", sep="")
        for i in range(3):
            if max(item[i * 2], item[i * 2 + 1]) - min(item[i * 2], item[i * 2 + 1]) <= 6:
                break
        else:
            cal_xz.setup(item)
            ok = cal_xz.run_step()
            if not ok: continue
            ans = cal_xz.reduce_path_graph(map_name=lambda x: map_index2name[x])
            total_ans.append(ans)
            print(xuly(iter_ * 50 / total, postfix=" PP"), end="\r", sep="")
    end = time.time()
    print("done {:.2f} - {}".format(end - st, len(total_ans)))
    print(str(total_ans[0]))

    if len(sys.argv) > 4:
        save_file = sys.argv[4]
        with open(save_file, "w") as f:
            for ans in total_ans:
                f.write(str(ans) + "\n")
