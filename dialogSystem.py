import re
import json
import pandas
import os


"""
基于脚本的多轮对话系统
"""


class DialogSystem:
    def __init__(self):
        self.load()

    def load(self):
        # 加载场景
        self.node_id_to_node_info = {}
        self.load_scenario("scenario-买衣服.json")

        # 加载槽位模板
        self.slot_info = {}
        self.load_slot_templete("slot_fitting_templet.xlsx")
    
    def load_scenario(self, scenario_file):
        scenario_name = os.path.basename(scenario_file).split(".")[0]
        with open(scenario_file, "r", encoding="utf-8") as f:
            self.scenario = json.load(f)
        for node in self.scenario:
            node_id = node["id"]
            node_id = scenario_name + "-" + node_id
            if "childnode" in node:
                new_child = []
                for child in node.get("childnode", []):
                    child = scenario_name + "-" + child
                    new_child.append(child)
                node["childnode"] = new_child
            self.node_id_to_node_info[node_id] = node
        print("场景加载完成")


    def load_slot_templete(self, slot_templete_file):
        dataframe = pandas.read_excel(slot_templete_file)
        for index, row in dataframe.iterrows():
            slot = row["slot"]
            query = row["query"]
            values = row["values"]
            self.slot_info[slot] = [query, values]
        return

    def get_sentence_simility(self, sentence1, sentence2):
        """"
        计算句子的相似度
        这里可以使用一些文本相似度计算方法, 比如编辑距离、余弦相似度、Jaccard相似度等, 也可以用训练好的文本匹配模型
        """
        set1 = set(sentence1)
        set2 = set(sentence2)
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        return len(intersection) / len(union)
        

    def get_node_score(self, node, memory):
        """
        和单个节点计算得分
        """
        intent = memory["user_input"]
        node_intents = node["intent"]
        scores = []
        for node_intent in node_intents:
            sentence_similarity = self.get_sentence_simility(intent, node_intent)
            scores.append(sentence_similarity)
        return max(scores)
            

    def get_intent(self, memory):
        """
        从所有当前可以访问的节点中找到最高分的节点
        """
        max_score = -1
        hit_intent = None
        for node_id in memory["available_nodes"]:
            node = self.node_id_to_node_info[node_id]
            score = self.get_node_score(node, memory)
            if score > max_score:
                max_score = score
                hit_intent = node_id
        memory["hit_intent"] = hit_intent
        memory["hit_intent_score"] = max_score
        return memory
            

    def get_slot(self, memory):
        """
        槽位抽取
        """
        hit_intent = memory["hit_intent"]
        for slot in self.node_id_to_node_info[hit_intent].get("slot", []):
            _, values = self.slot_info[slot]
            if re.search(values, memory["user_input"]):
                memory[slot] = re.search(values, memory["user_input"]).group()
        return memory

    def take_action(self):
        pass
        

    def nlu(self, memory):
        """
        这个函数要实现的功能有：意图识别、槽位抽取
        """
        # 意图识别
        memory = self.get_intent(memory)
        # 槽位抽取
        memory = self.get_slot(memory)
        return memory


    def dst(self, memory):
        """
        对话状态跟踪，判断当前intent所需的槽位是否已经被填满
        """
        hit_intent = memory["hit_intent"]
        slots = self.node_id_to_node_info[hit_intent].get("slot", [])
        for slot in slots:
            if slot not in memory:
                memory["need_slot"] = slot
                return memory
        memory["need_slot"] = None
        return memory


    def policy(self, memory):
        """
        对话策略，根据当前状态选择下一步的动作
        如果槽位有欠缺, 反问槽位
        如果槽位没有欠缺，直接回答
        """
        if memory["need_slot"] is None:
            memory["action"] = "answer"
            # 开放子节点
            memory["available_nodes"] = self.node_id_to_node_info[memory["hit_intent"]].get("childnode", [])
            # 执行动作 
            self.take_action()
            
        else:
            memory["action"] = "ask"
            # 停留在当前节点
            memory["available_nodes"] = [memory["hit_intent"]]
        return memory

    def replace_slot(self, text, memory):
        hit_intent = memory["hit_intent"]
        slots = self.node_id_to_node_info[hit_intent].get("slot", [])
        for slot in slots:
            text = text.replace(slot, memory[slot])
        return text
            

    def nlg(self, memory):
        if memory["action"] == "answer":
            # 直接回答
            answer = self.node_id_to_node_info[memory["hit_intent"]]["response"]
            memory["blot_response"] = self.replace_slot(answer, memory)
        else:
            # 反问
            slot = memory["need_slot"]
            query, _ = self.slot_info[slot]
            memory["blot_response"] = query
        return memory


    def generate_response(self, user_input, memory):
        memory["user_input"] = user_input   # 保存用户的输入
        memory = self.nlu(memory)
        # print(memory)
        memory = self.dst(memory)
        memory = self.policy(memory)
        memory = self.nlg(memory)
        return memory["blot_response"], memory



if __name__ == '__main__':
    ds = DialogSystem()
    # print(ds.node_id_to_node_info)
    # print(ds.slot_info)
    # input()
    memory = {"available_nodes": ["scenario-买衣服-node1"]}
    
    while True:
        user_input = input("user: ")
        response, memory = ds.generate_response(user_input, memory)
        print("bot:", response)
        print()














