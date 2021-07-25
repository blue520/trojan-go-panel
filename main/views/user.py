import base64
import json
import os
import yaml
import random

from flask import Response, current_app, jsonify, render_template, request
from flask.views import MethodView
from main.libs.auth_api import constant, create_token, login_required
from main.libs.db_api import (NodeInfoTable, UserNodesTable, UserTable,
                              check_user, add_locol_trojan)
from main.libs.log import log
from main.libs.tools import bytes2human, create_random_str
from main.libs.setting import setting
from main.libs.constant.regex import re_user, re_password, re_mail

__all__ = ["Login", "Logout", "User", "GetTrojanUrl", "Subscribe"]


class Login(MethodView):
    def post(self):
        """
        登录
        """
        user_api = UserTable()
        data = request.get_data()
        data = json.loads(data.decode("UTF-8"))
        username = data.get('username')
        password = data.get('password')
        if not re_user.search(username):
            ret = {'code': 401, 'message': "用户名格式错误"}
            return jsonify(ret)

        check_result, msg = user_api.verify_user(username, password)

        log.info("user", f"{username} 尝试登录 使用ip:{request.remote_addr}")

        if check_result:
            ret = {
                'code': 200,
                'data': {
                    'token': create_token({"username": username}),
                    'username': username
                }
            }
            log.info("user", f"{username} 登录成功 使用ip:{request.remote_addr}")
        else:
            ret = {'code': 401, 'message': msg}
            log.info("user",
                     f"{username} 登录失败:'{msg}' 使用ip:{request.remote_addr}")
        return jsonify(ret)

    def get(self):
        return render_template("index.html")


class Logout(MethodView):
    def post(self):
        pass


class User(MethodView):
    def post(self):
        """
        添加用户
        """
        user_api = UserTable()
        node_max_num = setting.get("trojan", "USER_MAX_NUM")
        all_user = user_api.get_all_user()
        if node_max_num != -1:
            if len(all_user) >= node_max_num:
                return jsonify({'code': 500, 'data': "添加失败, 用户数量超过限制"})
        data = request.get_data()
        data = json.loads(data.decode("UTF-8"))
        try:
            username = data.get("username")

            # 用户输入检查
            if not re_user.search(username):
                raise Exception("用户名格式错误, 请重新输入")
            if user_api.username_if_exist(username):
                raise Exception("用户名重复, 请重新输入")
            if not re_password.search(data.get("password")):
                raise Exception("密码格式错误, 请重新输入")
            if data.get("usermail") and not re_mail.search(data.get("usermail")):
                raise Exception("邮箱格式错误, 请重新输入")

            user_data = data
            if not all_user:
                # 首个账号默认为创建人
                user_data["user_permission"] = constant.PERMISSION_LEVEL_100
                # 创建本地节点
                add_locol_trojan()

            subscribe_pwd = create_random_str(8, 16)
            user_data["subscribe_pwd"] = subscribe_pwd
            user_api.add_user(user_data)
            log.info("user", f"{username} 成功注册用户")
            return jsonify({'code': 200, 'data': ""})
        except Exception as err:
            log.error("user", f"{username} 注册失败{str(err)}")
            return jsonify({'code': 400, 'data': str(err)})

    @login_required(constant.PERMISSION_LEVEL_4)
    def get(self):
        """
        获取所有用户信息
        """
        user_api = UserTable()
        user_node_api = UserNodesTable()
        node_api = NodeInfoTable()

        data_list = []
        for i in user_api.get_all_user():
            data = {}
            username = i["username"]
            quota = i.get("quota")
            expiry_date = i.get("expiry_date")
            data["username"] = username
            data["user_permission"] = i.get("user_permission")
            # 获取用户限制
            data["quota"] = "无限制" if quota == -1 else quota
            data["expiry_date"] = expiry_date.strftime(
                '%Y-%m-%d') if expiry_date else "永久"
            # 获取用户正在使用的节点
            data["nodes"] = user_node_api.get_node_for_user_name(username)
            # 获取用户流量使用状态
            upload, download, total = user_api.get_user_use(
                username, data["nodes"])
            data["upload"] = bytes2human(upload)
            data["download"] = bytes2human(download)
            data["total"] = bytes2human(total)

            data_list.append(data)
        node_list = [
            node["node_name"] for node in node_api.get_all_node_list()
        ]

        ret = {
            "code": 200,
            "data": {
                "user_list": data_list,
                "node_list": node_list
            }
        }
        return jsonify(ret)

    @login_required(constant.PERMISSION_LEVEL_4)
    def put(self):
        """
        修改用户信息
        """
        data = request.get_data()
        data = json.loads(data.decode("UTF-8"))
        user_name = data["username"]
        user_data = data["user_data"]
        node_list = data["node_list"]
        user_api = UserTable()
        user_node_api = UserNodesTable()
        node_api = NodeInfoTable()

        if not user_api.username_if_exist(user_name):
            return jsonify({
                "code": 200,
                "data": {
                    "msg": f"用户名{user_name}不存在!"
                }
            })
        if not user_data.get("expiry_date"):
            user_data["expiry_date"] = None
        if user_data.get("quota") == "无限制":
            user_data["quota"] = -1
        user_api.set_user(user_name, user_data)

        # 用户正在使用的节点
        exist_node_set = set(user_node_api.get_node_for_user_name(user_name))
        # 所有节点
        all_node_set = set(
            [i["node_name"] for i in node_api.get_all_node_list()])
        # 修改后的用户节点
        node_set = set(node_list)
        # 用户未使用的节点(所有节点与已使用节点取差集)
        available_node_set = all_node_set - exist_node_set
        # 需要新增的节点(未使用节点与修改后的节点取并集)
        insert_list = list(available_node_set & node_set)
        # 需要删除的节点(正在使用的节点与修改后的节点取差集)
        del_list = list(exist_node_set - node_set)

        # 添加节点
        insert_data_list = [{
            "user_name": user_name,
            "node_name": node,
            "node_pwd": create_random_str(8, 16)
        } for node in insert_list]
        user_node_api.add_user_node(insert_data_list)
        # 删除节点
        del_data_list = [{
            "user_name": user_name,
            "node_name": node
        } for node in del_list]
        user_node_api.del_user_node(del_data_list)

        # 如果节点有变动则重新计算用户限制
        all_set_node = del_data_list + insert_data_list
        for node in all_set_node:
            node_name = node["node_name"]
            node_usernumber = len(
                user_node_api.get_username_for_nodename(node_name))
            node_api.set_node_usernumber(node_name, node_usernumber)
        if all_set_node:
            check_user(user_api, user_node_api, user_name)

        return jsonify({"code": 200, "data": {}})


class DelUser(MethodView):
    @login_required(constant.PERMISSION_LEVEL_4)
    def post(self):
        """
        删除用户
        """
        data = request.get_data()
        data = json.loads(data.decode("UTF-8"))
        user_name = data["username"]
        user_api = UserTable()
        ret, msg = user_api.del_user(user_name)
        if not ret:
            return jsonify({"code": 500, "data": msg})
        user_node_api = UserNodesTable()
        user_node_api.del_user(user_name)
        del_list = user_node_api.get_node_for_user_name(user_name)
        del_data_list = [{
            "user_name": user_name,
            "node_name": node
        } for node in del_list]
        user_node_api.del_user_node(del_data_list)
        return jsonify({"code": 200, "data": ""})


class GetTrojanUrl(MethodView):
    @login_required(constant.PERMISSION_LEVEL_4)
    def get(self):
        """
        获取用户的trojan链接与订阅链接
        clash订阅链接交给前端处理, 在普通订阅链接后面添加'&t=clash'
        """
        user_name = request.args["0"]

        user_api = UserTable()
        user_node_api = UserNodesTable()
        node_api = NodeInfoTable()

        trojan_urls = []

        node_info_list = user_node_api.get_node_info_for_user_name(user_name)
        for node_info in node_info_list:
            pwd = node_info["node_pwd"]
            node_name = node_info["node_name"]
            node = node_api.get_node_for_nodename(node_name)
            _domain = node["node_domain"]
            node_domain = current_app.config[
                "DOMAIN"] if _domain == "localhost" else _domain
            node_region = node["node_region"]
            trojan_urls.append(
                f"trojan://{pwd}@{node_domain}:443#{node_region}|{node_name}")
        subscribe_pwd = user_api.get_user(user_name)["subscribe_pwd"]
        subscribe_link = ""
        if subscribe_pwd:
            subscribe_link = f"/user/subscribe?u={user_name}&p={subscribe_pwd}"
        data = {}
        data["trojan_urls"] = trojan_urls
        data["subscribe_link"] = subscribe_link
        return jsonify({"code": 200, "data": data})


class Subscribe(MethodView):
    @login_required(constant.PERMISSION_LEVEL_4)
    def post(self):
        """
        通过修改用户表'subscribe_pwd'重置订阅链接
        """
        data = request.get_data()
        data = json.loads(data.decode("UTF-8"))
        user_name = data["username"]

        user_api = UserTable()
        subscribe_pwd = create_random_str(8, 16)
        user_api.set_user(user_name, {"subscribe_pwd": subscribe_pwd})
        return jsonify({"code": 200, "data": {}})

    def generating_fake_data(self):
        # ᕕ( ᐛ )ᕗ 如果密码不对, 就返回随机假数据
        trojan_urls = []
        for _ in range(random.randint(1, 20)):
            domain3 = create_random_str(5, 9)
            domain2 = create_random_str(3, 5)
            domain1 = random.choice(
                ["com", "net", "org", "xyz", "cc", "fuck", "io"])
            pwd = create_random_str(5, 9)
            trojan_urls.append(
                f"trojan://{pwd}@{domain3}.{domain2}.{domain1}:443")
        nodes_str = "\n".join(trojan_urls)
        return base64.b64encode(nodes_str.encode("utf-8"))

    def get(self):
        """
        返回订阅内容
        """
        rsp = dict(request.args)
        user_name = rsp["u"]
        subscribe_pwd = rsp["p"]
        subscribe_type = rsp.get("t")

        user_api = UserTable()
        user_node_api = UserNodesTable()
        node_api = NodeInfoTable()

        content = ""

        # 订阅连接中u参数为user_name, 若用户名不存在则返回假数据
        if not user_api.username_if_exist(user_name):
            content = self.generating_fake_data()
            response = Response(content,
                                content_type="text/plain;charset=utf-8")
            return response

        # 订阅连接中p参数为subscribe_pwd, 若subscribe_pwd与用户名不匹配则返回假数据
        v_subscribe_pwd = user_api.get_user(user_name)["subscribe_pwd"]
        if subscribe_pwd != v_subscribe_pwd:
            content = self.generating_fake_data()
            response = Response(content,
                                content_type="text/plain;charset=utf-8")
            return response

        try:
            node_info_list = user_node_api.get_node_info_for_user_name(
                user_name)
            if subscribe_type == "clash":
                # 若t参数(type)为clash则返回clash配置
                clash_list = []
                clash_name_list = []
                for node_info in node_info_list:
                    trojan_clash = {"type": "trojan"}
                    node_name = node_info["node_name"]
                    node = node_api.get_node_for_nodename(node_name)
                    _domain = node["node_domain"]
                    node_domain = current_app.config[
                        "DOMAIN"] if _domain == "localhost" else _domain

                    trojan_clash["name"] = node_name
                    trojan_clash["server"] = node_domain
                    trojan_clash["password"] = node_info["node_pwd"]
                    trojan_clash["sni"] = node_domain
                    trojan_clash["port"] = 443
                    clash_list.append(trojan_clash)
                    clash_name_list.append(node_name)
                base_clask = os.path.realpath(
                    __file__ + "/../../../conf/clash/base_clask.yaml")
                with open(base_clask, "rb") as yaml_file:
                    yaml_obj = yaml.load(yaml_file, Loader=yaml.FullLoader)
                yaml_obj["proxies"] = clash_list
                yaml_obj["proxy-groups"] = [
                    {
                        "name": "节点选择",
                        "proxies": [
                            "DIRECT",
                        ] + clash_name_list,
                        "type": "select"
                    },
                    {
                        "name": "PROXY",
                        "proxies": clash_name_list,
                        "type": "select"
                    }
                ]
                content = yaml.dump(yaml_obj)
            else:
                # 若t参数(type)为空则返回通常配置
                trojan_urls = []
                for node_info in node_info_list:
                    trojan_clash = {}
                    pwd = node_info["node_pwd"]
                    node_name = node_info["node_name"]
                    node = node_api.get_node_for_nodename(node_name)
                    _domain = node["node_domain"]
                    node_domain = current_app.config[
                        "DOMAIN"] if _domain == "localhost" else _domain
                    node_region = node["node_region"]
                    trojan_urls.append(
                        f"trojan://{pwd}@{node_domain}:443#{node_region}|{node_name}"
                    )
                nodes_str = "\n".join(trojan_urls)
                content = base64.b64encode(nodes_str.encode("utf-8"))
        except Exception as e:
            return f"错误: {str(e)}"

        response = Response(content, content_type="text/plain;charset=utf-8")
        return response
